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

