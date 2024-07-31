# How to setup rules files

They are used to specify rules on how object must be placed and rendered, for example you could set what materials can be used for certain shapes, they are stored as **json files**. Every dataset needs some basic rules to define colors, identifiers and materials but lots of different rules can be applied to make the dataset more diverse and robust.

You can find an example structure at "docs/rules_example.json".

## Structure
Constraints file are divided in 5 sections:
- **`objects` [\<shape>]**: Specifies properties for objects, see [Shape attributes (objects and decoys)](##+Shape+attributes+(objects+and+decoys)) below.
- **`decoys` [\<shape>]**: Specifies properties for decoys, see [Shape attributes (objects and decoys)](##+Shape+attributes+(objects+and+decoys)) below.
- **`materials` [\<material>]**: Specifies properties for materials, see [Materials attributes](##+Materials+attributes) below.
- **`colors` [\<color>]**: Specifies properties for colors, see [Colors attributes](##+Colors+attributes) below.
- **`macros` [\<macro>]**: Specifies macros to easily save common configurations, see [Macros](##+Macros) below.

## Shape attributes (objects and decoys):
- **`id` [int]** (required and unique): An integer which uniquely identifies the shape.
- **`name` [str]** (*default*: matches **`file`**, unique): A name for the shape, can act as a category for tasks such as detection or classification. If unset the filename without the extension will be used.
- **`file` [str]** (required): Filename of the mesh.
- **`allowed_colors` ["all", "none" or [\<str>]]** (*default*: "all"): Colors which can be applied to the shape.   
<ins>NOTE</ins>: This attribute can be specified both for shapes and materials, when a shape is created a color present in both is chosen, if both are not *"none"* and there are no common colors, an error is raised. For example if a shape allows for *"green"*, *"red"*, *"gray"* and *"yellow"*, and the chosen material allows for *"red"*, *"yellow"* and *"white"*, the shape will be either *"yellow"* or *"red"*.

- **`allowed_materials` ["all", "none" or [\<str>]]** (*default*: "all"): Materials which can be applied to the shape. If *"none"* no material will be applied.
- **<strong style="color:red">WIP</strong> <s>`margin` [float]</s>** (*default*: 0): Minimum distance from another shape, can either be a float or a list of 3 floats. Defines a box of the specified dimensions (a cube if a float is used) around the origin of the shape, it should specify the space occupied by the object, so when two shapes are placed their boxes will not intersect.  
<ins>NOTE</ins>: The box will be scaled the same way as the shape, the size of this box should match the size of the original, not scaled shape.

- **`min_distance` [float]** (*default*: 0): Minimum distance from another shape. This value will be scaled accordingly to the maximum of the scaling factors along each axis of the shape. The distance between two shapes will be at least the sum of their **`min_distance`** values.
- **`scaling` ["none" or dict]** (*default*: "none"): Specifies how the scaling should be done, see [Scaling](###+Scaling) below, if left *"none"* no scaling will be applied.
- **`random_rotation` ["none" or dict]** (*default*: "none"): Specifies how random rotations should be applied, see [Random rotations](###+Rotations) below.
- **`snap_to_plane` [bool]** (*default*: true): Bool value, if true the shape will lay on the base plane, if false it will be placed at a random height.
- **`fixed_rotation` [\<int>]** (*default*: [0, 0, 0]): List of three integers, specifies roll, pitch and yaw values (in degrees).
- **`flip` ["none" or dict]** (*default*: "none"): If "none" the shape will remain the same, if a dict is specified, it should have 3 attributes: **`xy`**, **`xz`**, **`yz`**, each one of them can either be:
    - **true**: to flip the shape along that plane.
    - **false**: to not flip it.
    - **random**: to have it randomly flip along that plane.

## Materials attributes
- **`id` [int]** (required and unique): An integer which uniquely identifies the material.
- **`name` [str]** (*default*: matches **`file`**, unique): A name for the material, can act as a category for tasks such as detection or classification. If unset the filename without the extension will be used.
- **`file` [str]** (required): Filename of the material.
- **`allowed_colors` ["all", "none" or [\<str>]]** (*default*: "all"): Colors which can be applied to shapes with this material.  
<ins>NOTE</ins>: This attribute can be specified both for shapes and materials, when a shape is created a color present in both is chosen, if both are not *"none"* and there are no common colors, an error is raised. For example if a shape allows for *"green"*, *"red"*, *"gray"* and *"yellow"*, and the chosen material allows for *"red"*, *"yellow"* and *"white"*, the shape will be either *"yellow"* or *"red"*.

- **`degradation` ["none" or dict]** (*default*: "none"): Specifies how degradation should be applied, see [Random degradation](###+Degradation) below.
- **<strong style="color:red">WIP</strong> <s>`emission` ["none" or dict]</s>** (*default*: "none"): Specifies if the shape emits light, if not *"none"* the dict should have 4 values, the intensity of the is chosen randomly and ranges from 0 to 1:
    - **`color` [str]** (*default*: "dynamic"): Can be either "dynamic" to make it dependent of the color (must be specified in its attributes, see [Color attributes](##+Color+attributes) below), or a string specifying the color in hex RGB value. 
    - **`min` [float]** (*default*: 0): Minimum value for the intensity.
    - **`max` [float]** (*default*: 1): Maximum value for the intensity.
    - **`step` [float]** (*default*: 0.5): Intensities are chosen from an array ranging from *min* to *max* with increases specified by this value. For example with min=0.1, max=0.4 and step=0.1 intensity can be one of 0.1, 0.2, 0.3 or 0.4.

## Color attributes
- **`id` [int]** (required and unique): An integer which uniquely identifies the color.
- **`name` [str]** (required and unique): A name for the color, can act as a category for tasks such as detection or classification.
- **`hex` [str]** (required): hex RGB value of the color.
- **<strong style="color:red">WIP</strong> <s>`emission` [str]</s>** (*default*: same as **`hex`**): hex RGB value of the dynamic emission for this color. If *"none"* an attempt to use dynamic emission on this color results in an error.
- **`opacity` [float]** (*default*: 1): opacity of the color ranging from 0 to 1.

## Random values
Various attributes allow for random values to increase diversity.

### Scaling

Scaling can be randomly done in several combinations. When specifying a value for the *scaling* attribute of a shape a dict containing all the informations is used:

#### Attributes:
- **`min` [float]** (*default* 0.2): Minimum value for scaling.
- **`max` [float]** (*default* 1): Maximum value for scaling.
- **`step` [float]** (*default*: 0.4): Scale is chosen from an array ranging from *min* to *max* with increases specified by this value. For example with min=0.2, max=1 and step=0.4 scale can be one of 0.2, 0.6 or 1
- **`consistent` [str]** (*default*: "all"): Can be *"all"*, *"none"* or a combination of 2 axis (*"xy"*, *"yz"*, *"xz"*). If *"none"* scaling factors will be chosen independently for each axis, if *"all"* scaling will be consistent along all the axis, otherwise the 2 specified axis will have the same scaling factor while the other one can have a different one.
- **`max_scaling_difference` ["none" or float]** (*default*: "none"): Maximum difference between scaling factors on each axis, this value is used to prevent shapes from becoming too distorted. If left *"none"* no constriction will be applied.


### Rotations

Rotations can be applied randomly to increase variability, for example a cylinder could be placed on its base or on its side. When specifying a value for the *random_rotation* attribute a dict containing all the constraints of the rotations is used:  
<ins>NOTE</ins>: All angles are expressed in degrees.

#### Attributes
- **`min_bounds` [[\<int>]]** (*default* [0, 0, 0]): Minimum values for rotations along each axis.
- **`max_bounds` [[\<int>]]** (*default* [360, 360, 360]): Maximum value for rotation along each axis.
- **`snap` [[\<int>]]** (*default*: [0,0,0]): It represents the snapping points along each axis, if 0 no rotation will be applied on that axis.
- **`auto_snap_face` [bool]** (*default*: false): If True the shape will be aligned in such way that one of its faces is parallel to the base plane.  
<ins>NOTE</ins>: setting this value to true will override other attributes and no other rotation will be applied.
<strong style="color:red">WIP: </strong> In future the faces that can be chosen for the snapping will be dependent on **`min_bounds`** and **`max_bounds`** and a complementary rotation on the z axis could be applied.

### <strong style="color:red">WIP</strong> <s>Degradation</s>

Degradation can be used to make shapes look more realistic, it needs a blender file (inside the materials folder) specifying a `degrade` operation which will be applied to the material. Intensity is varied by changing the `intensity` parameter which ranges from 0 to 1. Degradation options are specified by using a dict containing all the rules:

#### Attributes:
- **`file` [str]** (required): File of the file containing the transformation.
- **`min` [float]** (*default* 0): Minimum value for degradation.
- **`max` [float]** (*default* 1): Maximum value for degradation.
- **`step` [float]** (*default*: 0.5): The `intensity` parameter is chosen from an array ranging from *min* to *max* with increases specified by this value. For example with min=0.2, max=1 and step=0.4, it can be one of 0.2, 0.6 or 1.
