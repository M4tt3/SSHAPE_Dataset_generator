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

from SSHAPE_Dataset_generator.errors import *
from SSHAPE_Dataset_generator.utils import intersect
import json
from typing import TypeAlias

Identifier: TypeAlias = int | str

class Rules:
    def __init__(self, path):
        rules, defaults = {}, {}

        with open(path, "r") as f:
            rules = json.load(f)
        with open("./rules_defaults.json", "r") as f:
            defaults = json.load(f)

        self.objects = RulesSection(rules, "objects", defaults)
        self.decoys = RulesSection(rules, "decoys", defaults)
        self.colors = RulesSection(rules, "colors", defaults)
        self.materials = RulesSection(rules, "materials", defaults)
        self.categories = rules["categories"]

    def __getitem__(self, id: str):
        return self.__getattribute__(id)
    
    def get_shape(self, identifier: Identifier) -> dict:
        # Returns the rule of a shape (can be object or decoy)
        # Args:
        # - identifier: id or name of the shape
        rule = self.objects[identifier]
        if rule is None:
            rule = self.decoys[identifier]
        if rule is None:
            raise Exception(f"Could not find shape matching this identification: {identifier}")
        
        return rule
    
    def get_composite_allowed_colors(self, shape_identifier: Identifier, material_identifier: Identifier) -> list[str]:
        # Returns the list of colors allowed both by a shape and a given material
        # Args:
        # - shape_identifier (str | int): id or name of the shape
        # - material_identifier (str | int): id or name of the material
        shape_allowed_colors = self.get_shape_allowed_colors(shape_identifier)

        if material_identifier is not None:
            material_allowed_colors = self.get_material_allowed_colors(material_identifier)
            return intersect(shape_allowed_colors, material_allowed_colors)
    
        return shape_allowed_colors
    
    def get_shape_allowed_colors(self, shape_identifier: Identifier) -> list[str]:
        # Returns the list of colors allowed by the shape
        # Args:
        # - shape_identifier (str | int): id or name of the shape
        shape_rule = self.get_shape(shape_identifier)
        
        allowed_colors = shape_rule["allowed_colors"]
        if allowed_colors == "none":
            return []
        elif allowed_colors == "all":
            return self.colors.get_values_list("name")
        else:
            return allowed_colors
        
    def get_material_allowed_colors(self, material_identifier: Identifier) -> list[str]:
        # Returns the list of colors allowed by the material
        # Args:
        # - material_identifier (str | int): id or name of the material
        material_rule = self.materials[material_identifier]

        if material_rule is None:
            raise Exception(f"Could not find material matching this identification: {material_identifier}")
        
        allowed_colors = material_rule["allowed_colors"]
        if allowed_colors == "none":
            return []
        elif allowed_colors == "all":
            return self.colors.get_values_list("name")
        else:
            return allowed_colors

    def get_shape_allowed_materials(self, shape_identifier: Identifier) -> list[str]:
        # Returns the list of materials allowed by the shape
        # Args:
        # - shape_identifier (str | int): id or name of the shape

        shape_rule = self.get_shape(shape_identifier)
        shape_rule = self.get_shape(shape_identifier)
        
        allowed_materials = shape_rule["allowed_materials"]
        if allowed_materials == "none":
            return []
        elif allowed_materials == "all":
            return self.materials.get_values_list("name")
        else:
            return allowed_materials

class RulesSection:
    def __init__(self, rules, section_name, defaults):
        self.name__ = section_name
        self.section__ = rules[section_name]
        check_rule(self.section__, defaults, section_name, rules["macros"])
        self.rules__ = rules

    def __getitem__(self, identifier : Identifier | None) -> dict:
        if identifier is None:
            return None
        elif isinstance(identifier, int):
            return self.get_by_id(identifier)
        elif isinstance(identifier, str):
            return self.get_by_name(identifier)
        
    def __iter__(self):
        self.iteration_counter__ = -1
        return self
    
    def __next__(self) -> dict:
        self.iteration_counter__ += 1
        if self.iteration_counter__ < len(self.section__):
            return self.section__[self.iteration_counter__]
        else:
            raise StopIteration
        
    def __len__(self) -> int:
        return len(self.section__)

    def get_by_name(self, name: str | list[str]) -> dict:
        # Returns rule with corresponding name.
        # If a list is passed it returns a list of all the rules with the corresponding name.
        rule = []
        if isinstance(name, list):
            for n in name:
                rule.append(self.search(name=n))
        else:
            rule = self.search(name=name)

        return rule
    
    def get_by_id(self, id: int | list[int]) -> dict:
        # Returns rule with corresponding id.
        # If a list is passed it returns a list of all the rules with the corresponding id.
        rule = []
        if isinstance(id, list):
            for i in id:
                rule.append(self.search(id=i))
        else:
            rule = self.search(id=id)

        return rule

    def search(self, **kwargs) -> dict:
        # Returns rule matching all given attributes.
        for rule_element in self.section__:
            for kw, val in kwargs.items():
                if rule_element[kw] != val:
                    break
                return rule_element
        return None
    
    def get_values_list(self, attribute: str) -> list[dict]:
        # Returns a list all the values of the given attribute in the section.
        val_list = []
        for rule in self.section__:
            val_list.append(rule[attribute])

        return val_list

def complete_rules(rules: Rules, defaults: dict):
    macros = rules.get("macros", None)
    rules.pop("macros")
    check_rule(rules["objects"] + rules["decoys"], defaults, "shape", macros)
    check_rule(rules["materials"], defaults, "material", macros)
    check_rule(rules["colors"], defaults, "color", macros)

def check_rule(rule: dict, defaults: dict, rule_name: str, macros: dict):
    default = defaults[rule_name]
    #list of dicts, unique values already used.
    in_use_uniques = []

    for element in rule:
        element_uniques = {} #stores unique values for this element
        for attribute in default.keys():
            value = element.get(attribute, None)
            default_value = default[attribute]
            #Substitute macros
            if type(value) == str and value.startswith("$"):
                macro_name = element[attribute][1:]
                if macros is not None and macros.get(macro_name, None) is not None:
                    element[attribute] = macros[macro_name]
                else:
                    raise UndefinedMacroError(macro_name)

            #Check for required values
            if type(default_value) == str and default_value.split(";")[0] == "REQUIRED" and value is None:
                raise RequiredAttributeNotFoundError(attribute, rule_name)
            
            #Add dynamic default values
            elif type(default_value) == str and default_value.startswith("=") and value is None:
                str_func = default_value[1:]
                if ";" in str_func:
                    str_func = str_func.split(";")[0]
                func = eval(str_func)
                element[attribute] = func(element)

            #Add static default values
            elif value is None:
                element[attribute] = default_value
            elif type(value) == dict:
                check_rule([element[attribute]], defaults, attribute, macros)

            #If value is unique add it to 'element_uniques'
            try:
                if default_value.split(";")[1] == "UNIQUE":
                    element_uniques[attribute] = element[attribute]
            except IndexError: pass #In case of no ';', which would trigger an index out of bounds exception
            except AttributeError: pass #In case of the value not being a string

        #Check if unique values used are duplicate
        for unique_attr in element_uniques.keys():
            for in_use in in_use_uniques:
                if element_uniques[unique_attr] == in_use[unique_attr]:
                    raise DuplicateValueError(unique_attr, rule_name)
                
        in_use_uniques.append(element_uniques)