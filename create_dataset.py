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
from SSHAPE_Dataset_generator.render import DatasetRenderer
import bpy, bpy_extras  #type:ignore
from bpy import context #type:ignore
import os, pathlib, json

PATH = pathlib.Path(__file__).parent.resolve()
os.chdir(PATH)
print(f"Working directory is set to {PATH}")

parser = setup_argparser()

if __name__ == "__main__":
    argv = extract_args()
    args = parser.parse_args(argv)
    rules, defaults = {}, {}

    assert args.rules is not None, "'rules' argument is not optional"

    if args.config is not None:
        #override default values of parser with arguments from configuration file
        with open(args.config, "r") as f:
            parser.set_defaults(**json.load(f))
            args = parser.parse_args(argv)

    with open(args.rules, "r") as f:
        rules = json.load(f)
    with open("rules_defaults.json", "r") as f:
        defaults = json.load(f)

    #Sets to default unset values, checks for required and unique values and substitutes macros
    complete_rules(rules, defaults)

    if args.test_mode == 1:
        args.num_images = 1 #in testing mode only one image will be shown

    if args.base_scene is not None:
        bpy.ops.wm.open_mainfile(filepath=args.base_scene)
        window = context.window_manager.windows[0]
        with context.temp_override(window=window):
            renderer = DatasetRenderer(args, rules)
            renderer.render()



