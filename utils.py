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

import argparse, sys, random
from SSHAPE_Dataset_generator.errors import *
from math import radians
import mathutils #type:ignore
from mathutils import Vector, Matrix, Euler #type:ignore

def setup_argparser():
    ap = argparse.ArgumentParser()
    # --------------- OUTPUT OPTIONS ---------------
    ap.add_argument("--output_dir", default='./output',
                    help="The directory in which the dataset is put.")
    ap.add_argument("--filename_prefix", default=None,
                    help="The prefix to be put in front of every generated file.")
    ap.add_argument("--split", default="train",
                    help="The dataset split.")
    ap.add_argument("--num_images", default=1, type=int,
                    help="How many images will be rendered.")
    ap.add_argument("--images_width" , default=640, type=int,
                    help="Width (in pixels) of every image.")
    ap.add_argument("--images_height" , default=640, type=int,
                    help="Height (in pixels) of every image.")
    ap.add_argument("--use_gpu", default=1, type=int,
                    help="Whether or not to use gpu fo rendering (1 for yes, 0 for no).")
    #ap.add_argument("--image_format", default="jpg",
    #                help="Saving format for images, must be supported bu OpenCV")
    ap.add_argument("--create_segmentations", default=1, type=int,
                    help="Whether or not to create segmentation ground truth data (1 for yes, 0 for no).")
    ap.add_argument("--create_depth", default=1, type=int,
                    help="Whether or not to create depth ground truth data (1 for yes, 0 for no).")
    ap.add_argument("--create_bounding_boxes", default=1, type=int,
                    help="Whether or not to create bounding boxes ground truth data (1 for yes, 0 for no).")
    # --------------- INPUT OPTIONS ---------------
    ap.add_argument("--materials_dir", default="./materials",
                    help="Directory in which materials are stored (in .blend format)")
    ap.add_argument("--objects_dir" , default="./objects",
                    help="Directory in which objects are stored (in .blend format).")
    ap.add_argument("--rules", default="./rules.json",
                    help="Rules path, see docs on how to set them.")
    ap.add_argument("--decoys_dir", default="./decoys",
                    help="Directory in which decoys are stored (in .blend format).")
    ap.add_argument("--base_scene", default=None,
                    help="Base blender scene, objects coordinates are relative to its origin, the working" + 
                    "area is centerd on the origin on x and y starts on z=0.")
    #ap.add_argument("--resume", default=None,
    #                help="Path of the checkpoint file to resume a paused rendering.")
    ap.add_argument("--config", default=None,
                    help="Config file (JSON) to use instead of command line arguments")
    # --------------- SETTINGS ---------------
    ap.add_argument("--area_size", default=3, type=int,
                    help="Size of the working area.")
    ap.add_argument("--min_num_objects", default=2, type=int,
                    help="Minimum number of objects in every scene.")
    ap.add_argument("--max_num_objects", default=6, type=int,
                    help="Maximum number of objects in every scene.")
    ap.add_argument("--min_num_decoys", default=0, type=int,
                    help="Minimum number of decoys in every scene.")
    ap.add_argument("--max_num_decoys", default=2, type=int,
                    help="Maximum number of decoys in every scene.")
    ap.add_argument("--min_num_lights", default=1, type=int,
                    help="Minimum number of decoys in every scene.")
    ap.add_argument("--max_num_lights", default=3, type=int,
                    help="Maximum number of lights in every scene.")
    ap.add_argument("--camera_distance", default=2.5, type=float,
                    help="Distance between the camera and the origin.")
    ap.add_argument("--min_camera_pitch", default=30, type=int,
                    help="Minimum angle (in degrees) of rotation  of the camera along the y axis.")
    ap.add_argument("--max_camera_pitch", default=80, type=int,
                    help="Maximum angle (in degrees) of rotation  of the camera along the y axis.")
    ap.add_argument("--min_camera_yaw", default=0, type=int,
                    help="Minimum angle (in degrees) of rotation  of the camera along the z axis.")
    ap.add_argument("--max_camera_yaw", default=0, type=int,
                    help="Maximum angle (in degrees) of rotation  of the camera along the z axis.")
    ap.add_argument("--padding", default=0.6, type=float,
                    help="Minimum distance between the center projection on the base plane of every "+
                         "object and the plane boundaries.")
    ap.add_argument("--min_pixels_per_object", default=200, type=int,
                    help="Minimum pixels visible for every object, if this condition is not met the " +
                         "scene is discarded and recreated.")
    ap.add_argument("--lights_jitter", default=0.4, type=float,
                    help="Max amount of random movement from the default position of each light.")
    ap.add_argument("--lights_distance", default=3, type=float,
                    help="Distance at which the lights are placed.")
    ap.add_argument("--lights_intensity", default=60, type=float,
                    help="Intensity of lights.")
    ap.add_argument("--test_mode", default=0, type=int,
                    help="Sets testing mode (1 for yes, 0 for no), see docs 'Testing mode'")
    
    return ap

def extract_args(input_argv=None):
    """
    Pull out command-line arguments after "--". Blender ignores command-line flags
    after --, so this lets us forward command line arguments from the blender
    invocation to our own script.
    """
    if input_argv is None:
        input_argv = sys.argv
    output_argv = []
    if '--' in input_argv:
        idx = input_argv.index('--')
        output_argv = input_argv[(idx + 1):]
    return output_argv

def complete_rules(rules, defaults):
    macros = rules.get("macros", None)
    rules.pop("macros")
    check_rule(rules["objects"] + rules["decoys"], defaults, "shape", macros)
    check_rule(rules["materials"], defaults, "material", macros)
    check_rule(rules["colors"], defaults, "color", macros)

