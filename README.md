# Contribution

This is an **ongoing project**, every contribution is welcome, feel free to send a **pull request** for any changes or to give me some **advice**.

If you like the project **sharing** it could be really helpful.


# Quickstart guide

<ol>
<h2><li> Install</h2>

### Prerequsites
To run this script you must have [Blender](https://www.blender.org/) installed on your system.  
The script will work on blender version >=3.0 and <=3.6, but version 3.6 is advised, in case of compatibility issues on theese versions please post an issue.

### Navigate to the packages directory of embedded python

Run the following script in a terminal.

    cd {BLENDER}/{BLENDER VERSION}/python/lib

Replace **{BLENDER}** in with your blender installation directory, and **{BLENDER VERSION}** with your blender version, which you can get by running `blender --version`.

### Clone the github repo
Dowload SSHAPE_Dataset_generator by running the following command.

    git clone https://github.com/M4tt3/SSHAPE_Dataset_generator.git

<h2><li> Install bpycv </h2>
[bpycv](https://github.com/DIYer22/bpycv) is a library used to generate instance annotations (segmentation, depth, ...), it is required to run this script.  

To install run an elevated terminal, navigate to the blender installation dir and run the following commands:

### Install pip (or update if installed)

    blender -b --python-expr "from subprocess import sys,call;call([sys.executable,'-m','ensurepip'])"

### Update pip toolchain

    blender -b --python-expr "from subprocess import sys,call;call([sys.executable]+'-m pip install -U pip setuptools wheel'.split())"

### Install bpycv with pip

    blender -b --python-expr "from subprocess import sys,call;call([sys.executable]+'-m pip install -U bpycv'.split())"


### Check installation
Once the installation is done you can check that bpycv was correctly installed by running:

    blender -b -E CYCLES --python-expr "import bpycv,cv2;d=bpycv.render_data();bpycv.tree(d);cv2.imwrite('/tmp/try_bpycv_vis(inst-rgb-depth).jpg', d.vis()[...,::-1])"



<h2><li> (OPTIONAL) Install tqdm</h2>

[tqdm](https://tqdm.github.io/) is a python library used to show a progress bar during rendering.  
Not installing tqdm will have no effect on performance but it can be handy to get information about progress during rendering.

Run the following to install tqdm

    {BLENDER}/{BLENDER VERSION}/python/bin/python -m pip install tqdm

Replace **{BLENDER}** in with your blender installation directory, and **{BLENDER VERSION}** with your blender version, which you can get by running `blender --version`.

<h2><li> Setup rules </h2>

Rules files store all the objects and decoys to be used, the materials and colors to be applied, and the transformations contstraints.  
To define the rules for your dataset first start from this template:

```json
{
    "objects" : [],
    "decoys" : [],
    "materials" : [],
    "colors" : [],
    "macros" : []
}
```

### Shapes

To define all the objects and decoys you want to use add them to the objects list, see [Rules: Shape attributes](./docs/rules.md). When the scenes are created random objects and decoys chosen from this list will be added, the decoys list can be left empty if they are not needed.  
Here is an example:
```json
{
    "id" : 0,
    "name" : "pyramid",
    "file" : "pyramid.blend",
    "allowed_colors" : "all",
    "allowed_materials" : ["rubber", "metal"],
    "min_distance" : 0.87,
    "snap_to_plane" : true
}
```

### Materials

The materials section is used to define all the materials to be used during rendering and their properties, see [Rules: Materials attributes](./docs/rules.md). Whenever an object is added a random material within its `allowed_materials` is applied to it.
Here is an example:
```json
{
    "id" : 0,
    "name" : "matte",
    "file" : "matte.blend",
    "allowed_colors" : "all"
},
```

### Colors

The colors section is used to define all the colors to be used during rendering, see [Rules: Colors attributes](./docs/rules.md). Whenever an object is added a random color within both `allowed_colors` of that shape and its material is applied to it.
Here is an example:
```json
{
    "name" : "white",
    "id" : 1,
    "hex" : "#ffffff",
    "opacity" : 1
},
```

### Macros

When creating rules for complex datasets with lots of shapes and materials it can become very confusing and verbose, macros are a way to make the rules simpler by avoiding redundant repetitions, see [Rules: Macros](./docs/rules.md).  
For example writing:
```json
{
    "objects" : [
        {
            "allowed_colors" : "$warm_colors",
            ...
        }
        ...
    ],
    ...
    "macros" : {
        "warm_colors" : ["red", "orange", "yellow"]
    }
}
```
is the **same** as:
```json
{
    "objects" : [
        {
            "allowed_colors" : ["red", "orange", "yellow"],
            ...
        }
        ...
    ],
    ...
}
```

<h2><li> Setup the file tree </h2>

When using the dataset generator some parameters and files must be provided, as well as an output folder for the finished dataset. For this reason it's good practice to use a tidy file tree like the one suggested below: 

    .
    └── My_dataset/
        ├── data/
        │   ├── objects/
        │   ├── decoys/
        │   ├── materials/
        │   ├── <span style="color:orange">base_scene.blend</span>
        │   └── <span style="color:lime">rules.json</span>
        └── oputput/

The files you must provide as arguments are the following:

 - `rules`: This is the most important argument, the rules file stores all the informations about how the scenes must be created, check [Setup rules]().

 - `objects_dir`, `decoys_dir` and `materials_dir`: This arguments provide the folders in which objects, decoys and materials are stored, check [How to create shapes and materials]().

 - `output_dir`: This is the output dir for the dataset, the format of the dataset is a slightly modified [COCO format](https://docs.aws.amazon.com/rekognition/latest/customlabels-dg/md-coco-overview.html).

 - `base_scene`: The scene onto which the objects are placed, can be left *None* to be empty.

<h2><li> (Optional) Create config file </h2>

When rendering there are lots of arguments that can be used to tweak how the dataset will turn out, to change this values you can simply specify the arguments and their values when running the script, but you can also provide a config file (JSON) to override the default values of each argument.  
To get a list of all the arguments run:

    blender --background --python create_dataset.py -- --help

To create a config file run:

    blender --background --python build_config_file.py -- {OUTPUT FILE}

Replace **{OUTPUT FILE}** with the file where the configuration must be written.   
After the output file you can put all the arguments and the values you want to assign them or you can leave it empty and modify them directly in the output file.

<h2><li> Start rendering </h2>

To start the rendering process simply use this command and put all the arguments after `--`:

    blender --background --python create_dataset.py -- {ARGUMENTS}

If you want to use a config file you can simply use the argument `--config`:

    blender --background --python create_dataset.py -- --config {PATH TO CONFIG}

</ol>