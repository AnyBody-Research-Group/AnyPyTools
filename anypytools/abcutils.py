# -*- coding: utf-8 -*-
"""
Utilities for working with the AnyBody Console applicaiton.

Created on Fri Oct 19 21:14:59 2012
@author: Morten
"""

import os
import io
import sys
import time
import copy
import types
import ctypes
import shelve
import atexit
import pathlib
import logging
import warnings
import collections
from pathlib import Path
from subprocess import Popen, TimeoutExpired
from tempfile import NamedTemporaryFile
from threading import Thread, RLock
from queue import Queue

from typing import Generator, List

import numpy as np
from tqdm.auto import tqdm

from .tools import (
    ON_WINDOWS,
    make_hash,
    AnyPyProcessOutputList,
    parse_anybodycon_output,
    getsubdirs,
    get_anybodycon_path,
    BELOW_NORMAL_PRIORITY_CLASS,
    AnyPyProcessOutput,
    run_from_ipython,
    get_ncpu,
    winepath,
    silentremove,
    case_preserving_replace,
)
from .macroutils import AnyMacro, MacroCommand

logger = logging.getLogger("abt.anypytools")

_thread_lock = RLock()
_KILLED_BY_ANYPYTOOLS = 10
_TIMEDOUT_BY_ANYPYTOOLS = 11
_NO_LICENSES_AVAILABLE = -22
_UNABLE_TO_ACQUIRE_LICENSE = 234  # May indicate wrong password


class _SubProcessContainer(object):
    """Class to hold a record of process pids from Popen.

    Properties
    ----------
    stop_all: boolean
        If set to True all process held by the object will be automatically
        killed

    Methods
    -------
    add(pid):
        Add process id to the record of process

    remove(pid):
        Remove process id from the record

    """

    def __init__(self):
        self._pids = set()
        self._stop_all = False

    def add(self, pid):
        with _thread_lock:
            self._pids.add(pid)
        if self.stop_all:
            self._kill_running_processes()

    def remove(self, pid):
        with _thread_lock:
            try:
                self._pids.remove(pid)
            except KeyError:
                pass

    @property
    def stop_all(self):
        return self._stop_all

    @stop_all.setter
    def stop_all(self, value):
        if value:
            self._stop_all = True
            self._kill_running_processes()
        else:
            self._stop_all = False

    def _kill_running_processes(self):
        """Clean up and shut down any running processes."""
        # Kill any rouge processes that are still running.
        with _thread_lock:
            killed = []
            for pid in self._pids:
                try:
                    os.kill(pid, _KILLED_BY_ANYPYTOOLS)
                    killed.append(str(pid))
                except Exception:
                    pass
            self._pids.clear()


_subprocess_container = _SubProcessContainer()
atexit.register(_subprocess_container._kill_running_processes)


