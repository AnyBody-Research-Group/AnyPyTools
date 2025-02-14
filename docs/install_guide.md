# Install guide

## Installation

### The easy way

The esiest way to get started is using the pixi package manager. It will
automatically install python and all needed depencies for you. 


Install the [pixi](https://pixi.sh/) package manager for Python.

```bash
powershell -ExecutionPolicy ByPass -c "irm -useb https://pixi.sh/install.ps1 | ie
```

After installation, open your working directory for you project in the terminal
and run the following command:

```bash
pixi init
pixi add anypytools
pixi install
```

This will create a virtual python environment in that folder and install the
AnyPyTools package. Likwise, you can add other depedencies to the virtual
environment (e.g. `pixi add jupyter pandas`). All dependencies are tracked in
the `pixi.yaml` file which can also be edited manually. 

You can now activate the virtual environment with `pixi shell` and run your
scripts. Otherwise, you can prefix your commands with `pixi run` to run them in
the virtual environment, e.g. `pixi run python myscript.py`.


### Controling the version of AnyBody used by AnyPyTools

The clever part of using a package manger like pixi is that you can also control
which version of the AnyBody is used by AnyPyTools.

A light gui-less version of AnyBody exists as
[conda-packages](https://anaconda.org/anybody/anybodycon). Hence, we can install
a specific version of AnyBody into our virtual environment. 

To do this we first need to add the `anybody` channel to our project. 

```bash
pixi project channel add anybody` 
```

Then we can install a specific version of AnyBody console application. 

```bash
pixi add anybodycon=8.0.4
```

Now all simulations executed with AnyPyTools in this project will use the
specified version of AnyBody, regardsless of what is installed on the host
system.

:::{note}
You still need valid AnyBody license to run the simulations with the AnyBody Conda packages. 
::: 