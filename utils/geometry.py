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

from SSHAPE_Dataset_generator.utils import *
import random
from math import radians, degrees
from mathutils import Vector, Matrix, Euler #type:ignore
import numpy as np
import bpy
from icecream import ic

def rotate(obj, angle):
    # rotates blender object, rotation is relativeand expressed in degrees
    # returns object orientation after rotation
    orientation = obj.rotation_euler
    orientation[0] += angle[0]
    orientation[1] += angle[1]
    orientation[2] += angle[2]
    set_orienation(obj, orientation)

    return (
        orientation[0],
        orientation[1],
        orientation[2]
    )

def set_orienation(obj, angle):
    #rotates blender object, rotation is absolute and expressed in degrees
    obj.rotation_euler = Euler(
        (radians(angle[0]),
        radians(angle[1]),
        radians(angle[2])),
        "XYZ"
    )
    
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

def project_ray_world(origin: Vector, direction: Vector, distance = 10**10):
    # Projects a ray from origin along direction until it reaches the given distance or hits an object
    # Returns: location, normal (if not hit returns None, None)
    direction = direction.normalized()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    result, location, normal, index, object, matrix = bpy.context.scene.ray_cast(
        depsgraph,
        origin,
        direction,
        distance=distance
    )

    if result:
        return location, normal
    else:
        return None, None

