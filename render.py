"""
Copyright 2024-present, Matteo Bicchi
All rights reserved


This file is part of SSHAPE_Dataset_generator.

SSHAPE_Dataset_generator is free software: you can redistribute it and/or modify it under the terms of the 
GNU General Public License as published by the Free Software Foundation, either version 3 of the 
License, or any later version.

SSHAPE_Dataset_generator is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without 
even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General 
Public License for more details.

You should have received a copy of the GNU General Public License along with SSHAPE_Dataset_generator. 
If not, see <https://www.gnu.org/licenses/>.
"""

try: #tqdm is not built in, if not installed it will be skipped
    from tqdm import tqdm 
except ImportError:
    tqdm = lambda k: k

from datetime import datetime
from math import sin, cos, radians, degrees, sqrt
import random, os, json
from random import randint
from SSHAPE_Dataset_generator.errors import *
from SSHAPE_Dataset_generator.utils import *
from SSHAPE_Dataset_generator.categories import create_categories_list, get_category_name
from icecream import ic
import numpy as np

#blender
import bpy, bpy_extras, mathutils #type: ignore
from bpy import context #type: ignore
from mathutils import Vector, Color #type: ignore
import bpycv, cv2

#Shapes with random_rotation.snap set to auto will have the normal of a random face aligned with this vector
#NOTE: Right now changing this vector is not properly supported
AUTO_ROTATION_VECT = mathutils.Vector((0, 0, -1))