def execute_anybodycon(
    macro,
    logfile=None,
    anybodycon_path=None,
    timeout=3600,
    keep_macrofile=False,
    env=None,
    priority=BELOW_NORMAL_PRIORITY_CLASS,
    debug_mode=0,
    folder=None,
):
    """Launch a single AnyBodyConsole applicaiton.

    This is a low level function to start a AnyBody Console process
    with a given list macros.

    Parameters
    ----------
    macro : list of str
        List of macros strings to pass to the AnyBody Console Application
    logfile : file like object, optional
        An open file like object to write to pipe the output of AnyBody
        into. (Defaults to None, in which case it will use sys.stdout)
    anybodycon_path : str, optional
        Path to the AnyBodyConsole application. Default to None, in which
        case the default installed AnyBody installation will be looked up
        in the Windows registry.
    timeout : int, optional
        Timeout before the process is killed autmotically. Defaults to
        3600 seconds (1 hour).
    keep_macrofile : bool, optional
        Set to True to prevent the temporary macro file from beeing deleted.
        (Defaults to False)
    env: dict
        Environment varaibles which are passed to the started AnyBody console
        application.
    priority : int, optional
        The priority of the subprocesses. This can be on of the following:
        ``anypytools.IDLE_PRIORITY_CLASS``, ``anypytools.BELOW_NORMAL_PRIORITY_CLASS``,
        ``anypytools.NORMAL_PRIORITY_CLASS``, ``anypytools.HIGH_PRIORITY_CLASS``
        Default is BELOW_NORMAL_PRIORITY_CLASS.
    debug_mode : int
        The AMS debug mode to use. Defaults to 0 which is disabled. 1 correspond to
        crashdump enabled
    folder : the folder in which AnyBody is executed

    Returns
    -------
    int
        The return code from the AnyBody Console application.

    """
    if folder is None:
        folder = os.getcwd()

    try:
        macrofile_path = Path(folder).resolve() / (Path(logfile.name).stem + ".anymcr")
    except AttributeError:
        macrofile_path = Path("macrofile.anymcr")

    macrofile_cleanup = [macrofile_path]

    if logfile is None:
        logfile = sys.stdout

    if anybodycon_path is None:
        anybodycon_path = Path(get_anybodycon_path())

    if macro and macro[-1] != "exit":
        macro.append("exit")

    if not os.path.isfile(anybodycon_path):
        raise IOError(f"Can not find anybodycon.exe: {anybodycon_path}")

    with open(macrofile_path, "w+b") as fh:
        fh.write("\n".join(macro).encode("UTF-8"))
        fh.flush()

    if ON_WINDOWS:
        # Don't display the Windows GPF dialog if the invoked program dies.
        # See comp.os.ms-windows.programmer.win32
        # How to suppress crash notification dialog?, Jan 14,2004 -
        # Raymond Chen's response [1]
        SEM_NOGPFAULTERRORBOX = 0x0002  # From MSDN
        ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX)
        subprocess_flags = 0x8000000  # win32con.CREATE_NO_WINDOW?
        subprocess_flags |= priority
        extra_kwargs = {"creationflags": subprocess_flags}

        anybodycmd = [
            str(anybodycon_path.resolve()),
            "--macro=",
            str(macrofile_path),
            "/deb",
            str(debug_mode),
            "/ni",
        ]
        proc = Popen(
            anybodycmd,
            stdout=logfile,
            stderr=logfile,
            env=env,
            cwd=folder,
            **extra_kwargs,
        )

    else:
        # ON Linux/Wine we use a bat file to redirect the output into a file on wine/windows
        # side. This prevents a bug with AnyBody starts it's builtin python.
        anybodycmd = (
            f'@call "{winepath(anybodycon_path.resolve(), "--windows")}"'
            f' -m "{winepath(macrofile_path, "--windows")}"'
            f" -deb {str(debug_mode)}"
            " -ni"
            f' >> "{winepath(str(logfile.name), "--windows")}"\n'
            r"@exit /b %ERRORLEVEL%"
        )
        # Wine can have problems with arbitrary names. Create simple uniqe name for the file
        hash_id = abs(hash(logfile.name)) % (10 ** 8)
        batfile = macrofile_path.with_name(f"wine_{hash_id}.bat")
        batfile.write_text(anybodycmd)
        macrofile_cleanup.append(batfile)

        from shlex import quote

        cmd = ["wine", "cmd", "/c", str(batfile)]
        proc = Popen(cmd, env=env, cwd=folder)

    _subprocess_container.add(proc.pid)
    try:
        proc.wait(timeout=timeout)
        retcode = ctypes.c_int32(proc.returncode).value
    except TimeoutExpired:
        proc.kill()
        proc.communicate()
        retcode = _TIMEDOUT_BY_ANYPYTOOLS
    except KeyboardInterrupt:
        proc.terminate()
        proc.communicate()
        retcode = _KILLED_BY_ANYPYTOOLS
        raise
    finally:
        _subprocess_container.remove(proc.pid)

    if retcode == _TIMEDOUT_BY_ANYPYTOOLS:
        logfile.write(f"\nERROR: AnyPyTools : Timeout after {int(timeout)} sec.")
    elif retcode == _KILLED_BY_ANYPYTOOLS:
        logfile.write("\nAnybodycon.exe was interrupted by AnyPyTools")
    elif retcode == _NO_LICENSES_AVAILABLE:
        logfile.write(
            "\nERROR: anybodycon.exe existed unexpectedly. "
            "Return code: " + str(_NO_LICENSES_AVAILABLE) + " : No license available."
        )
    elif retcode == _UNABLE_TO_ACQUIRE_LICENSE:
        logfile.write(
            "\nERROR: anybodycon.exe existed unexpectedly. "
            f"Return code {_UNABLE_TO_ACQUIRE_LICENSE}: "
            "Unable to aquire license from server"
        )
    elif retcode:
        logfile.write(
            "\nERROR: AnyPyTools : anybodycon.exe exited unexpectedly."
            " Return code: " + str(retcode)
        )
    if not keep_macrofile:
        for fname in macrofile_cleanup:
            silentremove(str(fname))
    return retcode


