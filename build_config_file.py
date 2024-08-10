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

-------------------------------------------------------------------------------------------------------------------

Setup a configuration file

First argument must be a path to the configuration file.
Can be followed by arguments for 'create_dataset.py' to save them,
otherwise default values will be used.

"""

from SSHAPE_Dataset_generator.utils import setup_argparser, extract_args
import sys, json
from pprint import pprint


if __name__ == "__main__":
    argparser = setup_argparser()
    output_file = None
    
    argv = extract_args()

    try:
        output_file = argv[0]
    except IndexError:
        pass
    finally:
        if output_file == None or output_file.startswith("-"):
            raise Exception("You must specify an output file")

        

    args = argparser.parse_args(argv[1:])

    with open(output_file, "w") as f:
        pprint(args.__dict__)
        print(f"Writing this configuration to {output_file}")
        json.dump(args.__dict__, f, indent=4)
    

