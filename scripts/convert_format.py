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

# -------------------------------------------
import sys
import os

# Add project root (one level above SSHAPE_Dataset_generator)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
# -------------------------------------------

from SSHAPE_Dataset_generator.scripts.lib.format_converter import *

if __name__ == "__main__":
    dataset_dir = "E:\\probes_dataset\\"
    dest_dir = "E:\\probes_detection_yolo_rev2_blender\\"
    copy_images = True
    use_segmentation_bboxes = False

    converter = YoloExport(dataset_dir, dest_dir, copy_images)
    converter.export_to_yolo_detection(use_segmentation_bboxes=True)