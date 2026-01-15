# AnyPyTools Change Log

## v1.20.4

* Fix crash with pytest plugin when saving output to h5 files.


## v1.20.3

* Fixed a bug where `ctrl-c` events were not propagated and were silenced. This
  fixes an issue where using AnyPyTools in tools liek pytest or snakemake made
  it difficult to interrupt the process. 


## v1.20.2

* Fixed a deprecation warning from the pytest plugin, and enable pytest 9 support. 


## v1.20.1

* Fixed an issue with AnyPyTools when running directly in the main thread 
  of the `snakemake` workflow tool (i.e., directly in the snakefile). This fix forces
  AnyPyTools to use the standard Python subprocess module when running in snakemake.


## v1.20.0

* Fixed a problem that prevented multiple AnyPyTools instances from running
  simultaneously in the same process. Previously, other running AnyBody instances
  were shut down when the first `AnyPyProcess.start_macro()` call finished.

## v1.19.2

* Fixed missing widget information is user-guide documentation.


## v1.19.1

* Fixed minor formatting issues in documentation.

## v1.19.0

**Changed:**
*  The `results.to_dataframe()` no longer returns the special `task_*` (meta data) in the output columns. 
   To get the extra task info use `results.to_dataframe(*, include_task_info=True)`
*  The documentation page updated.

**Added:**
* New `macro_commands.ExtendOutput()` helper macro that can add arbitrary values 
  to the results output. This allows adding values that don't need to exist as 
  variables in the AnyBody model. This is useful for adding extra metadata that will
  appear in the results output when creating the macros.

  ```python 
  macro = [
    mc.Load("MyModel.main.any"),
    mc.ExtendOutput("SubjectID", "S001"),
    mc.ExtendOutput("SubjectHeight", "1.8"),
  ]
  results = app.start_macro(macro)
  assert results[0]["SubjectID"] == "S001"
  assert results[0]["SubjectHeight"] == 1.8
  ```

## v1.18

**Added:**
* New `macro_commands.Export()` helper class that can save output with custom names. 
  Similar to the "Dump" command, but allows variables to be saved with arbitrary names.

  See the following example: 
  
  ```python 
  macro = [
    mc.Load("MyModel.main.any"),
    mc.RunOperation("MyModel.Study.Kinematics"),
    mc.Export("Main.Study.Output.EKin", "NewShortName"),
  ]
  results = app.start_macro(macro)
  ```
  The `Main.Study.Output.EKin` variable will be available in the results as `results[0]['NewShortName']` instead of 
  using the full variable name.

  This also allows the same variable to be exported multiple times during a
  single simulation with different names in the output. This was not possible
  with the "Dump" command, as only the last exported variable would be available in the 
  results. 

**Changed:**
* When exporting a whole folder hierarchy, the folders themselves will no longer
  appear in the results as `Main.MyFolder = "..."`. Instead, only actual values
  and strings will be included in the output.
* AnyPyTools now requires a minimum of Python 3.10.
* The helper macro class "OperationRun" has been renamed to "RunOperation". The old name still works for backwards compatibility. 



## v1.17.1

**Changed:**
* Temporary macro files `*.anymcr` are now always deleted after a run.


## v1.17.0

**Fixed:**
* Fixed issue with parsing 'nan' values from AnyBody in multi dimensional arrays.
* Fixed an issue preventing the pytest plugin from ignoring missing `RunDurationCPUThread` objects.


## v1.16.1

**Fixed:**
* Fixed issue with parsing 'nan' values from AnyBody in multi dimensional arrays.


## v1.16.0

**Fixed:** 
Resolved an issue where exporting 2D output to pandas dataframes
failed. Now, 2D outputs (3D when a function of time) are flattened into 1D arrays for compatibility. For
example, rotation matrices are split into 9 separate columns, similar to how 3D
vectors are split into 3 columns.


## v1.15.2

**Fixed:**
Updated the pytest plugin to handles the way AnyBody 8.2 reports missing RunTest operations. 


## v1.15.1

**Fixed:**
* Fixed an issue parsing output when AnyBody prints "-nan" in the output values. This is now 
just treated as NaN. 

## v1.15.0

**Added:**
* Improved formatting of output when running AnyPyTools in Jupyter notebooks. 
* Add type anotation to the output of the `start_macro` function.


## v1.14.0
**Added:**
* Replace tqdm with rich.progress for enhanced task progress visualization
* Write temp macro files together with the log files.

## v1.13.2

