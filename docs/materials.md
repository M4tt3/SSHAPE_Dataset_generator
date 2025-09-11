# How to create materials

Materials are used to define how the objects will be rendered, they are stored as **blend files** and must be placed inside the `materials_dir` folder.
What is imported to the scene is not the material itself, rather its **node group** is used.

<img src="images/material_nodes.png"  align="center" />

In this example the `metal` group on the left will be copied and routed to the output for the newly created material in the scene. Its input parameters are then appropriately set.
The name of the group must match the **`name`** parameter in the material rules. 

## Input parameters

Each material can have a set of input parameters:

- **`Color`**: The color of the material.
- **`Degradation`**: The degradation level of the material.
- **`Degradation Color`**: The color of the degradation.

Its mandatory for the input parameters to have the same exact names as above.
For a material to support color the `Color` parameters is needed, for it to support degradation both the `Degradation` and `Degradation Color` parameters are needed.
