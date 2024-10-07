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

import time
import bpy #type:ignore
from SSHAPE_Dataset_generator.utils import extract_args
import argparse

def setup_argparser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list_devices", default=0,
                    help="If set to 1 only list available devices")
    ap.add_argument("--benchmark_devices", default="all", nargs="+",
                    help="IDS of devices to use for benchmark")
    ap.add_argument("--benchmark_file", default="cube_diorama.blend",
                    help="File to render for benchmark")
    return ap

def set_render_args(devices_to_use="all"):
    render_args = bpy.context.scene.render
    render_args.engine = "CYCLES"
    render_args.resolution_x = 640
    render_args.resolution_y = 640
    render_args.resolution_percentage = 100

    cycles_prefs = bpy.context.preferences.addons['cycles'].preferences 
    cycles_prefs.compute_device_type = 'CUDA'
    bpy.context.scene.cycles.device = 'GPU'
    bpy.context.preferences.addons["cycles"].preferences.get_devices()

    for d in bpy.context.preferences.addons["cycles"].preferences.devices:
        if d["id"] in devices_to_use or devices_to_use == "all":
            d["use"] = 1
        else:
            d["use"] = 0

    bpy.data.worlds['World'].cycles.sample_as_light = True
    bpy.context.scene.cycles.blur_glossy = 2.0
    bpy.context.scene.cycles.samples = 32
    bpy.context.scene.cycles.transparent_min_bounces = 6
    bpy.context.scene.cycles.transparent_max_bounces = 8

def benchmark(files, devices_to_use="all"):
    #Checks how much time does it take to render all files
    #NOTE: This doesn't count the time each file takes to be loaded, only the rendering time
    overall_time = 0

    for filename in files:
        bpy.ops.wm.open_mainfile(filepath=filename)
        set_render_args(devices_to_use)
        start_time = time.time()
        while True:
            try:
                bpy.ops.render.render(write_still=False)
                break
            except Exception as e:
                print(e)
        overall_time += time.time() - start_time

    return overall_time

def get_available_devices():
    bpy.context.preferences.addons["cycles"].preferences.get_devices()
    devices = list(bpy.context.preferences.addons["cycles"].preferences.devices)
    devices.sort(key=lambda d: d["id"])
    return devices

def get_gpus_info():
    devices = get_available_devices()
    str_output = ""
    for i, dev in enumerate(devices):
        str_output += f"{i} -- ID: {dev['id']} - NAME: {dev['name']} - TYPE: {dev['type']} - ACTIVE: {dev['use']}\n"

    return str_output

if __name__ == "__main__":
    argv = extract_args()
    argparser = setup_argparser()
    args = argparser.parse_args(argv)
    gpus_info = get_gpus_info()

    if args.list_devices:
        print(f"Available devices: \n{gpus_info}")
    else:
        filename = args.benchmark_file
        devices_to_use = args.benchmark_devices

        time_taken = benchmark([filename], devices_to_use)
        print(f"""
Available devices:
{gpus_info}

Rendering benchmark on: {filename}
Using devices: {devices_to_use}
time: {time_taken}
        """)