**Fixed:**
* Fixed and syntax issue when removing logfiles when simulation fails.  

## v1.13.1

**Fixed:**
* Permission problems removing log files no longer causes a error message, but is silently ignored. 
  Hence, it doesn't cause a simulation to appear as failed to external tools. 


## v1.13.0

**Added:**
* Added a "LoadData" macro command can generate the macro for loading h5 files. 
* Allow the "AnyBodyCon" executable on path to have any valid windows executable extension (exe, bat, cmd etc.). 
  This will allow users to use custom shim of the AnyBodyCon executables to point else where.

## v1.12.2

**Fixed:**
* Fixed type annotation which broke compability with older versions of Python.


## v1.12.1

**Fixed:**
* Fixed a crash when stopping simulations with ctrl-c. It should now shutdown more gracefully.
* Fixed a bug making it was hard to stop simulations which were not running in parrallel. Now
  simulations are always started on separate threads, which makes it possible to stop them with ctrl-c.

**Added:**
* Added a some python annotations to the code base, which should provide better type hints in IDEs.



## v1.12.0

**Added:**

* Added a way of controlling AnyBodyCon processes, which forces the process to
  automatically end wwhen the Python process ends. This prevents the need to
  manually close the AnyBodyCon processes if the parent process was force killed. 


## v1.11.5

**Fixed:**

* Speed up importing by avoiding importing scipy until it is needed. 


## v1.11.4

**Fixed:**

* Fix regression in windows registry lookup which caused AnyPyTools to crash.


## v1.11.3

**Added:**

* Correctly detect installations of AnyBody version 8 on the machines.

**Fixed:**

* Allow the pytest plugin to work even if the machine doesn't have AnyBody installed. 


## v1.11.2

**Fixed:**

* Fix fix a backwards compatibiility problem when using the AnyPyTools Pytest plugin with 
  old versions of AMMR (<2.3). 


## v1.11.1

**Fixed:**

* Fix crash with version handling when AnyBody could not be found.


## v1.11.0

**Changed:**

* If AnyBody is on the PATH variable, then AnyPyTools will no use that version, 
  before looking for AnyBody in the registration database.  


**Fixed:**

* Fixed an issue with the pytest plugin when running tests with `--load-only` option and the "RunDurationCPU" output. 


## v1.10.0

**Added:**

- When running with "AnyBody" > 7.5 the pytest plugin will now save the timing
  information for how quickly the model loaded and how quickly the test ran. The output
  is added to the xml output from pytest. 

**Fixed:**
- Fix regression when specifying "#defines" from the pytest plugin.

## v1.9.1

**Fixed:**
- Fixed an regression with newer Numpy version, when combining output data from multiple AnyBody runs where some are missing values. 

## v1.9.0

**Fixed:**
- Fixed issue which would cauase macros to execute twice when running the GUI version of AnyBody. 

**Added:**
- Added a `interactive_mode` argument to the {class}`AnyPyProcess <anypytools.abcutils.AnyPyProcess>` class. Setting this argument will automaticially lauch the GUI version
of AnyBody with the macro commands. Futher it will not automatically exit AnyBody once the macro commands has finished. This must be done manually by the user. 


## v1.8.2