class DatasetRenderer:
    def __init__(self, args, rules):
        self.args = args
        self.rules = rules
        self.annotations = None
        self.state = None #None if not rendering, otherwise stores rendering data and progression

        #INITIALIZE SCENE
        scene = bpy.context.scene
                     
        #create and place camera
        cam = bpy.data.cameras.new("Camera")
        cam.lens = 20

        self.camera_obj = bpy.data.objects.new("Camera", cam)
        self.camera_obj.location = (0, 0, 0)
        self.camera_obj.rotation_euler = (0, 0, 0)

        scene.collection.objects.link(self.camera_obj)
        scene.camera = self.camera_obj

        render_args = bpy.context.scene.render
        render_args.engine = "CYCLES"
        render_args.resolution_x = args.images_width
        render_args.resolution_y = args.images_height
        render_args.resolution_percentage = 100 #NOTE: Changing this will probably mess up bounding boxes calculation

        if args.use_gpu == 1:
            cycles_prefs = bpy.context.preferences.addons['cycles'].preferences 
            cycles_prefs.compute_device_type = 'CUDA'
            bpy.context.scene.cycles.device = 'GPU'
            bpy.context.preferences.addons["cycles"].preferences.get_devices()
            for d in bpy.context.preferences.addons["cycles"].preferences.devices:
                d["use"] = 1 # Using all devices, include GPU and CPU
                print(d["name"], d["use"])

        bpy.data.worlds['World'].cycles.sample_as_light = True
        bpy.context.scene.cycles.blur_glossy = 2.0
        bpy.context.scene.cycles.samples = 512
        bpy.context.scene.cycles.transparent_min_bounces = 6
        bpy.context.scene.cycles.transparent_max_bounces = 8
        
        #add primitive plane  
        self.primitive_plane = bpy.ops.mesh.primitive_plane_add(size=args.area_size)

        #load materials
        self.load_materials()
        self.create_directory_tree()

        #
        render_scale = render_args.resolution_percentage / 100
        self.render_size = (
            int(render_args.resolution_x * render_scale),
            int(render_args.resolution_y * render_scale)
        )

    def create_directory_tree(self):
        #setup output directory tree
        os.makedirs(self.args.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.args.output_dir, self.args.split), exist_ok=True)
        os.makedirs(os.path.join(self.args.output_dir, self.args.split, "images"), exist_ok=True)
        if self.args.create_segmentations == 1:
            os.makedirs(os.path.join(self.args.output_dir, self.args.split, "segmentation"), exist_ok=True)
            os.makedirs(os.path.join(self.args.output_dir, self.args.split, "depth"), exist_ok=True)

    def save_annotations(self):
        prefix = self.args.filename_prefix
        filename = f"{prefix + '_' if prefix is not None else ''}{self.args.split}_annotations.json"
        with open(os.path.join(self.args.output_dir, self.args.split, filename), "w") as f:
            json.dump(self.annotations, f)

    def render(self):
        #tarts rendering
        args = self.args

        self.annotations = {
            "info" : self.create_info(),
            "licenses" : self.get_licenses(),
            "images" : [],
            "annotations" : [],
            "scenes" : [],
            "categories" : create_categories_list(self.rules)
        }

        self.state = {
            "img_index" : 0,
            "shape_index" : 0
        }


        # --------------------------- RENDERING LOOP ---------------------------


        for img_index in tqdm(range(args.num_images)):
            prefix = args.filename_prefix #prefix for files
            img_filename = f"{prefix + '_' if prefix is not None else ''}{img_index:010d}.png" #TODO: add support for other file formats

            #image metadata
            image_info = {
                "id" : img_index,
                "file_name" : img_filename,
                "height" : args.images_height,
                "width" : args.images_width,
                "date_captured" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "license" : -1
            }

            #scene metadata
            scene = {
                "camera_position" : self.get_camera_position(),
                "lights" : self.get_lights_positions(),
                "objects" : [],
                "decoys" : []
            }

            self.annotations["scenes"].append(scene)
            self.annotations["images"].append(image_info)

            self.populate_scene()

            render_args = bpy.context.scene.render #set path for rendering
            render_args.filepath = os.path.abspath(
                os.path.join(args.output_dir, args.split, "images", img_filename)
            )

            if not args.test_mode:
                while True:
                    try:
                        bpy.ops.render.render(write_still=True)
                        if args.create_segmentations == 1 or args.create_depth == 1:
                            gnd_truth = bpycv.render_data(render_image=False)
                            if args.create_segmentations == 1:
                                segmentation_path = os.path.join(args.output_dir, args.split, "segmentation", img_filename)
                                cv2.imwrite(segmentation_path, np.uint8(gnd_truth["inst"]))
                            if args.create_depth == 1:
                                depth_path = os.path.join(args.output_dir, args.split, "depth", img_filename)
                                cv2.imwrite(depth_path, np.uint16(gnd_truth["depth"] * 1000)) #save depth in mm

                        break
                    except Exception as e:
                        print(e)

            self.clear_scene()

        self.save_annotations()

    def create_info(self):
        return {
            "description" : "SSHAPE Dataset, a fully synthetic dataset for computer vision",
            "url" : "https://github.com/M4tt3/SSHAPE_Dataset_generator", 
            "version" : "pre-release",
            "contibutor" : "Matteo Bicchi",
            "date_created" : datetime.now().isoformat().split("T")[0]
        }

    def get_licenses(self):
        return []   #TODO

    def get_camera_position(self) -> mathutils.Vector:
        # Generate random pitch and yaw values for the camera, move the camera
        # to that position at a fixed distance from the origin, point the camera
        # towards the origin and returns camera x, y, z position

        pitch = randint(self.args.min_camera_pitch, self.args.max_camera_pitch)
        yaw = randint(self.args.min_camera_yaw, self.args.max_camera_yaw)

        pos = [
            self.args.camera_distance * sin(radians(yaw)),
            self.args.camera_distance * cos(radians(yaw)),
            self.args.camera_distance * sin(radians(pitch))
        ]

        #move camera into position and focus it on the origin
        self.camera_obj.location = pos

        rot_quat = self.camera_obj.location.to_track_quat('Z', 'Y')
        self.camera_obj.rotation_euler = rot_quat.to_euler()
        self.camera_obj.location = rot_quat @ mathutils.Vector((0.0, 0.0, self.args.camera_distance))

        return pos

    def get_lights_positions(self):
        # Chooses a random number of lights, moves them at a random position at
        # a fixed distance from the origin, and returns an array of their x, y, z
        # positions

        lights_number = randint(self.args.min_num_lights, self.args.max_num_lights)
        pos = []

        for i in range(lights_number):
            pos.append([
                self.args.lights_distance * sin(radians(randint(0, 360))) * self.args.lights_jitter,
                self.args.lights_distance * cos(radians(randint(0, 360))) * self.args.lights_jitter,
                self.args.lights_distance * (1 - sin(radians(randint(0, 180))) * self.args.lights_jitter)
            ])

            #place light
            light_data = bpy.data.lights.new(name=f"Light_{i}_data", type='POINT')
            light_data.energy = self.args.lights_intensity

            light_object = bpy.data.objects.new(name=f"Light_{i}", object_data=light_data)
            bpy.context.collection.objects.link(light_object)

            light_object.location = pos[-1]

        return pos
    
    def clear_scene(self):
        #removes all placed shapes and lights
        for obj in context.scene.objects:
            if obj.name.startswith("OBJECT_") or obj.type == "LIGHT":
                obj.select_set(True)
            else:
                obj.select_set(False)

        bpy.ops.object.delete()

    def load_materials(self):
        # Loads all the combinations of materials and colors
        for mat_rule in self.rules.materials:
            #load material file
            filename = os.path.join(self.args.materials_dir, mat_rule["file"], "NodeTree", mat_rule["name"])
            print(f"Loading material: {filename}")
            bpy.ops.wm.append(filename=filename)

            allowed_colors = self.rules.get_material_allowed_colors(mat_rule["name"])

            if len(allowed_colors) == 0: #load material without color
                self.create_material(mat_rule)

            for color in allowed_colors: #load all combinations of color and material
                color_rule = self.rules.colors[color]
                self.create_material(mat_rule, color_rule)


    def create_material(self, mat_rule, col_rule=None):
        # Adds a new material to the scene
        # Args:
        # - mat_rule : Rule for the material
        # - col_rule : If left None no color will be applied, otherwise it's the rule for
        #              the color to be applied to the material.
        bpy.ops.material.new()
        mat = bpy.data.materials['Material']
        
        output_node = mat.node_tree.nodes["Material Output"]

        #create a new group for the material node tree
        group_node = mat.node_tree.nodes.new("ShaderNodeGroup")
        #copy the material node tree into the new group
        group_node.node_tree = bpy.data.node_groups[mat_rule["name"]]

        if col_rule is None:
            mat.name = f"{mat_rule['name']}"
        else:
            group_node.inputs["Color"].default_value = [*color_from_hex(col_rule["hex"]), col_rule["opacity"]]
            mat.name = f"{mat_rule['name']}_{col_rule['name']}"

        mat.node_tree.links.new(
            group_node.outputs["Shader"],
            output_node.inputs["Surface"]
        )

    def populate_scene(self):
        #Places a random number of objects and decoys in random places, adds their position to annotations

        num_objects = randint(self.args.min_num_objects, self.args.max_num_objects) #random amount of objects
        obj_index = self.state["shape_index"]
        self.place_shapes(obj_index, num_objects, decoys=False)
        self.state["shape_index"] += num_objects

        if len(self.rules["decoys"]) > 0: 
            num_decoys = randint(self.args.min_num_decoys, self.args.max_num_decoys)
            decoy_index = self.state["shape_index"]
            self.place_shapes(decoy_index, num_decoys, decoys=True)
            self.state["shape_index"] += num_decoys

    def place_shapes(self, start_index: int, num_shapes: int, decoys: bool):
        # Places a random number of shapes in random places and applies random scale,
        # rotation, flip, material and color
        # Args:
        # start_index : Starting index for object ids
        # num_shapes : Number of shapes to create
        # decoys : Whether the shapes to be created are decoys (True) or objects (False)

        group = "decoys" if decoys else "objects" #either 'decoys' or 'object' depending on what shapes are being added
        for obj_index in range(start_index, start_index + num_shapes):
            shape_rule = random.choice(list(self.rules[group])) #random shape
            
            mat_name, col_name = self.choose_random_appearance(shape_rule)
            mat_rule = self.rules.materials[mat_name]
            col_rule = self.rules.colors[col_name]


            object_annotations = {
                "id" : obj_index,
                "shape" : {
                    "id" : shape_rule["id"],
                    "name" : shape_rule["name"],
                    "file" : shape_rule["file"],
                    "min_distance" : shape_rule["min_distance"]
                },
                "material" : {
                    "id" : mat_rule["id"],
                    "name" : mat_rule["name"],
                    "file" : mat_rule["file"]
                } if mat_rule is not None else None,
                "color" : {
                    "id" : col_rule["id"],
                    "name" : col_rule["name"],
                    "hex" : col_rule["hex"]
                } if col_rule is not None else None,
            }

            #add object to scene
            obj_blender = self.add_shape(self.args.decoys_dir if decoys else self.args.objects_dir, object_annotations)

            random_scale = [1, 1, 1]
            #perform random scale if needed
            if shape_rule["scaling"] != "none":
                random_scale = self.random_scale(obj_blender, shape_rule)

            #apply fixed rotation and random rotation if needed
            rotate(obj_blender, shape_rule["fixed_rotation"])
            random_rotation = [0, 0, 0]
            if shape_rule["random_rotation"] != "none":
                random_rotation = self.random_rotate(obj_blender, shape_rule)

            #apply random flips
            if shape_rule["flip"] != "none":
                self.random_flip(shape_rule["flip"])

            object_annotations["scale"] = random_scale
            object_annotations["rotation"] = [random_rotation[i] + shape_rule["fixed_rotation"][i] for i in range(3)] #sum random and fixed rotation

            bpy.context.view_layer.objects.active = obj_blender
            bpy.ops.object.transform_apply(rotation=True, scale=True)

            #position the shape randomly
            pos = self.try_shape_placement(obj_blender, shape_rule, object_annotations)
            if pos is not None:
                object_annotations["position"] = pos

            #apply material and color
            if mat_rule is not None:
                if col_rule is None:
                    material_blender = bpy.data.materials[f"{mat_name}"]
                else:
                    material_blender = bpy.data.materials[f"{mat_name}_{col_name}"]
            
                obj_blender.data.materials.append(material_blender)

            #get annotations for training
            if not decoys and self.args.create_bounding_boxes == 1:
                #bbox
                bbox = self.get_bounding_box(obj_blender)
                category_id = obj_blender["inst_id"]

                self.annotations["annotations"].append({
                    "id" : obj_index,
                    "category_id" : category_id,
                    "iscrowd" : 0,
                    "image_id" : self.annotations["images"][-1]["id"],
                    "bbox" : bbox
                })

            self.annotations["scenes"][-1][group].append(object_annotations)

    def choose_random_appearance(self, shape_rule):
        # Returns random material and color rules
        allowed_mats = self.rules.get_shape_allowed_materials(shape_rule["name"])
        if len(allowed_mats) > 0:
            mat_name = random.choice(allowed_mats)
            allowed_colors = self.rules.get_composite_allowed_colors(shape_rule["name"], mat_name)
            if len(allowed_colors) > 0:
                return mat_name, random.choice(allowed_colors)
            else:
                return mat_name, None
        else:
            return None, None
        
    def add_shape(self, shape_dir, object_annotation):
        #add a shape to the scene
        name = object_annotation["shape"]["name"]
        filename = os.path.join(shape_dir, object_annotation["shape"]["file"], "Object", name)
        bpy.ops.wm.append(filename=filename)

        blender_obj = bpy.data.objects[name]
        blender_obj.name = f"OBJECT_{name}_{object_annotation['id']}"


        #assign instance id
        categories = self.annotations["categories"]

        mat_name = object_annotation["material"]["name"] if object_annotation["material"] else None
        col_name = object_annotation["color"]["name"] if object_annotation["color"] else None

        try:
            cat_id = categories.index( #get category id by shape, material and color (if present and not ignored)
                get_category_name(
                    shape=name,
                    material=mat_name if not self.rules.categories["ignore_material"] else None,
                    color=col_name if not self.rules.categories["ignore_color"] else None
                )
            )
            blender_obj["inst_id"] = cat_id
        except ValueError:
            pass

        return blender_obj
    
    def random_scale(self, obj, shape):
        #Scales currently active object according to provided rule
        scaling_factors = []

        get_factor = lambda: randrange_float(shape["scaling"]["min"], shape["scaling"]["max"], shape["scaling"]["step"])

        if shape["scaling"]["consistent"] == "all":
            fac = get_factor()
            scaling_factors = [fac for k in range(3)]
        elif shape["scaling"]["consistent"] == "none":
            scaling_factors = [get_factor() for k in range(3)]
        elif shape["scaling"]["consistent"] in ["xy", "xz", "yz"]:
            fac1, fac2 = get_factor(), get_factor()
            if shape["scaling"]["consistent"] == "xy":
                scaling_factors = [fac1, fac1, fac2]
            elif shape["scaling"]["consistent"] == "yz":
                scaling_factors = [fac1, fac2, fac2]
            else:
                scaling_factors = [fac1, fac2, fac1]
        else:
            raise InvalidValueError("shape.scaling.consistent", shape["scaling"]["consistent"])
        
        obj.scale = scaling_factors
        return scaling_factors

    def random_rotate(self, obj, shape_rule):
        rotation = [0, 0, 0]
        get_random_angle = lambda axis: random.randrange(
            start=shape_rule["random_rotation"]["min_bounds"][axis],
            stop=shape_rule["random_rotation"]["max_bounds"][axis],
            step=shape_rule["random_rotation"]["snap"][axis],
        )
        
        if shape_rule["random_rotation"]["auto_snap_face"]:
            #Auto rotate so that the normal of a random face is aligned to AUTO_ROTATION_VECT
            for attempt in range(16):
                normal = random.choice(obj.data.polygons).normal #normal of a random face
                angle = normal.angle(AUTO_ROTATION_VECT) #angle between normal and AUTO_ROTATION_VECT
                axis = normal.cross(AUTO_ROTATION_VECT) #axis perpendicular to normal and AUTO_ROTATION_VECT
                matrix = mathutils.Matrix.Rotation(angle, 3, axis)
                rotation_radians = matrix.to_euler()
                valid = True
                for axis in range(3):
                    if (degrees(rotation_radians[axis]) <= shape_rule["random_rotation"]["max_bounds"][axis]
                    and degrees(rotation_radians[axis]) >= shape_rule["random_rotation"]["min_bounds"][axis]):
                        rotation[axis] = degrees(rotation_radians[axis])
                    else:
                        valid=False
                        break
                if valid:
                    break
            
            #Add z rotation if needed
            if shape_rule["random_rotation"]["snap"][2] != 0:
                rotation[2] = get_random_angle(2)

        else:
            for axis in range(3):
                angle = get_random_angle(axis) if shape_rule["random_rotation"]["snap"][axis] > 0 else 0
                rotation[axis] = angle

        rotate(obj, rotation)
        return rotation
    
    def random_flip(self, flip_rule):
        #mirrors currently active object based on the flip settings it receives
        flips = (False, False, False)
        for flip_axis, flip_mode in flip_rule.items():
            if flip_mode == "random":
                flip_mode = bool(random.getrandbits(1)) #random bool
            
            idx = ["yz", "xz", "xy"].index(flip_axis)
            flips[idx] = flip_mode

        bpy.ops.transform.mirror(constraint_axis=flips)

    def try_shape_placement(self, obj, shape_rule, obj_annotations, max_attempts=50):
        for attempt in range(max_attempts):
            get_random_pos = lambda: random.uniform(self.args.padding - self.args.area_size / 2, self.args.area_size / 2 - self.args.padding)
            pos = [get_random_pos() for i in range(3)]
            if shape_rule["snap_to_plane"] == True:
                origin = mathutils.Vector((0,0,0))
                dir = mathutils.Vector((0,0,-1))
                hit, point, face, index = obj.ray_cast(origin, dir)
                pos[2] = point.length
                    
            if self.check_min_distance(pos, obj_annotations):
                obj.location = pos
                return pos
        
        print(f"Unable to place shape {obj_annotations['id']} after {max_attempts} attempts, the shape will" + 
              "be removed.\nThis warning is probably a result of too many shapes, too high 'min_distance' or a too" +
              "low area size.\nIf this error pops up more than once you should probably modify those values.")
        return None
    
    def get_segmentation(self):
        pass
    
    def check_min_distance(self, pos, obj_annotations):
        #returns true if the object respects the 'min_distance' rule from all the other shapes of the last scene
        for other_object in self.annotations["scenes"][-1]["objects"] + self.annotations["scenes"][-1]["decoys"]:
            distance = get_distance(Vector(other_object["position"]), Vector(pos)) #distance between two shapes

            #minimum distances scaled to the max scaling along an axis of each object
            min_distance_1 = other_object["shape"]["min_distance"] * max(*other_object["scale"])
            min_distance_2 = obj_annotations["shape"]["min_distance"] * max(*obj_annotations["scale"])

            if distance < min_distance_1 + min_distance_2:
                return False
            
        return True
    
    def get_bounding_box(self, object):
        corners_locations = [vert.co for vert in object.data.vertices]
        lowest_values = [None , None]
        highest_values = [None, None]
        for corner in corners_locations:
            #get position of corner in 2d camera view
            c_2d = bpy_extras.object_utils.world_to_camera_view(bpy.context.scene, self.camera_obj, corner + object.location)
            #transform to pixel coordinates
            render = bpy.context.scene.render
            c_2d = [
                round(c_2d.x * render.resolution_x),
                self.args.images_height - round(c_2d.y * render.resolution_y) #for some reason y is flipped
            ]

            if lowest_values[0] is None: #if no value has been assigned yet
                lowest_values = c_2d.copy()
                highest_values = c_2d.copy()
                continue

            if lowest_values[0] > c_2d[0]:
                lowest_values[0] = c_2d[0]
            elif highest_values[0] < c_2d[0]:
                highest_values[0] = c_2d[0]

            if lowest_values[1] > c_2d[1]:
                lowest_values[1] = c_2d[1]
            elif highest_values[1] < c_2d[1]:
                highest_values[1] = c_2d[1]

        return [
            lowest_values[0],
            lowest_values[1],
            highest_values[0] - lowest_values[0],
            highest_values[1] - lowest_values[1]
        ]

        
