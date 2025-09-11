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
import random
from SSHAPE_Dataset_generator.utils.errors import *
from SSHAPE_Dataset_generator.utils.geometry import *
from SSHAPE_Dataset_generator.utils.categories import create_categories_list, get_category_name
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
SCENE_MAX_Z = 1000

class DatasetRenderer:
    def __init__(self, args, rules, checkpoint=None):
        self.args = args
        self.rules = rules
        self.annotations = checkpoint["annotations"] if checkpoint else None 
        self.state = checkpoint["state"] if checkpoint else None #Stores rendering progression
        self.run = True

        if checkpoint:
            self.annotations = checkpoint["annotations"]
            self.state = checkpoint["state"]
        else:
            self.annotations = {
                "info" : self.create_info(),
                "licenses" : self.get_licenses(),
                "images" : [],
                "annotations" : [],
                "scenes" : [],
                "categories" : create_categories_list(self.rules)
            }
            self.state = {
                "img_index" : self.args.start_index,
                "shape_index" : 0
            }


        #INITIALIZE SCENE
        scene = bpy.context.scene
                     
        #create and place camera
        cam = bpy.data.cameras.new("Camera")
        cam.lens = self.rules.camera["lens"]
        self.camera_obj = bpy.data.objects.new("Camera", cam)

        scene.collection.objects.link(self.camera_obj)
        scene.camera = self.camera_obj

        #load materials
        self.load_materials()
        self.create_directory_tree()

        # Set image resolution
        render_args = bpy.context.scene.render
        render_args.resolution_x = args.images_width
        render_args.resolution_y = args.images_height

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

        # --------------------------- RENDERING LOOP ---------------------------

        print(f"Starting from img_index: {self.state['img_index']}")
        for img_index in tqdm(range(self.state["img_index"], args.num_images)):
            self.state["img_index"] = img_index
            if not self.run: break
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
            
            # Cluster will be placed in a random position inside a cuboid of size cluster_area (world rule)
            get_rand_pos = lambda i: random.uniform(-self.rules.world["cluster_area"][i] / 2, self.rules.world["cluster_area"][i] / 2)
            cluster_pos = [
                get_rand_pos(i) + self.rules.world["offset"][i] for i in range(3)
            ]

            if self.rules.world["snap_cluster_to_ground"]:
                gnd_pos, _ = self.get_ground(cluster_pos)
                cluster_pos[2] = gnd_pos[2]

            #scene metadata
            scene = {
                "objects" : [],
                "decoys" : [],
                "cluster_position" : cluster_pos
            }


            self.annotations["scenes"].append(scene)
            self.annotations["images"].append(image_info)

            scene["lights"] = self.get_lights_positions()
            scene["camera"] = self.get_camera_position()

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
        if not self.run: self.save_checkpoint()

    def stop(self, sig, frm):
        #Args are signal and frame from the signal library, not important
        print("Interrupting rendering process and creating a checkpoint file.")
        self.run = False

    def save_checkpoint(self):
        checkpoint_path = os.path.join(
            self.args.output_dir,
            f"checkpoint_{datetime.now().isoformat().split('.')[0].replace(':','-')}.json"
        )

        checkpoint = {
            "state" : self.state,
            "args" : vars(self.args),
            "rules" : self.rules.get_dict(),
            "annotations" : self.annotations
        }

        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint, f)

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
            
        rule = self.rules.camera

        pitch = random.uniform(rule["min_pitch"], rule["max_pitch"])
        yaw = random.uniform(rule["min_yaw"], rule["max_yaw"])
        distance = random.uniform(rule["min_distance"], rule["max_distance"])

        pos = [
            distance * sin(radians(yaw)),
            distance * cos(radians(yaw)),
            distance * sin(radians(pitch))
        ]

        self.camera_obj.location = pos

        rot_quat = self.camera_obj.location.to_track_quat('Z', 'Y')
        self.camera_obj.rotation_euler = rot_quat.to_euler()

        pos = self.get_offset_position(pos)
        self.camera_obj.location = pos

        return pos

    def get_lights_positions(self):
        # Chooses a random number of lights, moves them at a random position at
        # a fixed distance from the origin, and returns an array of their x, y, z
        # positions
        
        rule = self.rules.lights
        lights_number = randint(rule["min_num"], rule["max_num"])
        pos = []

        for i in range(lights_number):
            pitch = random.uniform(rule["min_pitch"], rule["max_pitch"])
            yaw = random.uniform(rule["min_yaw"], rule["max_yaw"])
            distance = random.uniform(rule["min_distance"], rule["max_distance"])

            pos.append([
                distance * sin(radians(yaw)),
                distance * cos(radians(yaw)),
                distance * sin(radians(pitch))
            ])

            pos[-1] = self.get_offset_position(pos[-1])

            #place light
            light_data = bpy.data.lights.new(name=f"Light_{i}_data", type='POINT')
            light_data.energy = random.uniform(rule["min_intensity"], rule["max_intensity"])
            light_data.shadow_soft_size = rule["radius"]

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

            if len(allowed_colors) == 0: #material is already loaded with no color variants
                return 

            for color in allowed_colors: #load all combinations of color and material
                color_rule = self.rules.colors[color]
                self.create_material(mat_rule, color_rule)

    def get_material_full_name(self, mat_name, col_name=None, degradation_level=None, degradation_color=None):
        #Get the composite material name given its attributes
        # Args:
        # - mat_name: Base name of the material (eg: metal)
        # - col_name: Name of the color (from color rules, eg: red)
        # - degradation_level: Amount of degradation applied to the material (should not exceed 3 decimal places)
        # - degradation_color: Color of the degradation

        full_name = mat_name

        if col_name is not None:
            full_name += f"_{col_name}"
        if degradation_level is not None:
            assert degradation_color is not None , "Degradation color must be specified if material is degraded"
            full_name += f"_DEGRAD:{round(degradation_level*1000)}_{degradation_color}"
            
        return full_name

    def create_material(self, mat_rule, col_rule):
        # Adds a new material to the scene
        # Args:
        # - mat_rule : Rule for the material
        # - col_rule : The color to be applied to the material.
       
        mat_name = self.get_material_full_name(mat_rule["name"], col_rule["name"])
        print("Creating composite material:", mat_name)

        bpy.data.materials.new(name=mat_name)
        mat = bpy.data.materials[mat_name]

        mat.use_nodes = True

        output_node = mat.node_tree.nodes["Material Output"]

        #create a new group for the material node tree
        group_node = mat.node_tree.nodes.new("ShaderNodeGroup")
        #copy the material node tree into the new group
        group_node.node_tree = bpy.data.node_groups[mat_rule["name"]]

        group_node.inputs["Color"].default_value = [*color_from_hex(col_rule["hex"]), col_rule["opacity"]]

        mat.node_tree.links.new(
            group_node.outputs["Shader"],
            output_node.inputs["Surface"]
        )

    def get_degraded_material(self, src_mat, degradation_level, degradation_color):
        # Creates a degraded version of the source material, adds it to the scene and returns it
        # If the material already exists, just return

        new_mat_name = self.get_material_full_name(
            src_mat.name, #Hacky but given the name already includes the color and color arg is left None it still works
            degradation_level=degradation_level,
            degradation_color=degradation_color
        )
        if new_mat_name in bpy.data.materials.keys():
            return bpy.data.materials[new_mat_name]

        mat = src_mat.copy()
        mat.name = new_mat_name

        group_node = mat.node_tree.nodes["Group"]
        group_node.inputs["Degradation"].default_value = degradation_level
        group_node.inputs["Degradation Color"].default_value = [*color_from_hex(degradation_color), 1] #RGB + Alpha

        return mat

    def populate_scene(self):
        #Places a random number of objects and decoys in random places, adds their position to annotations
        world_rule = self.rules.world
        num_objects = randint(world_rule["min_num_objects"], world_rule["max_num_objects"]) #random amount of objects
        obj_index = self.state["shape_index"]
        self.place_shapes(obj_index, num_objects, decoys=False)
        self.state["shape_index"] += num_objects

        if len(self.rules["decoys"]) > 0: 
            num_decoys = randint(world_rule["min_num_decoys"], world_rule["max_num_decoys"])
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

            degradation_level = None
            degradation_color = None

            if mat_rule is not None and mat_rule["degradation"] != "none":
                degradation_level = randrange_float(mat_rule["degradation"]["min"], mat_rule["degradation"]["max"], mat_rule["degradation"]["step"]) 
                degradation_color = mat_rule["degradation"]["color"]
                if degradation_color == "auto":
                    degradation_color = col_rule["hex"]

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
                    "file" : mat_rule["file"],
                    "degradation" : degradation_level if degradation_level is not None else 0,
                    "degradation_color" : degradation_color if degradation_color is not None else "none"
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

            object_annotations["scale"] = random_scale
            
            #apply random flips
            if shape_rule["flip"] != "none":
                self.random_flip(shape_rule["flip"])

            # Attempt random placement and rotation until the shape is correctly placed
            pos, rotation = self.try_shape_placement(obj_blender, shape_rule, object_annotations) 

            if pos is None:
                bpy.data.objects.remove(obj_blender, do_unlink=True)
                continue

            object_annotations["position"] = pos
            object_annotations["rotation"] = rotation

            #apply material and color
            if mat_rule is not None:
                material_blender = bpy.data.materials[ #Get the material object without degradation
                    self.get_material_full_name(mat_name, col_name=col_name)
                ]
                if degradation_level is not None:
                    material_blender = self.get_degraded_material(material_blender, degradation_level, degradation_color)
                
                obj_blender.data.materials.append(material_blender)

            if not decoys:
                # Add annotations
                category_id = obj_blender["inst_id"]
                obj_annotations = {
                    "id" : obj_index,
                    "category_id" : category_id,
                    "iscrowd" : 0,
                    "image_id" : self.annotations["images"][-1]["id"],
                }

                if self.args.create_bounding_boxes:
                    obj_annotations["bbox"] = self.get_bounding_box(obj_blender)

                self.annotations["annotations"].append(obj_annotations)
                self.annotations["scenes"][-1][group].append(object_annotations)

            self.apply_transform(obj_blender)

    def get_offset_position(self, pos):
        offset_pos = [0, 0, 0]
        cluster_pos = self.annotations["scenes"][-1]["cluster_position"]
        offset_pos[0] = pos[0] + cluster_pos[0]
        offset_pos[1] = pos[1] + cluster_pos[1]
        offset_pos[2] = pos[2] + cluster_pos[2]
        
        return offset_pos

    def get_ground(self, pos):
        origin = mathutils.Vector((pos[0], pos[1], SCENE_MAX_Z))
        dir = mathutils.Vector((0,0, -1))
        gnd_location, gnd_normal = project_ray_world(origin, dir, SCENE_MAX_Z * 2)

        return gnd_location, gnd_normal

    def apply_transform(self, obj, location=True, rotation=True, scale=True):
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale)

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
        
        for axis in range(3):
            angle = get_random_angle(axis) if shape_rule["random_rotation"]["snap"][axis] > 0 else 0
            rotation[axis] = angle

        return rotate(obj, rotation)
    
    def random_flip(self, flip_rule):
        #mirrors currently active object based on the flip settings it receives
        flips = (False, False, False)
        for flip_axis, flip_mode in flip_rule.items():
            if flip_mode == "random":
                flip_mode = bool(random.getrandbits(1)) #random bool
            
            idx = ["yz", "xz", "xy"].index(flip_axis)
            flips[idx] = flip_mode

        bpy.ops.transform.mirror(constraint_axis=flips)

    def snap_rotate(self, obj, gnd_norm, shape_rule):
        #Auto rotate so that the normal of  random fac

        allowed_faces = shape_rule["random_rotation"]["faces_for_snapping"]
        if allowed_faces == "all":
            face = random.choice(obj.data.polygons)
        else:
            face = obj.data.polygons[random.choice(allowed_faces)]

        angle = face.normal.angle(gnd_norm * -1) #angle between normal and flipped gnd_norm
        axis = face.normal.cross(gnd_norm * -1) #axis perpendicular to normal and flipped gnd_norm
        matrix = mathutils.Matrix.Rotation(angle, 3, axis)
        rotation_radians = matrix.to_euler()
        rotation = [degrees(r) for r in rotation_radians]

        return rotate(obj, rotation)

    def try_shape_placement(self, obj, shape_rule, obj_annotations, max_attempts=50):
        world_rule = self.rules.world
        get_random_pos = lambda: random.uniform(-world_rule["cluster_size"] / 2, world_rule["cluster_size"] / 2)
        for attempt in range(max_attempts):
            pos = [get_random_pos() for i in range(3)]
            pos = self.get_offset_position(pos)

            if shape_rule["snap_to_plane"] and not self.check_min_distance(pos, obj_annotations, ignore_z=True):
                continue
            elif not self.check_min_distance(pos, obj_annotations):
                continue

            rotation = [0, 0, 0]
            if shape_rule["snap_to_plane"] or shape_rule["random_rotation"]["auto_snap_face"]:
                obj.location.z = SCENE_MAX_Z * 2

            gnd_location, gnd_normal = self.get_ground(pos) 
            if gnd_location is None: 
                continue

            if shape_rule["random_rotation"]["auto_snap_face"]:
                rotation = self.snap_rotate(obj, gnd_normal, shape_rule)
            
            rotation = rotate(obj, shape_rule["fixed_rotation"]) #Apply fixed rotation
            rotation = self.random_rotate(obj, shape_rule) #Apply random rotation


            if shape_rule["snap_to_plane"]:
                #move object so that the lowest point of the shape touches the ground
                z_off = project_ray_world(obj.location, mathutils.Vector((0,0, -1)))[0].z - SCENE_MAX_Z * 2
                pos[2] = gnd_location.z - z_off

            obj.location = pos
            return pos, rotation

        print(f"Unable to place shape {obj_annotations['id']} after {max_attempts} attempts, the shape will" + 
            "be removed.\nThis warning is probably a result of too many shapes, too high 'min_distance' or a too" +
            "low area size.\nIf this error pops up more than once you should probably modify those values.")
        return None, None

    def check_min_distance(self, pos, obj_annotations, ignore_z = False):
        #returns true if the object respects the 'min_distance' rule from all the other shapes of the last scene
        for other_object in self.annotations["scenes"][-1]["objects"] + self.annotations["scenes"][-1]["decoys"]:
            
            pos_vec_1 = Vector(other_object["position"])
            pos_vec_2 = Vector(pos)
            if ignore_z:
                pos_vec_1.z = 0
                pos_vec_2.z = 0
            distance = get_distance(pos_vec_1, pos_vec_2) #distance between two shapes

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