**Fixed:**
- Fix a bug in the {meth}`results.to_dataframe() <anypytools.tools.AnyPyProcessOutput.to_dataframe>` function when also specifying interpolation. 
  Now interpolation actually works again. Thanks to [Enrico De Pieri](https://github.com/depierie) and [Marc Bandi](https://github.com/marcbandi) for spotting and fixing this. 

## v1.8.1

**Added:**
- pytest plugin: Added an option to avoid deselecting tests which doesn't 
  save hdf5 files when using the `--anytest-output` option. 

  ```
  pytest --anytest-output=some-folder --no-anytest-deselect
  ```

## v1.8

**Fixed:**
- Fixed deprecation warning from the pytest plugin

**Added:**
- When writting AnyScript test files it is now possible to access the 
  pytest test-file object in the header section of the AnyScript file. 
  The file object is available in the name space as the `self` variable. 

**Removed:**
- Removed the option of implicitly writting `defines` in the headers
  of any test files. 

## v1.7.8

**Fixed:**
- Fix a bug with pytest plugin when saving output data from files.


## v1.7.7

**Fixed:**
- Fix minor problem in repr for AnyPyProcessOutput.
- Fix a problem where the pytest plugin would crash if AnyBody could not be found


## v1.7.6

**Fixed:**
- Fix small issues in tutorials.
- Fix issues when reading NaNs produced by AnyBody


## v1.7.5

**Fixed:**
- Return code on linux is now correctly intercepted and reported.


## v1.7.4

**Fixed:**
- Fixed pytest deprecation warnings.

## v1.7.4

**Fixed:**
- Fixed pytest deprecation warnings.

## v1.7.3

**Fixed:**
- Fixed a bug on linux when anybody was using it own internal Python hooks. Redirecting the output on the linux would cause
  python initialization to fail. 

## v1.7.2

**Changed:**
- Update documentation to use markdown.
- Add error message when no files are found with
  `search_subdir` arguments (fixes [#69](https://github.com/AnyBody-Research-Group/AnyPyTools/issues/69)). 

## v1.7.1

**Fixed:**

- Fix deprecation warnings in pytest plugin.

## v1.7.0

**Added:**

- AnyPyTools can now be used on linux if the AnyBody Modeling System is installed using wine.

## v1.6.0

**Changed**:

- The `to_dataframe()` methods have been updated.
  They now return a dataframe without an index by default.

  They also now support interpolation of the data.

  ```python
  app =  AnyPyProcess()
  results = app.start_marco(macro_list)

  df = results.to_dataframe(
    interp_var="Main.MyStudy.Output.Abscissa.t",
    interp_val=linspace(0,1,50)
  )
  ```

**Added**:

- Documentation on how to use the `to_dataframe()` method has been added to the tutorials.

## v1.5.0

Add methods for exporing simuation output as a pandas dataframe.

```python
app =  AnyPyProcess()
results = app.start_marco(macro_list)

df = results.to_dataframe(index_var="Main.MyStudy.Output.Abscissa.t")
```

The data has too be consistent across all macros. That means that the
`index_var` must be present in all simulations. Also note that since
pandas dataframes are 2D any 3D data will be flattened. For example 3D vectors
which will be saved into three columns in the dataframe. E.g. `r[0]`, `r[1]`, `r[2]`.

## v1.4.7

Ensure that 'nan' values returned from AnyBody are treated as "float('nan')" when returned to Python.

## v1.4.6

Fixed a bug when using explicit logfile arguments to `start_macro` did not work with the
`search_subdirs` argument.

## v1.4.5

Fixed a small issue with using AnyPyTools with pytest 6.0.0rc1

## v1.4.4

Adressed a deprecation warning from pytest plugin due to API change in pytest 5.4

## v1.4.3

Fixed regression with Python 3.8 where model output could not be serialzed. This
happend because empty folders (represented by "...") would become the python elipsis object.

## v1.4.2

**Fixed:**

- A potential bug when using the pytest plugin and expected errors in AnyScript test files.
- Fixed a bug with the pytest plugin not working with pytest 5.4

## v1.4.1

**Fixed:**

- Fixed a bug where log files would be removed even if the processing failed.

## v1.4.0

**Changed:**

- Progressbars are now draw using [tqdm](https://github.com/tqdm/tqdm). This enables error
  messages while the progress bar is rendering, and solves a problem with detecting when the
  code is running in Jupyter notebook and not.
- Running the pytest plugin with the `--anytest-save` argument now deselects
  all tests which doesn't save data to HDF 5 files.
- New option for running the GUI version of AMS with AnyPyTools instead of the console.
- Task meta info (i.e. `task_logfile`, `task_macro` etc.) are now hidden by default in the
  when printing the object witht the default `__repr__()`
- The `return_task_info` argument to `AnyPyProcess` class is now deprecated and task information is
  always include in the output.

## v1.3.0

**Changed:**

- Changed the interface for the pytest plugin when saving hdf5 files from anybody tests.

## v1.2.2

**Fixed:**

- Fixed problem with Ctrl-C events not working. `scipy.stats` used
  some fortran routines which hijacked the key event and caused a crash instead.
- Fixed an issue with process time not being reported correctly.
- Fixed an issue with macros which were a mixture of normal strings and macro-command helper
  classes from `anypytools.macro_commands`.

## v1.2.1

**Fixed:**

- Add a work-around for a bug in AnyBody \< 7.2.2 which cause the AnyBody console
  to start in interactive mode when launched from AnyPyTools. This could cause the
  console application to hang if something fails in AnyBody.

## v1.2.0

**Added:**

- Pytest plugin: Option to set the `faltal_warnings` variable as a list
  to select the warnings which should trigger an error.

**Removed:**

- Pytest plugin: Deprecated the `warnings_to_include` variable. Instead use the `fatal_warnings`
  variable to select specific warnings.

## v1.1.5

**Fixed:**

- Fix a bug with pytest plugin which caused expected errors to still show up in the error list.

## v1.1.4

**Removed:**

- Removed an `--runslow` argument in pytest plugin api. This setting caused problem when the user defined it them self.

## v1.1.3

**Added:**

- Add an option to add pytest markers to in the AnyScript test files. This is done by setting `pytest_markers=["slow"]` in
  in the header. It is the same as decorating Python tests with `@pytest.mark.slow`.

## v1.1.2

**Added:**

- Add an option to the pytest plugin to set the `debug_mode` for the console application.

**Fixed:**

- Pytest plugin can now handle new error messages from the upcoming AnyBody Modeling System 7.2.
- Deprecation warnings from using abstract base classes in the Python collection module.

## v1.1.1

**Fixed:**

- Fix bug in pytest plugin when pytest-xdist is installed.

## v1.1

**Added:**

- Added an `logfile` argument to the `app.start_macro()` function. This allow for setting an
  explicit name for a log file. If `start_macro()` runs muliple instances the logfile will have
  the task number appended.
- Added `debug_mode` option to the `AnyPyProcess` class. This will the debug mode of the
  console application (e.g. the `/deb #` flag).

## v1.0.1

**Fixed:**

- Fixed a problem with pytest plugin when the pytest-xdist plugin is missing.

## v1.0.0

**Changed:**

- Source code now formatted with [black](https://black.readthedocs.io/en/stable/) formatter.

**Added:**

- Added a feature to the pytest plugin to save HDF5 files when running AnyScript tests. The purpose
  of this feature is to easily generated data for comparing the simulation of two different models
  or the same model with a different version of AMS.

**Removed:**

- Support for legacy Python (2) was dropped. This also removes the dependency on the `future` package.

**Fixed:**

- Fixed a regression when accessing the output of the `start_macro` command
  (`AnyPyProcessOutputList`) for aggregated results across multiple macros.

## v0.14.1

**Fixed:**

- Minor problem with building documentation with sphinx 1.8.

## v0.14

**Fixed:**

- Make sure anypytools works in IPython/Jupyter even when ipywidgets is not installed.
- Fix problem with dump'ing variables which are references in the AnyBody Output structure. Now
  the variables will have the same name in the output as given in the dump command.
- Fix problem with log-files beeing removed if AnyBody crashed or exited unexpectedly.

**Added:**

- Added a simple functionality to save hdf5 files from the pytest plugin.

## v0.13

**Fixed:**

- Fix regression in for {py:class}`SetValue_random <anypytools.macroutils.SetValue_random>` which caused a
  crash when generating macros.

## v0.12

**Fixed:**

- Missing newlines in error output from pytest plugin.
- Fix a problem where the `ignore_errors` argument to {class}`anypytools.abcutils.AnyPyProcess` could
  not filter warnings when they were considered as errors with the `fatal_warnings`
  arguments.

**Changed:**

- Better error message when `anybodycon.exe` can not be found.

## v0.11.1

**New:**

- Pytest plugin adds support for specifying `warnings_to_include`,
  `fatal_warnings` in the header of AnyScript test files.

**Changed:**

- The output from pytest plugin is restructured to be more readable.

## v0.11.0

**New:**

- Added option to the set the priority of the macro operations.
  The option is an argument to {class}`AnyPyProcess <anypytools.abcutils.AnyPyProcess>`.

  ```python
  from anypytools import IDLE_PRIORITY_CLASS

  app = AnyPyProcess(priority = IDLE_PRIORITY_CLASS)
  ```

  Default is `BELOW_NORMAL_PRIORITY_CLASS`, and possible values are

  - `IDLE_PRIORITY_CLASS`
  - `BELOW_NORMAL_PRIORITY_CLASS`
  - `NORMAL_PRIORITY_CLASS`
  - `ABOVE_NORMAL_PRIORITY_CLASS`.

- Added argument `fatal_warnings` to {class}`AnyPyProcess <anypytools.abcutils.AnyPyProcess>` which
  treat warnings as errors when running macros.

  ```python
  app = AnyPyProces(warnings_to_include=['OBJ.MCH.KIN9'], fatal_warnings=True)
  ```

  The argument will only triggers for specific warnings given
  by `warnings_to_include` argument.

**Changed:**

- Macro operation now run with slightly lower priority (BELOW_NORMAL_PRIORITY_CLASS) to prevent
  Windows to become unusable when running many processes.

**Fixed:**

- Fixed a bug preventing really large variables to be read by AnyPyTools. The AnyBody Modeling System
  could split really large data matrixes across several lines in the log files which meant they
  were not picked up. The function {func}`anypytools.tools.parse_anybodycon_output` has been
  rewritten to fix this.

**Removed:**

- The AnyScript Pygments plugin is no longer part of AnyPyTools. It now has its own library
  [pygments_anyscript](https://pypi.python.org/pypi/pygments-anyscript).

## v0.10.10

**fixed:**

- Fix crash when `--define` option was not provided.

## v0.10.9

**New:**

- Add option to the pytest plugin, to set the define statements with an argument to pytest.

## v0.10.8

**Fixed:**

- Wrong error report when AnyBody exists abnormally during batch processing.

## v0.10.7

**Changed:**

- Always append 'exit' command to all macros. Seems to solve problem with AMS not shutting down correctly.
- Only enable pytest plugin on Windows platform

## v0.10.6

**Fixed:**

- Bug where no AMS license was not detected as a failed macro.

## v0.10.5

**Fixed:**

- Crash when the starting pytest plug-in when no AnyBody licenses are available

**New:**

- Pytest plugin support for the `ANYBODY_PATH_AMMR` path statement which will be
  used in the AMS 7.1

## v0.10.4

**Changed:**

- The pytest plugin can now get the BM configurations directly from the
  AMMR if they are availble. The will be for AMMR 2. This will eliminate
  the problem of keeping AnyPyTools in sync with the AMMR.

## v0.10.3

**New:**

- Update pytest plugin to support AMMR 2.0 Parameters. AMMR 1 parameters
  are still supported using `--ammr-version` argument to pytest.

## v0.10.2

**New:**

- Support new BodyModel statements, which starts and end with a underscore.

**Changed:**

> - Improved exception handling when trying to access data which
>   is not avaible in the output.

- Detect if AnyBodyCon exited from a license problem and report
  that in the log files.
- Refactor `_execute_anybodycon()` into a public function.

**Removed:**

> - Remove the deprecated `disp` argument to the `AnyPyProcess` class.

## v0.10.1

**Changed:**

- Updates and fixes to the documentation website.
- Added flake8 testing on Travis CI
- Fix crash using pytest on systems where git is not installed.

## v0.10.0

**Merged pull requests:**

- Fix PEP8 issues and remaining pytest issues
  [#21](https://github.com/AnyBody-Research-Group/AnyPyTools/pull/21)
  ([melund](https://github.com/melund))
- Update Documentaion and tutorials
  [#20](https://github.com/AnyBody-Research-Group/AnyPyTools/pull/20)
  ([melund](https://github.com/melund))
- Add SaveData MacroCommand for saving hdf5 files
  [#19](https://github.com/AnyBody-Research-Group/AnyPyTools/pull/19)
  ([melund](https://github.com/melund))
- Fix Crash on Python 2.7 when using h5py_wrapper
  [#18](https://github.com/AnyBody-Research-Group/AnyPyTools/pull/18)
  ([melund](https://github.com/melund))
- Setup Travis-CI for building documentation for publishing on github.io
  [#13](https://github.com/AnyBody-Research-Group/AnyPyTools/pull/13)
  ([melund](https://github.com/melund))
- Refactor the library for the new library documention.
  [#12](https://github.com/AnyBody-Research-Group/AnyPyTools/pull/12)
  ([melund](https://github.com/melund))
- Added `AnyPyProcessOutputList.tolist()` converting results to native Python
  [#11](https://github.com/AnyBody-Research-Group/AnyPyTools/pull/11)
  ([KasperPRasmussen](https://github.com/KasperPRasmussen))

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.7...master>)

## v0.9.7

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.6...0.9.7>)

## v0.9.6

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.5...0.9.6>)

## v0.9.5

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.4...0.9.5>)

## v0.9.4

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.3...0.9.4>)

## v0.9.3

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.2...0.9.3>)

## v0.9.2

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.1...0.9.2>)

## v0.9.1

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.9.0...0.9.1>)

## v0.9.0

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.3...0.9.0>)

## v0.8.3

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.2...0.8.3>)

## v0.8.2

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.1...0.8.2>)

## v0.8.1

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.8.0...0.8.1>)

## v0.8.0

\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.7.9...0.8.0>)

## \<v0.8

The before times... See GitHub for a full
\[Full Changelog\](<https://github.com/AnyBody-Research-Group/AnyPyTools/compare/0.1...0.8.0>)
