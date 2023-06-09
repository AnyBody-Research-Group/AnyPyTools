# Install guide

## Installation

### The easy way

The easiest way to install AnyPyTools on Windows (along with all dependencies) is through the Anaconda Python
Distribution and the conda package manager.

Install AnyPyTools with the following command:

```bat
> conda config --add channels conda-forge
> conda install anypytools
```

This will install `anypytools` and all the recommended dependencies. Next, try to launch the
interactive AnyPyTools notebook tutorial :

```bat
> AnyPyToolsTutorial.bat
```

### Other installations options

It is also possible to install directly from the python package index. 

```bat
> pip install AnyPyTools 
```

or clone/download the source files from [GitHub](https://github.com/AnyBody-Research-Group/AnyPyTools):  

To install run the following command in the source folder: 

```bat
> pip install -e .
```
