----------
AnyPyTools
----------

.. image:: https://img.shields.io/badge/License-MIT-yellow.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

.. image:: https://badges.gitter.im/Join%20Chat.svg
   :alt: Join the chat at https://gitter.im/xonsh/xonsh
   :target: https://gitter.im/AnyBody-Research-Group/AnyPyTools?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

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
* `Gitter channel <https://gitter.im/AnyBody-Research-Group/AnyPyTools>`_

.. _Jupyter Notebook based tutorial: http://nbviewer.ipython.org/github/AnyBody-Research-Group/AnyPyTools/blob/master/Tutorial/00_AnyPyTools_tutorial.ipynb

.. image:: docs/_static/relax.png
   :alt: Don't panic
   :height: 100 px
   :align: left
