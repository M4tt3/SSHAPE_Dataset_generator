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

class RequiredAttributeNotFoundError(Exception):
    def __init__(self, attribute, rule):
        super().__init__(f"Attribute '{attribute}' is required for '{rule}'")

class DuplicateValueError(Exception):
    def __init__(self, attribute, rule):
        super().__init__(f"Attribute '{attribute}' must be unique but a duplicate value was found in '{rule}'")

class UndefinedMacroError(Exception):
    def __init__(self, macro):
        super().__init__(f"Trying to access undefined macro: '{macro}'")

class InvalidValueError(Exception):
    def __init__(self, attribute, value):
        super().__init__(f"Invalid value: '{value}' for attribute: '{attribute}'")

class UndefinedMaterialError(Exception):
    def __init__(self, material):
        super().__init__(f"Trying to apply undefined material: '{material}'")

class UndefinedColorError(Exception):
    def __init__(self, color):
        super().__init__(f"Trying to apply undefined color: '{color}'")
