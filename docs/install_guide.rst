==========================
Install guide
==========================

Installation
================

The easy way
----------------

The easiest way to install AnyPyTools on windows is through the Anaconda Python
Distribution and the conda package manager.

Install AnyPyTools with the following command:

.. code-block:: bat

   > conda config --add channels conda-forge
   > conda install anypytools

This will install xonsh and all the recommended dependencies. Next, try to launch the
interactive AnyPyTools notebook tutorial :

.. code-block:: bat

   > AnyPyToolsTutorial.bat


Install from source
-------------------

To install xonsh from source on Windows, first install `Python`_. Remember to select "Add python to PATH" during installation.


Download the latest `anypytools-master.zip`_ from github and unzip it
to ``anypytools-master``.

Now install anypytools:

.. code-block:: bat

   > cd anypytools-master
   > pip install -e

.. _Python: https://www.python.org/downloads/windows/
.. _anypytools-master.zip: https://github.com/anybody-research-group/anypytools/archive/master.zip



