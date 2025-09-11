# Rules files

They are used to specify rules on how object must be placed and rendered, for example you could set what materials can be used for certain shapes, they are stored as **json files**. Every dataset needs some basic rules to define colors, identifiers and materials but lots of different rules can be applied to make the dataset more diverse and robust.

You can find an example structure at "docs/rules_example.json".

## Structure
Rules files are divided in 5 sections:
- **`world` [dict]**: Specifies generic properties, see [World attributes](##+World+attributes) below.
- **`camera` [dict]**: Specifies properties for the camera, see [Camera attributes](##+Camera+attributes) below.
- **`lights` [dict]**: Specifies properties for the lights, see [Lights attributes](##+Lights+attributes) below.
- **`objects` [\<shape>]**: Specifies properties for objects, see [Shape attributes (objects and decoys)](##+Shape+attributes+(objects+and+decoys)) below.
- **`decoys` [\<shape>]**: Specifies properties for decoys, see [Shape attributes (objects and decoys)](##+Shape+attributes+(objects+and+decoys)) below.
- **`materials` [\<material>]**: Specifies properties for materials, see [Materials attributes](##+Materials+attributes) below.
- **`colors` [\<color>]**: Specifies properties for colors, see [Colors attributes](##+Colors+attributes) below.
- **`macros` [\<macro>]**: Specifies macros to easily save common configurations, see [Macros](##+Macros) below.

## World attributes

- **`offset` [\<float>]** (*default*: [0, 0, 0]): Offset applied to all shapes and decoys.
- **`cluster_area` [\<float>]** (*default*: [0, 0, 0]): Area in which clusters can be placed (cuboid of this size centered at `offset`).
- **`cluster_size` [float]** (*default*: 1.0): Area in which all the shapes of a cluster must fit.
- **`snap_cluster_to_ground` [bool]** (*default*: false): If *true* the cluster Z coordinate will be the ground level at its center.
- **`min_num_objects` [int]** (*default*: 2): Minimum number of objects in the scene.
- **`max_num_objects` [int]** (*default*: 5): Maximum number of objects in the scene.
- **`min_num_decoys` [int]** (*default*: 0): Minimum number of decoys in the scene.
- **`max_num_decoys` [int]** (*default*: 0): Maximum number of decoys in the scene.

## Camera attributes

- **`min_distance` [float]** (*default*: 3): Minimum distance of the camera from the origin.
- **`max_distance` [float]** (*default*: 3): Maximum distance of the camera from the origin.
- **`min_pitch` [float]** (*default*: 30): Minimum pitch of the camera.
- **`max_pitch` [float]** (*default*: 80): Maximum pitch of the camera.
- **`min_yaw` [float]** (*default*: 0): Minimum yaw of the camera.
- **`max_yaw` [float]** (*default*: 360): Maximum yaw of the camera.
- **`lens` [float]** (*default*: 20): Lens of the camera.

## Lights attributes

- **`min_distance` [float]** (*default*: 3): Minimum distance of the lights from the origin.
- **`max_distance` [float]** (*default*: 3): Maximum distance of the lights from the origin.
- **`min_pitch` [float]** (*default*: 70): Minimum pitch of the lights.
- **`max_pitch` [float]** (*default*: 90): Maximum pitch of the lights.
- **`min_yaw` [float]** (*default*: 0): Minimum yaw of the lights.
- **`max_yaw` [float]** (*default*: 360): Maximum yaw of the lights.
- **`min_num` [int]** (*default*: 1): Minimum number of lights in the scene.
- **`max_num` [int]** (*default*: 3): Maximum number of lights in the scene.
- **`min_intensity` [int]** (*default*: 100): Minimum intensity of the lights.
- **`max_intensity` [int]** (*default*: 500): Maximum intensity of the lights.
- **`radius` [float]** (*default*: 0.5): Radius of the light.

## Shape attributes (objects and decoys):
- **`id` [int]** (required and unique): An integer which uniquely identifies the shape.
- **`name` [str]** (*default*: matches **`file`**, unique): This value must match the name of the object to be loaded from the scene of the shape file.  
<u>NOTE</u>: If unset, the **`file`** value without the extension will be used.

- **`file` [str]** (required): Filename of the shape (not the path, the file will be searched inside of either `objects_dir` or `decoys_dir`).
- **`allowed_colors` ["all", "none" or [\<str>]]** (*default*: "all"): Colors which can be applied to the shape.   
<ins>NOTE</ins>: This attribute can be specified both for shapes and materials, when a shape is created a color present in both is chosen, if both are not *"none"* and there are no common colors, an error is raised. For example if a shape allows for *"green"*, *"red"*, *"gray"* and *"yellow"*, and the chosen material allows for *"red"*, *"yellow"* and *"white"*, the shape will be either *"yellow"* or *"red"*.

- **`allowed_materials` ["all", "none" or [\<str>]]** (*default*: "all"): Materials which can be applied to the shape. If *"none"* no material will be applied.
- **`min_distance` [float]** (*default*: 0): Minimum distance from another shape. This value will be scaled accordingly to the maximum of the scaling factors along each axis of the shape. The distance between two shapes will be at least the sum of their **`min_distance`** values.
- **`scaling` ["none" or dict]** (*default*: "none"): Specifies how the scaling should be done, see [Scaling](###+Scaling) below, if left *"none"* no scaling will be applied.
- **`random_rotation` ["none" or dict]** (*default*: "none"): Specifies how random rotations should be applied, see [Random rotations](###+Rotations) below.
- **`snap_to_plane` [bool]** (*default*: true): Bool value, if true the shape will lay on the base plane, if faalse it will be placed at a random height.
- **`fixed_rotation` [\<int>]** (*default*: [0, 0, 0]): List of three integers, specifies roll, pitch and yaw values (in degrees).
- **`flip` ["none" or dict]** (*default*: "none"): If "none" the shape will remain the same, if a dict is specified, it should have 3 attributes: **`xy`**, **`xz`**, **`yz`**, each one of them can either be:
    - **true**: to flip the shape along that plane.
    - **false**: to not flip it.
    - **"random"**: to have it randomly flip along that plane.

## Materials attributes
- **`id` [int]** (required and unique): An integer which uniquely identifies the material.
- **`name` [str]** (*default*: matches **`file`**, unique): A name for the material, can act as a category for tasks such as detection or classification. If unset the filename without the extension will be used.
- **`file` [str]** (required): Filename of the material.
- **`allowed_colors` ["all", "none" or [\<str>]]** (*default*: "all"): Colors which can be applied to shapes with this material.  
<ins>NOTE</ins>: This attribute can be specified both for shapes and materials, when a shape is created a color present in both is chosen, if both are not *"none"* and there are no common colors, an error is raised. For example if a shape allows for *"green"*, *"red"*, *"gray"* and *"yellow"*, and the chosen material allows for *"red"*, *"yellow"* and *"white"*, the shape will be either *"yellow"* or *"red"*.

- **`degradation` ["none" or dict]** (*default*: "none"): Specifies how degradation should be applied, see [Random degradation](###+Degradation) below.

## Color attributes
- **`id` [int]** (required and unique): An integer which uniquely identifies the color.
- **`name` [str]** (required and unique): A name for the color, can act as a category for tasks such as detection or classification.
- **`hex` [str]** (required): hex RGB value of the color.
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
<ins>NOTE</ins>: if set to *true* the random rotation will be applied **after** the snapping.
- **`faces_for_snapping` [[\<int>] or "all"]** (*default*: "all"): List of faces ids to which the auto snapping can occur.

### Degradation

Degradation makes objects look less sharp, it can be applied to materials which support it.

#### Attributes:
- **`color` [str]** (*default* "auto"): Hex value for the `Degradation Color` parameter or "*auto*", which sets the same color as the one used for the shape.
- **`min` [float]** (*default* 0): Minimum value for degradation.
- **`max` [float]** (*default* 1): Maximum value for degradation.
- **`step` [float]** (*default*: 0.5): The `Degradation` parameter is chosen from an array ranging from *min* to *max* with increases specified by this value. For example with min=0.2, max=1 and step=0.4, it can be one of 0.2, 0.6 or 1.