def check_rule(rule, defaults, rule_name, macros):
    default = defaults[rule_name]
    #list of dicts, unique values already used
    in_use_uniques = []

    for element in rule:
        element_uniques = {} #stores unique values for this element
        for attribute in default.keys():
            value = element.get(attribute, None)
            default_value = default[attribute]
            #Substitute macros
            if type(value) == str and value.startswith("$"):
                macro_name = element[attribute][1:]
                if macros is not None and macros.get(macro_name, None) is not None:
                    element[attribute] = macros[macro_name]
                else:
                    raise UndefinedMacroError(macro_name)

            #Check for required values
            if type(default_value) == str and default_value.split(";")[0] == "REQUIRED" and value is None:
                raise RequiredAttributeNotFoundError(attribute, rule_name)
            
            #Add dynamic default values
            elif type(default_value) == str and default_value.startswith("=") and value is None:
                str_func = default_value[1:]
                if ";" in str_func:
                    str_func = str_func.split(";")[0]
                func = eval(str_func)
                element[attribute] = func(element)

            #Add static default values
            elif value is None:
                element[attribute] = default_value
            elif type(value) == dict:
                check_rule([element[attribute]], defaults, attribute, macros)

            #If value is unique add it to 'element_uniques'
            try:
                if default_value.split(";")[1] == "UNIQUE":
                    element_uniques[attribute] = element[attribute]
            except IndexError: pass #In case of no ';', which would trigger an index out of bounds exception
            except AttributeError: pass #In case of the value not being a string

        #Check if unique values used are duplicate
        for unique_attr in element_uniques.keys():
            for in_use in in_use_uniques:
                if element_uniques[unique_attr] == in_use[unique_attr]:
                    raise DuplicateValueError(unique_attr, rule_name)
                
        in_use_uniques.append(element_uniques)

def intersect(list1, list2):
    return list(set(list1) & set(list2))

def rotate(obj, angle):
    #rotates blender object, rotation is absolute and expressed in degrees
    obj.rotation_euler = (radians(angle[0]), radians(angle[1]), radians(angle[2]))
    
def randrange_float(min, max, step):
    #similar to random.randrange() but works with floating point values
    range = [min]
    while range[-1] < max:
        range.append(range[-1] + step)
    
    return random.choice(range)

def get_random_scaling_factors(amount, min, max, step, max_delta=None):
    factors = []
    for i in range(amount):
        factors.append(randrange_float(min, max, step))
    
    #check for max delta if needed
    if max_delta is not None:
        for fac1 in factors:
            for fac2 in factors:
                if abs(fac1 - fac2) > max_delta:
                    try:
                        return get_random_scaling_factors(amount, min, max, step, max_delta)
                    except RecursionError:
                        print("Ignoring 'max_delta' in random scaling due to RecursionError \n"+
                              "This error can be caused by having a too low 'step' value and/or a too low 'max_scaling_difference', "+
                              "if this warning pops up more than once you should probably modify those values.")
                
    return factors

def get_distance(vect1, vect2):
    #get distance from 2 points located by vectors
    return (vect1 - vect2).length

def check_point_intersection(point, bbox_origin, bbox_size, bbox_rotation):
    #checks if the point lands inside the given bounding box
    
    rot_matrix = bbox_rotation.to_matrix()
    #vector connecting the point to the origin of the bbox
    #transformed to global space
    vector_origin_point = (point - bbox_origin) @ rot_matrix
    
    if vector_origin_point > bbox_size.length:
        return False
    
    for axis in range(3):
        if abs(bbox_size[axis] / 2) < abs(vector_origin_point[axis]):
            return False
    return True

def get_box_corners(origin, size, rotation):
    #returns a list of vectors pointing from the origin to each corner of the box
    
    rot_matrix = rotation.to_matrix()
    corners = []
    
    for x_sign in [-1, 1]:
        for y_sign in [-1, 1]:
            for z_sign in [-1, 1]:
                mat = Matrix([
                    [x_sign, 0, 0],
                    [0, y_sign, 0],
                    [0, 0, z_sign]
                ])
                corners.append(size / 2 @ mat @ rot_matrix.inverted() + origin)
                
    return corners

def check_box_intersection(bbox1, bbox2):
    """
    For each bbox expects a tuple:
    (
        origin : Mathutils.Vector,
        size: Mathutils.Vector,
        rotation: Mathutils.Euler
    )
    """
    radius1 = (bbox1[1] / 2).length
    radius2 = (bbox2[1] / 2).length
    
    if get_distance(bbox1[0], bbox2[0]) > radius1 + radius2:
        #if the distance of the 2 boxes origin is greater than the sum of the radiuses
        #of the circumscribed spheres there can't be any intersection
        return False
    
    for axis in range(3):
        if (bbox1[0] - bbox2[0])[axis] < min(bbox1[1][axis], bbox2[1][axis]):
            return True
    
    corners1 = get_box_corners(*bbox1)
    for corner in corners1:
        if check_point_intersection(corner, *bbox2):
            return True
        
    corners2 = get_box_corners(*bbox2)
    for corner in corners2:
        if check_point_intersection(corner, *bbox2):
            return True
        
    return False

def color_from_hex(h : str) -> mathutils.Color:
    if h.startswith("#"):
        h = h[1:]

    color = tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) #color in rgb 0-1 format
    color_srgb = mathutils.Color(color) #color in srgb format
    return mathutils.Color.from_srgb_to_scene_linear(color_srgb)