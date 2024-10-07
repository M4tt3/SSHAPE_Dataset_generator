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
from SSHAPE_Dataset_generator.rules_utils import Rules
from SSHAPE_Dataset_generator import configure_gpus
import bpy, bpy_extras  #type:ignore
from bpy import context #type:ignore
import os, pathlib, json, subprocess, sys
import signal

sys.stdout = sys.stderr

PATH = pathlib.Path(__file__).parent.resolve()
os.chdir(PATH)
print(f"Working directory is set to {PATH}")

parser = setup_argparser()

if __name__ == "__main__":
    argv = extract_args()
    args = parser.parse_args(argv)

    assert args.rules is not None, "'rules' argument is not optional"

    checkpoint = None
    rules = None

    if args.resume is not None:
        with open(args.resume, "r") as f:
            checkpoint = json.load(f)
            parser.set_defaults(**checkpoint["args"])
            args = parser.parse_args([])
            rules = Rules(checkpoint["rules"])
    elif args.config is not None:
        #override default values of parser with arguments from configuration file
        with open(args.config, "r") as f:
            parser.set_defaults(**json.load(f))
            args = parser.parse_args(argv)
    if rules is None:
        with open(args.rules, "r") as f:
            rules = Rules(json.load(f))

    assert args.base_scene is not None, "'base_scene' argument is not optional"

    if args.test_mode == 1:
        args.num_images = 1 #in testing mode only one image will be shown

    if not args.use_multiple_gpus:
        bpy.ops.wm.open_mainfile(filepath=args.base_scene)
        window = context.window_manager.windows[0]
        with context.temp_override(window=window):
            renderer = DatasetRenderer(args, rules, checkpoint=checkpoint)
            signal.signal(signal.SIGINT, renderer.stop)
            renderer.render()
    else:
        if args.resume:
            pass
        else:
            assert args.gpu_groups is not None, "'gpu_groups' argument is not optional when multi gpu rendering is enabled" 
            #do a benchmark on each gpu group to check how fast each one is
            gpu_groups = [g.split(",") for g in args.gpu_groups]
            print(gpu_groups)

            benchmark_files = [f"benchmark_files/benchmark_{i}.blend" for i in range(1, 11)]
            times = []
            for group in gpu_groups:
                group_time = configure_gpus.benchmark(benchmark_files, group)
                times.append(group_time)
            
            #subdivide the number of images according to the speed of each group
            ranges = divide_workloads(times, args.num_images)
            print(ranges)

            #start subprocesses for each group
            subprocesses = []
            for i, group_range in enumerate(ranges):
                group_args = argv.copy()
                group_args = change_args(args=group_args, 
                            start_index=group_range[0],
                            num_images=group_range[1],
                            use_multiple_gpus=0,
                            use_devices=" ".join([f'"{g}"' for g in gpu_groups[i]]),
                            gpu_groups=None
                            )
                
                
                sp = subprocess.Popen(["blender", "-b", "--python", "create_dataset.py", "--"] + group_args)
                subprocesses.append(sp)

            #wait for each subprocess
            for sp in subprocesses:
                sp.wait()

            

            