class _Task(object):
    """Class for storing processing jobs.

    Attributes:
        folder: directory in which the macro is executed
        macro: list of macro commands to execute
        number: id number of the task
        name: name of the task, which is used for printing status informations
        logfile: If provided will specify an explicit logfile to use.

    """

    def __init__(self, folder=None, macro=None, taskname=None, number=1, logfile=None):
        """Init the Task class with the class attributes."""
        if folder:
            folder = Path(folder)
        else:
            folder = Path(os.getcwd())
        self.folder = str(folder.absolute())
        if macro is not None:
            self.macro = macro
        else:
            self.macro = []
        self.output = AnyPyProcessOutput()
        self.number = number
        self.logfile = logfile or ""
        self.processtime = 0
        self.retcode = None
        self.name = taskname
        if taskname:
            self.name = taskname
        else:
            self.name = f"{folder.parent.name}-{folder.name}-{number}".lstrip("-")

    def has_error(self):
        return "ERROR" in self.output

    def add_error(self, error_msg):
        try:
            self.output["ERROR"].append(error_msg)
        except KeyError:
            self.output["ERROR"] = [error_msg]

    def get_output(self, include_task_info=True):
        out = self.output
        if include_task_info:
            out["task_macro_hash"] = format(make_hash(self.macro), "x")
            out["task_id"] = self.number
            out["task_work_dir"] = self.folder
            out["task_name"] = self.name
            out["task_processtime"] = self.processtime
            out["task_macro"] = self.macro
            out["task_logfile"] = self.logfile
        return out

    @classmethod
    def from_output_data(cls, task_output):
        if not cls.is_valid(task_output):
            raise ValueError(
                'Output can only be reprocessed, if "Task info"'
                "is included in the output."
            )
        task = cls(
            folder=task_output["task_work_dir"],
            macro=task_output["task_macro"],
            taskname=task_output["task_name"],
            number=task_output["task_id"],
            logfile=task_output["task_logfile"],
        )
        task.processtime = task_output["task_processtime"]
        task.output = task_output
        return task

    @classmethod
    def from_output_list(cls, outputlist):
        for elem in outputlist:
            yield cls.from_output_data(elem)

    @classmethod
    def from_macrofolderlist(cls, macrolist, folderlist, explicit_logfile=None):
        if not macrolist:
            raise StopIteration
        macrofolderlist = [(m, f) for f in folderlist for m in macrolist]
        for i, (macro, folder) in enumerate(macrofolderlist):
            log = explicit_logfile
            if log and len(macrofolderlist) > 1:
                log = pathlib.Path(log)
                log = log.parent / (log.stem + "_" + str(i) + log.suffix)
            yield cls(folder, macro, number=i, logfile=log)

    @staticmethod
    def is_valid(output_elem):
        keys = (
            "task_macro_hash",
            "task_id",
            "task_work_dir",
            "task_name",
            "task_processtime",
            "task_macro",
            "task_logfile",
        )
        return all(k in output_elem for k in keys)


def tasklist_summery(tasklist: List[_Task]) -> str:
    out = ""
    unfinished_tasks = [t for t in tasklist if t.processtime <= 0]
    failed_tasks = [t for t in tasklist if t.has_error() and t.processtime > 0]
    completed_tasks = [t for t in tasklist if not t.has_error() and t.processtime > 0]
    out += f"Completed: {len(completed_tasks)}"
    if len(failed_tasks):
        out += f", Failed: {len(failed_tasks):d}"
    if len(unfinished_tasks):
        out += f", Not processed: {len(unfinished_tasks):d}"
    return out


def task_summery(task: _Task) -> str:
    if task.has_error():
        status = "Failed"
    elif task.processtime == 0:
        status = "Not completed"
    else:
        status = "Completed"
    line = f"{status} (i={task.number}) : {task.processtime:.1f} sec"
    if task.logfile:
        line += f" : {os.path.basename(task.logfile)}"
    return line


