=================
Developer's Guide
=================
.. image:: _static/relax.png
   :width: 80 %
   :alt: Don't panic
   :align: center

This is place for developer information that does not belong in the user 
guides or the API reference, but is useful for people developing or contributing
to AnyPyTools.

.. note:: All code changes must go through the pull request review procedure.



Style Guide
===========
AnyPyTools use PEP8 (with some relaxations to the line length) to
ensure consistency throughout the code base.

How to Test
================


----------------------------------
Dependencies
----------------------------------

Prep your environment for running the tests::

    $ pip install -r requirements-tests.txt


----------------------------------
Running the Tests
----------------------------------

Run all the tests using pytest::

    $ pytest --flake8


If you want to run specific tests you can specify the test names to
execute. For example to run test_aliases::

    $ pytest abcutils.py

Note that you can pass multiple test names in the above examples::

    $ pytest abcutils.py datautils.py



Happy Testing!


How to Document
====================
Documentation takes many forms. This will guide you through the steps of
successful documentation.

----------
Docstrings
----------
No matter what language you are writing in, you should always have
documentation strings along with you code. This is so important that it is
part of the style guide.  When writing in Python, your docstrings should be
in reStructured Text using the `numpydoc`_ format.

------------------------
Auto-Documentation Hooks
------------------------
The docstrings that you have written will automatically be connected to the
website, once the appropriate hooks have been setup.  At this stage, all
documentation lives within AnyPyTools's top-level ``docs`` directory.
We uses the sphinx tool to manage and generate the documentation, which
you can learn about from `the sphinx website <http://sphinx-doc.org/>`_.
If you want to generate the documentation, first AnyPyTools itself must be installed
and then you may run the following command from the ``docs`` dir:

.. code-block:: console

    ~/AnyPyTools/docs $ make html

All user-facing API should be added to the sphinx documentation. This should be done the
first time that the module, class or function appears in a pull request.  From here, call the
new module ``mymod``.  The following explains how to add hooks.

------------------------
Python Hooks
------------------------
Python documentation lives in the ``docs/api`` directory.
First, create a file in this directory that represents the new module called
``mymod.rst``.
The ``docs/api`` directory matches the structure of the ``AnyPyTools/`` directory.
So if your module is in a sub-package, you'll need to go into the sub-package's
directory before creating ``mymod.rst``.
The contents of this file should be as follows:

**mymod.rst:**

.. code-block:: rst

    .. _AnyPyTools_mymod:

    =======================================
    My Awesome Module -- :mod:`AnyPyTools.mymod`
    =======================================

    .. currentmodule:: AnyPyTools.mymod

    .. automodule:: AnyPyTools.mymod
        :members:

This will discover all of the docstrings in ``mymod`` and create the
appropriate webpage. Now, you need to hook this page up to the rest of the
website.

Go into the ``index.rst`` file in ``AnyPyTools/docs/api`` and add
``mymod`` to the appropriate ``toctree`` (which stands for table-of-contents
tree).


Building the Website
===========================

Building the website/documentation requires the following dependencies:

#. `Sphinx <http://sphinx-doc.org/>`_
#. `Cloud Sphinx Theme <https://pythonhosted.org/cloud_sptheme/cloud_theme.html>`_
#. `recommonmark <https://recommonmark.readthedocs.io/en/latest/>`_
#. `pandoc <https://pandoc.org/>`_
#. `ipykernel <http://ipython.readthedocs.io/en/stable/install/kernel_install.html>`_ 
#. `nbsphinx <https://nbsphinx.readthedocs.io>`_ 

-----------------------------------
Procedure for modifying the website
-----------------------------------
The AnyPyTools website source files are located in the ``docs`` directory.
A developer first makes necessary changes, then rebuilds the website locally
by executing the command::

    $ make html

This will generate html files for the website in the ``_build/html/`` folder.
The developer may view the local changes by opening these files with their
favorite browser, e.g.::

    $ google-chrome _build/html/index.html

Once the developer is satisfied with the changes, the changes should be
committed and pull-requested per usual. Once the pull request is accepted, the 
documentation is build automatically by travis CI and pushed to the 
anybody-research-group/anypytools-docs repository from where it is published with
github pages.

Branches and Releases
=============================
Mainline AnyPyTools development occurs on the ``master`` branch. Other branches
may be used for feature development (topical branches) or to represent
past and upcoming releases.

If you have a new fix that needs to be in the next release, you
should make a topical branch and then pull request it into the release branch.
After this has been accepted, the topical branch should be merged with
master as well.

--------------------
Maintenance Tasks
--------------------
You can cleanup your local repository of transient files such as \*.pyc files
created by unit testing by running::

    $ rm -f AnyPyTools/*.pyc tests/*.pyc
    $ rm -fr build

-----------------------
Performing the Release
-----------------------

    1. Update and push the release log
    2. Update version number in ``anypytools.__init__.py``
    3. Ensure test pass
    4. Make PR on GitHub, and check docs compile correctly on travis
    5. Create a tag with the version number and push it.
    6. Crate PYPI pckage 
        a. Run ``python setup.py sdist``
        b. Run ``twine upload dist/*``
    7. Update the conda forge package on https://github.com/conda-forge/anypytools-feedstock


Document History
===================
Portions of this page have been forked from

  - Xonsh documentation, Copyright 2014-2017, the Xonsh Development Team. All rights reserved.
  - PyNE documentation,Copyright 2011-2015, the PyNE Development Team. All rights reserved.

.. _PEP8: https://www.python.org/dev/peps/pep-0008/
.. _numpydoc: https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt
