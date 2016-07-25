# AnyPyTools

[![Gitter](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/AnyBody-Research-Group/AnyPyTools?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

AnyPyTools is a toolkit for working with the [AnyBody Modeling System (AMS)](http://www.anybodytech.com) from Python. Its main purpose is to launch AnyBody simulations and collect results. It has a scheduler to launch multiple instances of AMS utilising computers with multiple cores. AnyPyTools makes it possible to run parameter and Monte Carlo studies more efficiently than from within AMS.


# Installation

- Download and install the [Anaconda Python distribution](https://store.continuum.io/cshop/anaconda/)

- After installation opens the Anaconda command prompt and type:

>``` cmd
> conda config --add channels conda-forge
> conda install anypytools
> ```


# Usage

The simplest case:
>``` py
> from anypytools import AnyPyProcess
> app = AnyPyProcess()
> macro = [['load "Model.main.any"',
>           'operation Main.Study.InverseDynamics',
>           'run' ]]
> app.start_macro(macro)
> ```

Please see this [tutorial](http://nbviewer.ipython.org/github/AnyBody-Research-Group/AnyPyTools/blob/master/Tutorial/00_AnyPyTools_tutorial.ipynb) on how to use the library. 

<img src="https://dl.dropboxusercontent.com/u/1683635/store/relax.png" alt="" align="left"  style="height: 100px;"/>
