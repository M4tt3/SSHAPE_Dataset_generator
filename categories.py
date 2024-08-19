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

from SSHAPE_Dataset_generator.rules_utils import Rules

def create_categories_list(rules: Rules) -> list:
    # Creates a list of all the possible categories
    # When using 'ignore_materials' two same shapes with different materials will not be considered
    # as different categories, the same applies to 'ignore_colors'.
    # Args:
    # - rules (rules_utils.Rules): rules of the dataset

    ignore_color = rules["categories"]["ignore_color"]
    ignore_material = rules["categories"]["ignore_material"]
    categories = set()

    for object in rules.objects:
        shape_name = object["name"]
        allowed_materials = rules.get_shape_allowed_materials(shape_name)
        if ignore_material and ignore_color or len(allowed_materials) == 0:
            categories.add(
                get_category_name(shape=shape_name)
            )
        elif not ignore_material and ignore_color:
            for material_name in allowed_materials:
                categories.add(
                    get_category_name(
                        shape=shape_name,
                        material=material_name
                    )
                )
        elif ignore_material and not ignore_color:
            for material_name in allowed_materials:
                allowed_colors = rules.get_composite_allowed_colors(shape_name, material_name)
                if len(allowed_colors) == 0:
                    categories.add(
                        get_category_name(
                            shape=shape_name,
                            material=material_name
                        )
                    )
                else:
                    for color_name in allowed_colors:
                        categories.add(
                            get_category_name(
                                shape=shape_name,
                                color=color_name
                            )
                        ) 
        elif not ignore_material and not ignore_color:
            for material_name in allowed_materials:
                allowed_colors = rules.get_composite_allowed_colors(shape_name, material_name)
                if len(allowed_colors) == 0:
                    categories.add(
                        get_category_name(
                            shape=shape_name,
                            material=material_name
                        )
                    ) 
                else:
                    for color_name in allowed_colors:
                        
                        categories.add(
                            get_category_name(
                                shape=shape_name,
                                material=material_name,
                                color=color_name
                            )
                        )

    return list(categories)

def get_category_name(shape, material=None, color=None) -> str:
    # Returns the category name given the properties of an object
    # Args:
    # - shape (str): shape name
    # - material (str): material name
    # - color (str): color name

    prefix = ""
    if color:
        prefix += f"{color} "
    if material:
        prefix += f"{material} "

    return prefix + shape
            