class AnyPyProcess(object):
    """
    Class for configuring batch process jobs of AnyBody models.

    This is the main interface to control the AnyBody console application from
    python. The class stores all the configuration about how AnyBody is run.
    It has one important method `start_macro` which launches the AnyBody with
    a given anyscript macro.

    Parameters
    ----------
    num_processes : int, optional
        Number of anybody models to start in parallel.
        This defaults to the number of logical CPU cores in the computer.
    anybodycon_path : str, optional
        Overwrite the default anybodycon.exe file to
        use in batch processing. Defaults to what is found in the windows
        registry.
    timeout : int, optional
        Maximum time (i seconds) a model can run until it is terminated.
        Defaults to 3600 sec (1 hour).
    silent : bool, optional
        Set to True to suppress any output such as progress bar and error
        messages. (Defaults to False).
    ignore_errors : list of str, optional
        List of AnyBody Errors substrings to ignore when running the models.
        (Defaults to None)
    warnings_to_include : list of str, optional
        List of strings that are matched to warnings in the model
        output. If a warning with that string is found the warning
        is returned in the output. (Defaults to None)
    fatal_warnings: bool, optional
        Treat warnings as errors. This only triggers for specific warnings given
        by ``warnings_to_include`` argument.
    keep_logfiles : bool, optional
        If True logfile will never be removed. Even if a simulations successeds
        without error. (Defautls to False)
    logfile_prefix : str, optional
        String which will be prefixed to the generated log files. This can be used
        to assign a more meaningfull name to a batch of logfiles.
        (Defaults to None)
    python_env : pathlike, optional
        Path to a python environment/installation that the AnyBody Modeling System
        should use for Python Hooks. This will added the ``PYTHONHOME`` environment variable and
        prepended to the ``PATH`` before starting the AnyBody Console application.
        (Defaults to None, which will use the default Python installation on the computer.)
    debug_mode : int, optional
        Sets the debug mode flag for the AnyBodyConsole appplication (e.g. the /deb <number> flag)
    use_gui : bool, optional
        Swictch to use the GUI instead of the console version of AMS. This works by replacing the 'anybodycon' part
        of the executable with 'anybody' of the `anybodycon_path` arguments. I.e. ".../anybdoycon.exe" becomes ".../anybody.exe"
    priority : int, optional
        The priority of the subprocesses. This can be on of the following:
        ``anypytools.IDLE_PRIORITY_CLASS``, ``anypytools.BELOW_NORMAL_PRIORITY_CLASS``,
        ``anypytools.NORMAL_PRIORITY_CLASS``, ``anypytools.HIGH_PRIORITY_CLASS``
        Default is BELOW_NORMAL_PRIORITY_CLASS.


    Returns
    -------
    AnyPyProcess
        An instance of the AnyPyProcess object for running batch processing,
        parameter studies and pertubation jobs.

    Example
    -------
    The following example shows how to instantiate a AnyPyProcess object.

    >>> app = AnyPyProcess(num_processes=8)

    The `app` object has methods for launching macros, saving results etc.

    >>> macro = ['load "MyModel.any"', 'operation Main.MyStudy.Kinematics', 'run']
    >>> app.start_macro(macro)

    """

    def __init__(
        self,
        num_processes=get_ncpu(),
        anybodycon_path=None,
        timeout=3600,
        silent=False,
        ignore_errors=None,
        warnings_to_include=None,
        fatal_warnings=False,
        return_task_info=None,
        keep_logfiles=False,
        logfile_prefix=None,
        python_env=None,
        debug_mode=0,
        use_gui=False,
        priority=BELOW_NORMAL_PRIORITY_CLASS,
        **kwargs,
    ):

        if return_task_info is not None:
            warnings.warn(
                "return_task_info is deprecated, and task meta information is always included in the output.",
                DeprecationWarning,
                stacklevel=2,
            )
        if len(kwargs):
            warnings.warn(
                "The following input arguments are not supported/understood:\n"
                + str(list(kwargs.keys()))
            )
        if not isinstance(ignore_errors, (list, type(None))):
            raise ValueError("ignore_errors must be a list of strings")

        if not isinstance(warnings_to_include, (list, type(None))):
            raise ValueError("warnings_to_include must be a list of strings")

        if anybodycon_path is None:
            anybodycon_path = get_anybodycon_path()
        anybodycon_path = Path(anybodycon_path)
        if use_gui:
            anybodycon_path = anybodycon_path.with_name(
                case_preserving_replace(anybodycon_path.name, "anybodycon", "anybody")
            )

        if anybodycon_path.exists():
            self.anybodycon_path = anybodycon_path
        else:
            raise IOError(f"Can't find  {anybodycon_path}")
        self.num_processes = num_processes
        self.priority = priority
        self.silent = silent
        self.timeout = timeout
        self.counter = 0
        self.debug_mode = debug_mode
        self.fatal_warnings = fatal_warnings
        self.ignore_errors = ignore_errors
        self.warnings_to_include = warnings_to_include
        self.keep_logfiles = keep_logfiles
        self.logfile_prefix = logfile_prefix
        self.cached_arg_hash = None
        self.cached_tasklist = None
        if python_env is not None:
            if not os.path.isdir(python_env):
                raise IOError("Python environment does not exist:" + python_env)
            env = dict(os.environ)
            env["PYTHONHOME"] = python_env
            env["PATH"] = env["PYTHONHOME"] + ";" + env["PATH"]
            self.env = env
        else:
            self.env = None
        logging.debug("\nAnyPyProcess initialized")

    def save_results(self, filename, append=False):
        """Save resently processed results.

        Save results for later reloading or to continue processing unfished
        results at a later time.

        Parameters
        ----------
        filename : str
            filename of the file where processing was stored.
        append : bool
            If true append data to what ever is already saved. This allows
            for saving data in batches.

        Returns
        -------
        None

        Examples
        --------
        >>> macro = ['load "model1.any"', 'operation Main.RunApplication', 'run']
        >>> app.start_macro(macro)
        >>> app.save_results('saved_data.db')

        """
        if self.cached_tasklist:
            savekey = "processed_tasks"
            db = shelve.open(filename, writeback=True)
            if not append or savekey not in db:
                db[savekey] = self.cached_tasklist
            else:
                db[savekey].extend(self.cached_tasklist)
            db.close()
        else:
            raise ValueError("Noting to save")

    def save_to_hdf5(self, filename, batch_name=None):
        """Save cached results to hdf5 file.

        Parameters
        ----------
        filename : str
            filename where data should be stored

        batch_name : str
            Name of the group in the HDF5 file to
            save the data within. If not specified
            the group hash value of the macro will
            be used.

        Returns
        -------
            None

        """
        import h5py

        if not self.cached_tasklist:
            raise ValueError("No data available for saving")

        if batch_name is None:
            batch_name = str(self.cached_arg_hash)

        any_output = AnyPyProcessOutputList(
            [task.get_output() for task in self.cached_tasklist]
        )
        task_names = [elem["task_name"] for elem in any_output]
        unique_names = len(task_names) == len(set(task_names))
        with h5py.File(filename, "w") as h5file:
            h5_batch_group = h5file.create_group(batch_name)
            for run in any_output:
                task_name = run["task_name"] if unique_names else str(run["task_id"])
                task_name = task_name.replace("/", "|")
                h5_task_group = h5_batch_group.create_group(task_name)
                for k, v in run.items():
                    if not isinstance(v, np.ndarray):
                        if isinstance(v, list):
                            h5_task_group.attrs[k] = str(v)
                        else:
                            h5_task_group.attrs[k] = v
                    elif isinstance(v, np.ndarray):
                        h5_task_group.create_dataset(k, data=v)

    def load_results(self, filename):
        """Load previously saved results.

        Besides reloading results the function can be used to continue
        a partial finished processing process.

        Parameters
        ----------
        filename : str
            filename of the file where processing was stored.

        Returns
        -------
        list
            A list with the output from each macro executed. This maybe empty
            the macros did not output any data.

        Examples
        --------
        Results are easily reloaded:

        >>> app = AnyPyProcess()
        >>> results = app.load_results('saved_results.db')

        Continue processing unfinished batches:

        >>> app.load_results('unfinished_results.db')
        >>> results = app.start_macro() # rerun unfinished

        """
        loadkey = "processed_tasks"
        db = shelve.open(filename)
        loaded_data = db[loadkey]
        db.close()
        # Hack to help Enrico convert data to the new structured
        if not isinstance(loaded_data[0].output, AnyPyProcessOutput):
            for task in loaded_data:
                task.output = AnyPyProcessOutput(task.output)
        self.cached_tasklist = loaded_data
        results = [task.get_output(True) for task in loaded_data]
        return AnyPyProcessOutputList(results)

    def start_macro(
        self, macrolist=None, folderlist=None, search_subdirs=None, logfile=None
    ):
        """Start a batch processing job.

        Runs a list of AnyBody Macro commands in
        the current directory, or in the folders specified by `folderlist`. If
        `search_subdirs` is a regular expression the folderlist will be expanded
        to include all subdirectories that match the regular expression

        Parameters
        ----------
        macrolist : list of macrocommands, optional
            List of anyscript macro commands. This may also be obmitted in
            which case the previous macros will be re-run.
        folderlist : list of str, optional
            List of folders in which to excute the macro commands. If `None` the
            current working directory is used. This may also be a list of
            tuples to specify a name to appear in the output
        search_subdirs : str, optional
            Regular expression used to extend the folderlist with all the
            subdirectories that match the regular expression.
            Defaults to None: No subdirectories are included.
        logfile: str, optional
            If specified an explicit name will be used for the log files generated.
            Otherwise, random names are used for logfiles

        Returns
        -------
        list
            A list with the output from each macro executed. This maybe empty
            the macros did not output any data.


        Examples
        --------
        >>> macro = [['load "model1.any"', 'operation Main.RunApplication', 'run'],
                     ['load "model2.any"', 'operation Main.RunApplication', 'run'],
                     ['load "model3.any"', 'operation Main.RunApplication', 'run']]
        >>> folderlist = [('path1/', 'name1'), ('path2/', 'name2')]
        >>> app.start_macro(macro, folderlist, search_subdirs = "*.main.any")

        """
        # Handle different input types
        if isinstance(macrolist, types.GeneratorType):
            macrolist = list(macrolist)
        if isinstance(macrolist, AnyMacro):
            macrolist = macrolist.create_macros()
        elif isinstance(macrolist, list) and len(macrolist):
            if not isinstance(macrolist[0], (list, tuple)):
                macrolist = [macrolist]
            if isinstance(macrolist[0], list) and len(macrolist[0]):
                macrolist = [
                    [
                        mc.get_macro(index=0) if isinstance(mc, MacroCommand) else mc
                        for mc in elem
                    ]
                    for elem in macrolist
                ]
        elif isinstance(macrolist, str):
            if macrolist.startswith("[") and macrolist.endswith("]"):
                macrolist = macrolist.strip("[").rstrip("]")
                macrolist = [macrolist.split(", ")]
            else:
                macrolist = [[macrolist]]
        elif isinstance(macrolist, (type(None), AnyPyProcessOutputList)):
            pass
        else:
            raise ValueError("Wrong input argument for macrolist")
        # Check folderlist input argument
        if not folderlist:
            folderlist = [os.getcwd()]
        if not isinstance(folderlist, list):
            raise TypeError("folderlist must be a list of folders")
        # Extend the folderlist if search_subdir is given
        if isinstance(search_subdirs, str) and isinstance(folderlist[0], str):
            folderlist = sum([getsubdirs(d, search_subdirs) for d in folderlist], [])
            if len(folderlist) == 0:
                raise ValueError(
                    f"No subdirectories found, which match the file:{search_subdirs}"
                )
        # Check for explicit logfile
        if not isinstance(logfile, (type(None), str, os.PathLike)):
            raise ValueError("logfile must be a str or path")
        # Check the input arguments and generate the tasklist
        if macrolist is None:
            if self.cached_tasklist:
                tasklist = self.cached_tasklist
            else:
                raise ValueError(
                    "macrolist argument can only be ommitted if "
                    "the AnyPyProcess object has cached output "
                    "to process"
                )
        elif isinstance(macrolist[0], collections.abc.Mapping):
            tasklist = list(_Task.from_output_list(macrolist))
        elif isinstance(macrolist[0], list):
            arg_hash = format(
                abs(make_hash([macrolist, folderlist, search_subdirs, logfile])), "x"
            )
            if self.cached_tasklist and self.cached_arg_hash == arg_hash:
                tasklist = self.cached_tasklist
            else:
                self.cached_arg_hash = arg_hash
                tasklist = list(
                    _Task.from_macrofolderlist(macrolist, folderlist, logfile)
                )
        else:
            raise ValueError("Nothing to process for " + str(macrolist))

        # Start the scheduler
        try:
            with tqdm(total=len(tasklist), disable=self.silent) as pbar:
                for task in self._schedule_processes(tasklist):
                    if task.has_error() and not self.silent:
                        tqdm.write(task_summery(task))
                        if hasattr(pbar, "container"):
                            pbar.container.children[0].bar_style = "danger"
                    pbar.update()
        except KeyboardInterrupt as e:
            _subprocess_container.stop_all = True
            tqdm.write("KeyboardInterrupt: User aborted")
            time.sleep(1)
        finally:
            if not self.silent:
                tqdm.write(tasklist_summery(tasklist))

        self.cleanup_logfiles(tasklist)
        # Cache the processed tasklist for restarting later
        self.cached_tasklist = tasklist
        # self.summery.final_summery(process_time, tasklist)
        task_output = [task.get_output() for task in tasklist]
        return AnyPyProcessOutputList(task_output)

    def _worker(self, task, task_queue):
        """Handle processing of the tasks."""
        with _thread_lock:
            task.process_number = self.counter
            self.counter += 1
        if task.output:
            # Skip processing trials already completed without errors
            if not task.has_error() and task.processtime > 0:
                task_queue.put(task)
                return

        if not os.path.exists(task.folder):
            raise (ValueError("The folder does not exists: {}".format(task.folder)))

        try:
            if not task.logfile:
                # If no explicit log file was given use NamedTemporaryFile
                # to create one
                with NamedTemporaryFile(
                    mode="w+",
                    prefix=(self.logfile_prefix or task.name.lower()) + "_(",
                    suffix=").txt",
                    dir=task.folder,
                    delete=False,
                ) as fh:
                    task.logfile = fh.name
            with open(task.logfile, "w+") as logfile:
                logfile.write("########### MACRO #############\n")
                logfile.write("\n".join(task.macro))
                logfile.write("\n\n######### OUTPUT LOG ##########")
                logfile.flush()
                task.logfile = logfile.name
                starttime = time.time()
                exe_args = dict(
                    macro=task.macro,
                    logfile=logfile,
                    anybodycon_path=self.anybodycon_path,
                    timeout=self.timeout,
                    keep_macrofile=self.keep_logfiles,
                    env=self.env,
                    priority=self.priority,
                    debug_mode=self.debug_mode,
                    folder=task.folder,
                )
                try:
                    task.retcode = execute_anybodycon(**exe_args)
                    if task.retcode == _KILLED_BY_ANYPYTOOLS:
                        task.processtime = 0
                    else:
                        task.processtime = time.time() - starttime
                except KeyboardInterrupt as e:
                    task.processtime = 0
                    raise e
                finally:
                    logfile.seek(0)

                task.output = parse_anybodycon_output(
                    logfile.read(),
                    self.ignore_errors,
                    self.warnings_to_include,
                    fatal_warnings=self.fatal_warnings,
                )
        finally:
            if not self.keep_logfiles and not task.has_error():
                silentremove(logfile.name)
                task.logfile = ""
            task_queue.put(task)

    def _schedule_processes(self, tasklist) -> Generator[_Task, None, None]:
        _subprocess_container.stop_all = False
        # Make a shallow copy of the task list,
        # so we don't mess with the callers list.
        tasklist = copy.copy(tasklist)
        number_tasks = len(tasklist)
        use_threading = number_tasks > 1 and self.num_processes > 1
        task_queue: Queue = Queue()
        threads: List[Thread] = []
        # run while there is still threads, tasks or stuff in the queue
        # to process
        while threads or tasklist or task_queue.qsize():
            # if we aren't using all the processors AND there is still
            # data left to compute, then spawn another thread
            if (len(threads) < self.num_processes) and tasklist:
                if use_threading:
                    t = Thread(
                        target=self._worker, args=tuple([tasklist.pop(0), task_queue])
                    )
                    t.daemon = True
                    t.start()
                    threads.append(t)
                else:
                    self._worker(tasklist.pop(0), task_queue)
            else:
                # In the case that we have the maximum number
                # of running threads or we run out tasks.
                # Check if any of them are done
                for thread in threads:
                    if not thread.is_alive():
                        threads.remove(thread)
            while task_queue.qsize():
                task = task_queue.get()
                yield task

            time.sleep(0.05)

    def cleanup_logfiles(self, tasklist):
        for task in tasklist:
            try:
                if not self.keep_logfiles:
                    if not task.has_error() or task.retcode == _KILLED_BY_ANYPYTOOLS:
                        silentremove(task.logfile)
                        task.logfile = ""
            except OSError as e:
                logger.debug("Could not remove " "{} {}".format(task.logfile, str(e)))
            if not self.keep_logfiles and task.logfile:
                try:
                    macrofile = Path(task.logfile).with_suffix(".anymcr")
                    silentremove(macrofile)
                except OSError as e:
                    logger.debug(f"Could not remove: {macrofile} {e}")
