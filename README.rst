----------
AnyPyTools
----------

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

.. image:: https://travis-ci.org/AnyBody-Research-Group/AnyPyTools.svg?branch=master
    :target: https://travis-ci.org/AnyBody-Research-Group/AnyPyTools

.. image:: https://anaconda.org/conda-forge/anypytools/badges/installer/conda.svg
   :target: https://conda.anaconda.org/conda-forge

.. image:: https://anaconda.org/conda-forge/anypytools/badges/downloads.svg 
   :target: https://anaconda.org/conda-forge/anypytools


AnyPyTools is a toolkit for working with the `AnyBody Modeling System (AMS)`_
from Python. Its main purpose is to launch AnyBody simulations and collect results. It has a scheduler 
to launch multiple instances of AMS utilizing computers with multiple cores. AnyPyTools makes it 
possible to run parameter and Monte Carlo studies more efficiently than from within AMS.

.. _AnyBody Modeling System (AMS): http://www.anybodytech.com


Installation
============

- Download and install the `Anaconda Python distribution`_

- After installation opens the Anaconda command prompt and type:

.. code-block:: bash

    conda config --add channels conda-forge
    conda install anypytools

The library is also available on `PyPi <https://pypi.python.org/pypi/AnyPyTools>`_ for installing using ``pip``.


.. _Anaconda Python distribution: https://store.continuum.io/cshop/anaconda/

.. highlight:: python

Usage
============

The simplest case::

    from anypytools import AnyPyProcess
    app = AnyPyProcess()
    macro = [
        'load "Model.main.any"',
        'operation Main.Study.InverseDynamics',
        'run',
    ]
    app.start_macro(macro)


Please see the `Jupyter Notebook based tutorial`_, or check the the following for more information:

* `AnyPyTools's Documentation <https://anybody-research-group.github.io/anypytools-docs>`_

.. _Jupyter Notebook based tutorial: http://nbviewer.jupyter.org/github/AnyBody-Research-Group/AnyPyTools/blob/master/docs/Tutorial/00_AnyPyTools_tutorial.ipynb

.. image:: docs/_static/relax.png
   :alt: Don't panic
   :height: 100 px
   :align: left
