=====================
AnyPyTools Change Log
=====================


v1.1.1
=============

**Fixed:**

- Fix bug in pytest plugin when pytest-xdist is installed.



v1.1
=============

**Added:**

- Added an ``logfile`` argument to the ``app.start_macro()`` function. This allow for setting an
  explicit name for a log file. If ``start_macro()`` runs muliple instances the logfile will have
  the task number appended.
- Added ``debug_mode`` option to the ``AnyPyProcess`` class. This will the debug mode of the
  console application (e.g. the ``/deb #`` flag).


v1.0.1
=============

**Fixed:**

- Fixed a problem with pytest plugin when the pytest-xdist plugin is missing. 



v1.0.0
=============

**Changed:**

- Source code now formatted with `black <https://black.readthedocs.io/en/stable/>`__ formatter.

**Added:**

- Added a feature to the pytest plugin to save HDF5 files when running AnyScript tests. The purpose
  of this feature is to easily generated data for comparing the simulation of two different models
  or the same model with a different version of AMS.

**Removed:**

- Support for legacy Python (2) was dropped. This also removes the dependency on the ``future`` package. 

**Fixed:**

- Fixed a regression when accessing the output of the ``start_macro`` command
  (``AnyPyProcessOutputList``) for aggregated results across multiple macros. 


v0.14.1
=============

**Fixed:**

* Minor problem with building documentation with sphinx 1.8.  


v0.14
=============

**Fixed:**

- Make sure anypytools works in IPython/Jupyter even when ipywidgets is not installed.  

- Fix problem with dump'ing variables which are references in the AnyBody Output structure. Now 
  the variables will have the same name in the output as given in the dump command.
- Fix problem with log-files beeing removed if AnyBody crashed or exited unexpectedly.  

**Added:**

- Added a simple functionality to save hdf5 files from the pytest plugin.

v0.13
=============

**Fixed:**

- Fix regression in for :class:`AnyPyTools.macro_comands.SetValue_random` which caused a 
  crash when generating macros. 

v0.12
=============

**Fixed:**

- Missing newlines in error output from pytest plugin. 
- Fix a problem where the ``ignore_errors`` argument to :class:`AnyPyProcess()` could
  not filter warnings when they were considered as errors with the ``fatal_warnings`` 
  arguments. 

**Changed:**

- Better error message when ``anybodycon.exe`` can not be found.


v0.11.1
=============

**New:**

- Pytest plugin adds support for specifying ``warnings_to_include``, 
  ``fatal_warnings`` in the header of AnyScript test files. 

**Changed:**

- The output from pytest plugin is restructured to be more readable. 


v0.11.0
=============

**New:**

- Added option to the set the priority of the macro operations. 
  The option is an argument to :class:`AnyPyProcess()`. 

  .. code-block:: python
  
    from anypytools import IDLE_PRIORITY_CLASS

    app = AnyPyProcess(priority = IDLE_PRIORITY_CLASS) 

  Default is ``BELOW_NORMAL_PRIORITY_CLASS``, and possible values are 
  
  * ``IDLE_PRIORITY_CLASS``
  * ``BELOW_NORMAL_PRIORITY_CLASS``
  * ``NORMAL_PRIORITY_CLASS``
  * ``ABOVE_NORMAL_PRIORITY_CLASS``.
  
- Added argument ``fatal_warnings`` to :class:`AnyPyProcess()` which 
  treat warnings as errors when running macros.

  .. code-block:: python
    
    app = AnyPyProces(warnings_to_include=['OBJ.MCH.KIN9'], fatal_warnings=True)

  The argument will only triggers for specific warnings given 
  by ``warnings_to_include`` argument. 

**Changed:**

- Macro operation now run with slightly lower priority (BELOW_NORMAL_PRIORITY_CLASS) to prevent
  Windows to become unusable when running many processes. 

**Fixed:**

- Fixed a bug preventing really large variables to be read by AnyPyTools. The AnyBody Modeling System 
  could split really large data matrixes across several lines in the log files which meant they 
  were not picked up. The function :func:`anypytools.tools.parse_anybodycon_output` has been 
  rewritten to fix this. 

**Removed:**

- The AnyScript Pygments plugin is no longer part of AnyPyTools. It now has its own library 
  `pygments_anyscript <https://pypi.python.org/pypi/pygments-anyscript>`__. 


v0.10.10
=============

**fixed:** 

-  Fix crash when ``--define`` option was not provided.



v0.10.9
=============

**New:** 

-  Add option to the pytest plugin, to set the define statements with an argument to pytest.


v0.10.8
=============

**Fixed:** 

- Wrong error report when AnyBody exists abnormally during batch processing.



v0.10.7
=============

**Changed:** 

- Always append 'exit' command to all macros. Seems to solve problem with AMS not shutting down correctly.

- Only enable pytest plugin on Windows platform


v0.10.6
=============

**Fixed:** 

- Bug where no AMS license was not detected as a failed macro.


v0.10.5
=============

**Fixed:** 

- Crash when the starting pytest plug-in when no AnyBody licenses are available

**New:**

- Pytest plugin support for the ``ANYBODY_PATH_AMMR`` path statement which will be
  used in the AMS 7.1



v0.10.4
=============

**Changed:** 

- The pytest plugin can now get the BM configurations directly from the 
  AMMR if they are availble. The will be for AMMR 2. This will eliminate
  the problem of keeping AnyPyTools in sync with the AMMR.


v0.10.3
=============

**New:** 

- Update pytest plugin to support AMMR 2.0 Parameters. AMMR 1 parameters 
  are still supported using ``--ammr-version`` argument to pytest.


v0.10.2
=============

**New:**

- Support new BodyModel statements, which starts and end with a underscore. 


**Changed:**

 - Improved exception handling when trying to access data which 
   is not avaible in the output.

- Detect if AnyBodyCon exited from a license problem and report
  that in the log files.

- Refactor ``_execute_anybodycon()`` into a public function.

**Removed:**
 
 - Remove the deprecated ``disp`` argument to the ``AnyPyProcess`` class. 


v0.10.1
=============

**Changed:**

- Updates and fixes to the documentation website.
- Added flake8 testing on Travis CI
- Fix crash using pytest on systems where git is not installed.


v0.10.0
=============

**Merged pull requests:**

-  Fix PEP8 issues and remaining pytest issues
   `#21 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/21>`__
   (`melund <https://github.com/melund>`__)
-  Update Documentaion and tutorials
   `#20 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/20>`__
   (`melund <https://github.com/melund>`__)
-  Add SaveData MacroCommand for saving hdf5 files
   `#19 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/19>`__
   (`melund <https://github.com/melund>`__)
-  Fix Crash on Python 2.7 when using h5py_wrapper
   `#18 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/18>`__
   (`melund <https://github.com/melund>`__)
-  Setup Travis-CI for building documentation for publishing on github.io
   `#13 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/13>`__
   (`melund <https://github.com/melund>`__)
-  Refactor the library for the new library documention.
   `#12 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/12>`__
   (`melund <https://github.com/melund>`__)
-  Added ``AnyPyProcessOutputList.tolist()`` converting results to native Python 
   `#11 <https://github.com/AnyBody-Research-Group/AnyPyTools/pull/11>`__
   (`KasperPRasmussen <https://github.com/KasperPRasmussen>`__)


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.7...master)

v0.9.7
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.6...0.9.7)

v0.9.6
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.5...0.9.6)


v0.9.5
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.4...0.9.5)


v0.9.4
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.3...0.9.4)

v0.9.3
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.2...0.9.3)

v0.9.2
=============

[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.1...0.9.2)

v0.9.1
=============


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.0...0.9.1)

v0.9.0
=============



[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.3...0.9.0)


v0.8.3
=============


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.2...0.8.3)


v0.8.2
=============


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.1...0.8.2)

v0.8.1
=============



[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.0...0.8.1)

v0.8.0
=============


[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.7.9...0.8.0)

<v0.8
=============
The before times... See GitHub for a full 
[Full Changelog](https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.1...0.8.0)