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

#blender
import bpy, bpy_extras, mathutils #type: ignore
from bpy import context #type: ignore
from mathutils import Vector, Color #type: ignore

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
        render_args.resolution_percentage = 100

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

    def create_directory_tree(self):
        os.makedirs(self.args.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.args.output_dir, self.args.split), exist_ok=True)
        os.makedirs(os.path.join(self.args.output_dir, self.args.split, "images"), exist_ok=True)

    def save_annotations(self):
        prefix = self.args.filename_prefix
        filename = f"{prefix + '_' if prefix is not None else ''}{self.args.split}_annotations.json"
        with open(os.path.join(self.args.output_dir, self.args.split, filename), "w") as f:
            json.dump(self.annotations, f)

    def render(self):
        args = self.args
        rules = self.rules

        self.annotations = {
            "info" : self.create_info(),
            "licenses" : self.get_licenses(),
            "images" : [],
            "annotations" : [],
            "scenes" : [],
            "categories" : {
                "material" : rules["materials"],
                "color" : rules["colors"],
                "object" : rules["objects"],
                "decoy" : rules["decoys"]
            }
        }

        self.state = {
            "img_index" : 0,
            "shape_index" : 0
        }


        # --------------------------- RENDERING LOOP ---------------------------


        for img_index in tqdm(range(args.num_images)):
            prefix = args.filename_prefix
            img_filename = f"{prefix + '_' if prefix is not None else ''}{img_index:010d}.png" #TODO: add support for other file formats
            image_info = {
                "id" : img_index,
                "file_name" : img_filename,
                "height" : args.images_height,
                "width" : args.images_width,
                "date_captured" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "license" : -1
            }

            scene = {
                "camera_position" : self.get_camera_position(),
                "lights" : self.get_lights_positions(),
                "objects" : [],
                "decoys" : []
            }

            self.annotations["scenes"].append(scene)

            self.place_shapes()

            render_args = bpy.context.scene.render
            render_args.filepath = os.path.abspath(
                os.path.join(args.output_dir, args.split, "images", img_filename)
            )

            while not args.test_mode:
                try:
                    bpy.ops.render.render(write_still=True)
                    break
                except Exception as e:
                    print(e)

            self.clear_scene()

        self.save_annotations()

    def create_info(self):
        return {
            "description" : "SSHAPE Dataset, a fully synthetic dataset for computer vision",
            "url" : "", #TODO
            "version" : "pre-release",
            "contibutor" : "Matteo Bicchi",
            "date_created" : datetime.now().isoformat().split("T")[0]
        }

    def get_licenses(self):
        return []   #TODO

    def get_camera_position(self):
        pitch = randint(self.args.min_camera_pitch, self.args.max_camera_pitch)
        yaw = randint(self.args.min_camera_yaw, self.args.max_camera_yaw)

        pos = [
            self.args.camera_distance * sin(radians(yaw)),
            self.args.camera_distance * cos(radians(yaw)),
            self.args.camera_distance * sin(radians(pitch))
        ]

        #move camera into position and focus it on the origin
        self.camera_obj.location = tuple(pos)

        rot_quat = self.camera_obj.location.to_track_quat('Z', 'Y')
        self.camera_obj.rotation_euler = rot_quat.to_euler()
        self.camera_obj.location = rot_quat @ mathutils.Vector((0.0, 0.0, self.args.camera_distance))

        return pos

    def get_lights_positions(self):
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

            light_object.location = tuple(pos[-1])

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
        for mat_rule in self.rules["materials"]:
            #load material file
            filename = os.path.join(self.args.materials_dir, mat_rule["file"], "NodeTree", mat_rule["name"])
            print(f"Loading material: {filename}")
            bpy.ops.wm.append(filename=filename)

            allowed_colors = []
            if mat_rule["allowed_colors"] == "all":
                allowed_colors = self.rules["colors"]
            elif mat_rule["allowed_color"] == "none":
                pass #TODO: add support for materials with no colors applied
            elif type(mat_rule["allowed_colors"]) == list:
                allowed_colors = [self.get_rule("colors", name=col) for col in mat_rule["allowed_colors"]]

            for color_rule in allowed_colors:
                #add new material to the scene
                bpy.ops.material.new()
                mat = mat = bpy.data.materials['Material']
                mat.name = f"{mat_rule['name']}_{color_rule['name']}"
                
                output_node = mat.node_tree.nodes["Material Output"]

                #create a new group for the material node tree
                group_node = mat.node_tree.nodes.new("ShaderNodeGroup")
                #copy the material node tree into the new group
                group_node.node_tree = bpy.data.node_groups[mat_rule["name"]]


                group_node.inputs["Color"].default_value = [*color_from_hex(color_rule["hex"]), color_rule["opacity"]]

                mat.node_tree.links.new(
                    group_node.outputs["Shader"],
                    output_node.inputs["Surface"]
                )


    def place_shapes(self):
        num_objects = randint(self.args.min_num_objects, self.args.max_num_objects) #random amount of objects and decoys

        obj_index = self.state["shape_index"]

        for obj_index in range(obj_index, num_objects + obj_index):

            shape_rule = random.choice(self.rules["objects"]) #random shape
            
            material, color = self.choose_random_appearance(shape_rule)

            object_annotations = {
                "id" : obj_index,
                "shape" : {
                    "id" : shape_rule["id"],
                    "name" : shape_rule["name"],
                    "file" : shape_rule["file"],
                    "min_distance" : shape_rule["min_distance"]
                },
                "material" : {
                    "id" : material["id"],
                    "name" : material["name"],
                    "file" : material["file"]
                },
                "color" : {
                    "id" : color["id"],
                    "name" : color["name"],
                    "hex" : color["hex"]
                },
            }

            #add object to scene
            obj_blender = self.add_shape(self.args.objects_dir, object_annotations)
            #perform random scale if needed
            if shape_rule["scaling"] != "none":
                random_scale = self.random_scale(obj_blender, shape_rule)
            #apply fixed rotation and random rotation if needed
            rotate(obj_blender, shape_rule["fixed_rotation"])
            random_rotation = [0, 0, 0]
            if shape_rule["random_rotation"] != "none":
                random_rotation = self.random_rotate(obj_blender, shape_rule)

            object_annotations["scale"] = random_scale #apply random scaling to scene annotations
            object_annotations["rotation"] = [random_rotation[i] + shape_rule["fixed_rotation"][i] for i in range(3)] #sum random and fixed rotation

            bpy.context.view_layer.objects.active = obj_blender
            bpy.ops.object.transform_apply(rotation=True, scale=True)

            pos = self.try_shape_placement(obj_blender, shape_rule, object_annotations)
            object_annotations["position"] = pos

            material_blender = bpy.data.materials[f"{material['name']}_{color['name']}"]
            obj_blender.data.materials.append(material_blender)

            self.annotations["scenes"][-1]["objects"].append(object_annotations)

            
            

        self.state["shape_index"] += num_objects

    def choose_random_appearance(self, shape):
        #returns random material and color rules

        material = None 
        if shape["allowed_materials"] == "all":
            material = random.choice(self.rules["materials"])
        if type(shape["allowed_materials"]) == list and len(shape["allowed_materials"]) > 0:
            mat_name = random.choice(shape["allowed_materials"])
            material = self.get_material(mat_name)
            if material is None:
                raise UndefinedMaterialError(mat_name)
            
        #create an array of colors allowed by the shape rule
        shape_allowed_colors = shape["allowed_colors"]
        if shape_allowed_colors == "all":
            shape_allowed_colors = [c["name"] for c in self.rules["colors"]]
        elif shape_allowed_colors == "none" or len(shape_allowed_colors) == 0:
            return material, None 

        #create an array of colors allowed by the material rule, if material is None allow all colors
        mat_allowed_colors = []
        if material is None:
            mat_allowed_colors = "all"
        else:
            mat_allowed_colors = material["allowed_colors"]

        if mat_allowed_colors == "all":
            mat_allowed_colors = [c["name"] for c in self.rules["colors"]]
        elif mat_allowed_colors == "none" or len(mat_allowed_colors) == 0:
            return material, None 

        color_name = random.choice(intersect(mat_allowed_colors, shape_allowed_colors))
        color = self.get_color(color_name)

        if color is None:
            raise UndefinedMaterialError(color_name)
        
        return material, color

    def get_material(self, name: str) -> dict:
        #finds material by name
        for mat in self.rules["materials"]:
            if mat["name"] == name:
                return mat
        
        return None
    
    def get_color(self, name: str) -> dict:
        #finds color by name
        for col in self.rules["colors"]:
            if col["name"] == name:
                return col
        
        return None
    
    def get_rule(self, category, **kwargs):
        for rule in self.rules[category]:
            valid=True
            for kw in kwargs.keys():
                if rule[kw] != kwargs[kw]:
                    valid = False

            if valid:
                return rule
            
        return None
    
    def add_shape(self, shape_dir, object_annotation):
        #add a shape to the scene
        name = object_annotation["shape"]["name"]
        filename = os.path.join(shape_dir, object_annotation["shape"]["file"], "Object", name)
        bpy.ops.wm.append(filename=filename)

        blender_obj = bpy.data.objects[name]
        blender_obj.name = f"OBJECT_{name}_{object_annotation['id']}"

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

    def random_rotate(self, obj, shape):
        rotation = [0, 0, 0]
        #TODO: Make this function better, add support for a change of AUTO_ROTATION_VECT, add caching possibility and the option to limit auto snap range
        if shape["random_rotation"]["auto_snap_face"]:
            #Auto rotate so that the normal of a random face is aligned to AUTO_ROTATION_VECT
            normal = random.choice(obj.data.polygons).normal
            angle = normal.angle(AUTO_ROTATION_VECT)
            axis = normal.cross(AUTO_ROTATION_VECT)
            matrix = mathutils.Matrix.Rotation(angle, 3, axis)
            rotation_radians = matrix.to_euler()
            rotation = [degrees(k) for k in rotation_radians]
        else:
            get_random_angle = lambda axis: random.randrange(
                start=shape["random_rotation"]["min_bounds"][axis],
                stop=shape["random_rotation"]["max_bounds"][axis],
                step=shape["random_rotation"]["snap"][axis],
            )

            for axis in range(3):
                angle = get_random_angle(axis) if shape["random_rotation"]["snap"][axis] > 0 else 0
                rotation[axis] = angle

        rotate(obj, rotation)
        return rotation
            

    def try_shape_placement(self, obj, shape_rule, obj_annotations, max_attempts=50):
        for attempt in range(max_attempts):
            get_random_pos = lambda: random.uniform(self.args.padding - self.args.area_size / 2, self.args.area_size / 2 - self.args.padding)
            pos = [get_random_pos() for i in range(3)] #this is the centroid position
            origin = mathutils.Vector((0, 0, 0))
            if shape_rule["snap_to_plane"] == True:
                origin = mathutils.Vector((0,0,0))
                dir = mathutils.Vector((0,0,-1))
                hit, point, face, index = obj.ray_cast(origin, dir)
                pos[2] = point.length
                    
            if self.check_min_distance(pos, obj_annotations):
                obj.location = pos
                return pos
            
        return None
    
    def check_min_distance(self, pos, obj_annotations):
        #returns true if the object respects the 'min_distance' rule from all the other object of the last scene
        for other_object in self.annotations["scenes"][-1]["objects"]:
            distance = get_distance(Vector(other_object["position"]), Vector(pos)) #distance between two objects

            #minimum distances scaled to the max scaling along an axis of each object
            min_distance_1 = other_object["shape"]["min_distance"] * max(*other_object["scale"])
            min_distance_2 = obj_annotations["shape"]["min_distance"] * max(*obj_annotations["scale"])

            if distance < min_distance_1 + min_distance_2:
                return False
            
        return True


            
