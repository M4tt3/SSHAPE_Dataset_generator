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

import argparse, sys, random, pathlib
from SSHAPE_Dataset_generator.utils.errors import *
from math import radians
import mathutils #type:ignore
from mathutils import Vector, Matrix, Euler #type:ignore
import numpy as np
from icecream import ic

# Argparse attributes that hold filesystem paths and therefore need base-dir resolution.
# NOTE: 'config' and 'resume' are deliberately excluded: they are always supplied on the
# command line, so they're resolved separately against the invocation cwd before this list
# is used (see create_dataset.py).
PATH_ARG_NAMES = ("output_dir", "materials_dir", "objects_dir", "decoys_dir", "rules", "base_scene")

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
    ap.add_argument("--resume", default=None,
                    help="Path of the checkpoint file to resume a paused rendering.")
    ap.add_argument("--config", default=None,
                    help="Config file (JSON) to use instead of command line arguments")
    ap.add_argument("--test_mode", default=0, type=int,
                    help="Sets testing mode (1 for yes, 0 for no), see docs 'Testing mode'.")
    
    # --------------- RENDERING OPTIONS ---------------

    ap.add_argument("--use_devices", default="all", nargs="+",
                    help="Which devices to use for rendering, separate each one with a space." + 
                    "Incompatible with --use_multiple_gpus.")

    ap.add_argument("--use_multiple_gpus", default=0, type=int,
                    help="Wether or not to divide the rendering across multiple gpus (enable "+
                    "with 1, disable with 0.")

    ap.add_argument("--gpu_groups", default=None, nargs="+",
                    help="IDs of devices across which the rendering must be divided, see docs" +
                    "'Multi gpu rendering' for more info.")

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

def resolve_path(path, base_dir):
    """
    Resolves 'path' into an absolute path.
    Args:
    - path: A path, either absolute or relative. None/empty values are returned unchanged
      (used for optional path arguments such as 'base_scene' or 'resume').
    - base_dir: Directory an already-relative 'path' is resolved against. Ignored if
      'path' is already absolute.
    """
    if not path:
        return path

    p = pathlib.Path(path)
    if p.is_absolute():
        return str(p)

    return str((pathlib.Path(base_dir) / p).resolve())

def resolve_args_paths(args, base_dir):
    """
    Resolves every path-valued attribute in 'args' (see PATH_ARG_NAMES) in place, relative
    to 'base_dir'. Use the invocation's current working directory as 'base_dir' when no
    config file is used, or the config file's containing directory when one is used, so
    that relative paths written inside a config file are resolved relative to that file
    rather than to whatever the process's cwd happens to be.
    """
    for name in PATH_ARG_NAMES:
        setattr(args, name, resolve_path(getattr(args, name, None), base_dir))
    return args

def change_args(args, **kwargs):
    for (arg_name, new_value) in kwargs.items():
        arg_name = f"--{arg_name}"
        try:
            arg_i = args.index(arg_name)
            if new_value is None:
                for arg_end in range(arg_i + 1, len(args) + 1):
                    if arg_end == len(args) or args[arg_end].startswith("--"):
                        del args[arg_i:arg_end]
                        break
            else:
                for arg_end in range(arg_i + 1, len(args) + 1):
                    if arg_end == len(args) or args[arg_end].startswith("--"):
                        args[arg_i + 1] = str(new_value)
                        if arg_i + 2 < arg_end:
                            del args[arg_i + 2:arg_end]
                        break
        except ValueError:
            args += [arg_name, str(new_value)]

    return args

def divide_workloads(times, num_images):
    #Divide the images in ranges inversely proportional to the time each device takes to render
    product = np.prod(times)
    combinations_sum = 0
    for i in range(len(times)):
        times_without_i = times.copy()
        times_without_i.pop(i)
        combinations_sum += np.prod(times_without_i)
    
    k = product/combinations_sum
    ranges = []
    lower_limit = 0
    for time in times:
        upper_limit = round(lower_limit + (k / time) * num_images)
        ranges.append([
            lower_limit,
            upper_limit
        ])
        lower_limit = upper_limit + 1

    ranges[-1][1] = num_images
    return ranges


