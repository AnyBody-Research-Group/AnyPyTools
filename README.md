# AnyPyTools

[![Gitter](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/AnyBody-Research-Group/AnyPyTools?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

AnyPyTools is a toolkit for working with the [AnyBody Modeling System (AMS)](www.anybodytech.com) from Python. Its main purpose is to launch AnyBody simulations and collect results. It has a scheduler to launch multiple instances of AMS utilsing  computers with multiple cores. This makes it possible to run parameter and monte carlo studies more effciently than from within AMS.


# Installation

- Download and install the [Anaconda python distribution](https://store.continuum.io/cshop/anaconda/)

- After installation open the Anaconda command prompt and type:

>``` cmd
> conda install -c melund anypytools
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

To really use the library see this [tutorial](http://nbviewer.ipython.org/github/AnyBody-Research-Group/AnyPyTools/blob/master/Tutorial/00_AnyPyTools_tutorial.ipynb)
