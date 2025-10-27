# Install and setup

[AnyPyTools](https://github.com/AnyBody-Research-Group/AnyPyTools) is an open source python library for working with the AnyBody Modeling System.

## Requirements:

The tool requies that you already a license for the [AnyBody Modeling System](http://www.anybodytech.com).

Depending on how you install the software, you may also need to 
have Python and the AnyBody Modeling System installed on the machine. However, if you use [pixi package manager](#recommended_install), it can handle these things for you. 

## Installation: 

AnyPyTools is Python libarary and can be installed directly from pypi `pip install anypytools`,
or as a conda package from the `conda-forge` channel. 


(recommended_install)=
### Recommended install


The best way to get started is using the pixi package manager. It will automatically install python and all needed depencies for you. 

Install the [pixi](https://pixi.sh/) package manager for Python.

> ```bash
> powershell -ExecutionPolicy ByPass -c "irm -useb https://pixi.sh/install.ps1 | ie
> ```

After installation, open your working directory in the terminal and run the following command:

> ```bash
> pixi init
> pixi add anypytools
> ```
 
This will create a virtual python environment in that folder and install the AnyPyTools package. Likwise, you can add other depedencies to the virtual environment (e.g. `pixi add jupyter pandas`). All dependencies are tracked in the `pixi.yaml` file which can also be edited manually. 

You can now activate the virtual environment with `pixi shell` and run your scripts. Otherwise, you can prefix your commands with `pixi run` to run them in the virtual environment. 

e.g.: 
```bash 
pixi run python my_script.py
```

### Controling the version of AnyBody used by AnyPyTools

The clever part of using a package manger like pixi is that you can also control which version of the AnyBody is used by AnyPyTools.

A light weight headless version of AnyBody exists as a [conda-packages](https://anaconda.org/anybody/anybodycon). Hence, we can install a specific version of AnyBody into our virtual environment. 

To do this we first need to add the `anybody` channel to our workspace. 

```bash
pixi workspace channel add anybody` 
```

Then we can install a specific version of AnyBody console application. 

```bash
pixi add anybodycon=8.1.4
```

Now all simulations in this workspace will use the specified version of AnyBody, regardsless of what is installed.