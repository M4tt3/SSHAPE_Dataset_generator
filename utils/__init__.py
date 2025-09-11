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


from icecream import ic
import mathutils

def intersect(list1, list2):
    return list(set(list1) & set(list2))

def color_from_hex(h : str) -> mathutils.Color:
    if h.startswith("#"):
        h = h[1:]

    color = tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4)) #color in rgb 0-1 format
    color_srgb = mathutils.Color(color) #color in srgb format
    return mathutils.Color.from_srgb_to_scene_linear(color_srgb)

