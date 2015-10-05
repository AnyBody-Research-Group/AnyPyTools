# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 21:14:59 2012

@author: Morten
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *  # nopep8
from future.utils import text_to_native_str
from past.builtins import basestring as string_types

import os
import sys
import time
import copy
import types
import errno
import ctypes
import shelve
import atexit
import logging
import collections

from subprocess import Popen
from tempfile import NamedTemporaryFile
from threading import Thread, RLock
from queue import Queue

from .utils import (make_hash, AnyPyProcessOutputList, parse_anybodycon_output,
                    getsubdirs, get_anybodycon_path, mixedmethod,
                    AnyPyProcessOutput)
from .macroutils import AnyMacro, MacroCommand

try:
    __IPYTHON__
    from IPython.display import clear_output, HTML, display
    import ipywidgets
except NameError:
    pass

logger = logging.getLogger('abt.anypytools')

_thread_lock = RLock()
_KILLED_BY_ANYPYTOOLS = -10


class SubProcessContainer(object):
    """ Class to hold a record of process pids from Popen.

        Properties:
        ------------
        stop_all: boolean
            If set to True all process held by the object will be automatically
            killed

        Methods:
        -----------
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
        with _thread_lock:
            if value:
                self._stop_all = True
                self._kill_running_processes()
            else:
                self._stop_all = False

    def _kill_running_processes(self):
        """ Clean up and shut down any running processes
        """
        # Kill any rouge processes that are still running.
        with _thread_lock:
            killed = []
            for pid in self._pids:
                try:
                    os.kill(pid, _KILLED_BY_ANYPYTOOLS)
                    killed.append(str(pid))
                except:
                    pass
            self._pids.clear()


_subprocess_container = SubProcessContainer()
atexit.register(_subprocess_container._kill_running_processes)


def _silentremove(filename):
    """ Removes a file ignoring cases where the file does not exits.  """
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:  # errno.ENOENT : no such file or directory
            logging.debug('Error removing file: ' + filename)
            raise  # re-raise exception if a different error occured


def _get_ncpu():
    """ Return the number of CPUs in the computer
    """
    from multiprocessing import cpu_count
    return cpu_count()


def _run_from_ipython():
    try:
        __IPYTHON__
        return True
    except NameError:
        return False


def _display(line, *args, **kwargs):
    if _run_from_ipython():
        display(HTML(line))
    else:
        print(line, *args, **kwargs)


def _execute_anybodycon(macro,
                        logfile,
                        anybodycon_path=get_anybodycon_path(),
                        timeout=3600,
                        keep_macrofile=False,
                        env=None):
    """ Launches the AnyBodyConsole applicaiton with the specified macro
        saving the result to logfile """
    if not os.path.isfile(anybodycon_path):
        raise IOError("Can not find anybodycon.exe: " + anybodycon_path)
    macro_filename = os.path.splitext(logfile.name)[0] + '.anymcr'
    with open(macro_filename, 'w+b') as macro_file:
        macro_file.write('\n'.join(macro).encode('UTF-8'))
        macro_file.flush()
    anybodycmd = [os.path.realpath(anybodycon_path),
                  '--macro=', macro_file.name, '/ni']
    if sys.platform.startswith("win"):
        # Don't display the Windows GPF dialog if the invoked program dies.
        # See comp.os.ms-windows.programmer.win32
        # How to suppress crash notification dialog?, Jan 14,2004 -
        # Raymond Chen's response [1]
        SEM_NOGPFAULTERRORBOX = 0x0002  # From MSDN
        ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX)
        subprocess_flags = 0x8000000   # win32con.CREATE_NO_WINDOW?
    else:
        subprocess_flags = 0
    try:
        # Check global module flag to avoid starting processes after
        # the user cancelled the processes
        proc = Popen(anybodycmd,
                     stdout=logfile,
                     stderr=logfile,
                     creationflags=subprocess_flags,
                     env=env)
        _subprocess_container.add(proc.pid)
        timeout_time = time.clock() + timeout
        while proc.poll() is None:
            if time.clock() > timeout_time:
                proc.terminate()
                proc.communicate()
                logfile.seek(0, 2)
                logfile.write('ERROR: Timeout after {:d} sec.'.format(timeout))
                break
            time.sleep(0.05)
        _subprocess_container.remove(proc.pid)
        if proc.returncode == _KILLED_BY_ANYPYTOOLS:
            logfile.write('Anybodycon.exe was interrupted by AnyPyTools')
        elif proc.returncode:
            logfile.write('ERROR: anybodycon.exe exited unexpectedly.'
                          ' Return code: ' + str(proc.returncode))
        if not keep_macrofile:
            _silentremove(macro_file.name)
    finally:
        logfile.seek(0)
    return proc.returncode


class _Task(object):
    """Class for storing processing jobs

    Attributes:
        folder: directory in which the macro is executed
        macro: list of macro commands to execute
        number: id number of the task
        name: name of the task, which is used for printing status informations
    """
    def __init__(self, folder=None, macro=None,
                 taskname=None, number=1):
        """ Init the Task class with the class attributes
        """
        self.folder = folder
        if not folder:
            self.folder = os.getcwd()
        if macro is not None:
            self.macro = macro
        else:
            self.macro = []
        self.output = AnyPyProcessOutput()
        self.number = number
        self.logfile = ""
        self.processtime = 0
        self.name = taskname
        if not taskname:
            head, folder = os.path.split(folder)
            parentfolder = os.path.basename(head)
            self.name = parentfolder + '/' + folder

    @property
    def has_error(self):
        return 'ERROR' in self.output

    def add_error(self, error_msg):
        try:
            self.output['ERROR'].append(error_msg)
        except KeyError:
            self.output['ERROR'] = [error_msg]

    def get_output(self, include_task_info):
        out = self.output
        if include_task_info:
            out['task_macro_hash'] = make_hash(self.macro)
            out['task_id'] = self.number
            out['task_work_dir'] = self.folder
            out['task_name'] = self.name
            out['task_processtime'] = self.processtime
            out['task_macro'] = self.macro
            out['task_logfile'] = self.logfile
        return out

    @classmethod
    def from_output_data(cls, task_output):
        if not cls.is_valid(task_output):
            raise ValueError('Output can only be reprocessed, if "Task info"'
                             'is included in the output.')
        task = cls(folder=task_output['task_work_dir'],
                   macro=task_output['task_macro'],
                   taskname=task_output['task_name'],
                   number=task_output['task_id'])
        task.processtime = task_output['task_processtime']
        task.output = task_output
        return task

    @classmethod
    def from_output_list(cls, outputlist):
        for elem in outputlist:
            yield cls.from_output_data(elem)

    @classmethod
    def from_macrofolderlist(cls, macrolist, folderlist):
        if not macrolist:
            raise StopIteration
        macrofolderlist = ((m, f) for f in folderlist for m in macrolist)
        for i, (macro, folder) in enumerate(macrofolderlist):
            yield cls(folder, macro, number=i)

    @staticmethod
    def is_valid(output_elem):
        keys = ('task_macro_hash', 'task_id', 'task_work_dir', 'task_name',
                'task_processtime', 'task_macro', 'task_logfile')
        return all(k in output_elem for k in keys)


class Summery(object):
    """ class to display the summery of task """
    def __init__(self, have_ipython=False, disp=True):
        self._disp = disp
        if have_ipython and self._disp:
            self.ipywidget = ipywidgets.HTML()
            self.ipywidget.initialized = False
        else:
            self.ipywidget = None

    def task_summery(self, task):
        if self.ipywidget:
            if task.has_error:
                self._display(self.format_summery(task))

    def _display(self, s):
        if self.ipywidget is not None:
            if not self.ipywidget.initialized:
                display(self.ipywidget)
                self.ipywidget.initialized = True
            self.ipywidget.value += s + '<br>'
        else:
            print(s)

    def format_summery(self, task):
        entry = ''
        if task.has_error:
            entry += 'Failed :'
        elif task.processtime == 0:
            entry += 'Not completed :'
        else:
            entry += 'Completed :'
        entry += '{1!s} : {2:4.1} sec : {0} : '.format(task.name,
                                                       task.number,
                                                       task.processtime)
        if task.logfile:
            if _run_from_ipython():
                tmpl = '<a href="file:///{0}" target="_blank">{1}</a>'
                entry += tmpl.format(task.logfile,
                                     os.path.basename(task.logfile))
            else:
                entry += '{0}'.format(os.path.basename(task.logfile))
        return entry


    def final_summery(self, total_process_time, tasklist):
        unfinished_tasks = [t for t in tasklist if t.processtime <= 0]
        failed_tasks = [t for t in tasklist
                        if t.has_error and t.processtime > 0]
        if len(failed_tasks):
            self._display('Tasks with errors: {:d}'.format(len(failed_tasks)))
            if self._disp and self.ipywidget is None:
                self._display('\n'.join([self.format_summery(t)
                                         for t in failed_tasks]))
        if len(unfinished_tasks):
            self._display('Tasks that did not complete: '
                          '{:d}'.format(len(unfinished_tasks)))
        self._display('Total time: {:.1f} seconds'.format(total_process_time))


class AnyPyProcess(object):
    """
    AnyPyProcess(num_processes = nCPU,
                 anybodycon_path = 'installed version',
                 timeout = 3600, disp = True, keep_logfiles = False)

    Commen class for setting up batch process jobs of AnyBody models.

    Overview
    ----------
    Main class for running the anybody console application from python.
    The class have maethods for running different kind of batch processing:

    - Batch job: running many different models)

    - Parameter jobs: running the same model multiple times with different
      input parameters. (Usefull for sensitivity studies)

    - Pertubation jobs: Find the sensitivity of of some output parameters,
      given a set of input parameters. (Usefull for calculating the
      gradient in optimization studies)

    Parameters
    ----------
    num_processes:
        number of anybody models to start in parallel.
        This defaults to the number of CPU in the computer.
    anybodycon_path:
        Overwrite the default anybodycon.exe file to
        use in batch processing
    timeout:
        maximum time a model can run until it is terminated.
        Defaults to 1 hour
    ignore_errors:
        List of AnyBody Errors to ignore when running the models
    return_task_info: bool
        Return the task status information when running macros
    disp:
        Set to False to suppress output
    warnings_to_include:
        List of strings that are matched to warnings in the model
        output. If a warning with that string is found the warning
        is returned in the output.

    Returns
    -------
    AnyPyProcess object:
        a AnyPyProcess object for running batch processing, parameter
        studies and pertubation jobs.
    """
    def __init__(self,
                 num_processes=_get_ncpu(),
                 anybodycon_path=None,
                 timeout=3600,
                 disp=True,
                 ignore_errors=None,
                 warnings_to_include=None,
                 return_task_info=False,
                 keep_logfiles=False,
                 logfile_prefix='',
                 python_env=None):

        if anybodycon_path is None:
            self.anybodycon_path = get_anybodycon_path()
        elif os.path.exists(anybodycon_path):
            self.anybodycon_path = anybodycon_path
        else:
            raise FileNotFoundError("Can't find " + anybodycon_path)
        self.num_processes = num_processes
        self.disp = disp
        self.timeout = timeout
        self.counter = 0
        self.return_task_info = return_task_info
        self.ignore_errors = ignore_errors
        self.warnings_to_include = warnings_to_include
        self.keep_logfiles = keep_logfiles
        self.logfile_prefix = logfile_prefix
        self.cached_arg_hash = None
        self.cached_tasklist = None
        if python_env is not None:
            if not os.path.isdir(python_env):
                raise FileNotFoundError('Python environment does'
                                        ' not exist:' + python_env)
            env = dict(os.environ)
            env['PYTHONHOME'] = python_env
            env['PATH'] = env['PYTHONHOME'] + ';' + env['PATH']
            self.env = env
        else:
            self.env = None
        logging.debug('\nAnyPyProcess initialized')

    def save_results(self, filename, append=False):
        if self.cached_tasklist:
            savekey = text_to_native_str('processed_tasks')
            db = shelve.open(text_to_native_str(filename), writeback=True)
            if not append or savekey not in db:
                db[savekey] = self.cached_tasklist
            else:
                db[savekey].extend(self.cached_tasklist)
            db.close()
        else:
            raise ValueError('Noting to save')

    @mixedmethod
    def load_results(self, cls, filename):
        loadkey = text_to_native_str('processed_tasks')
        db = shelve.open(text_to_native_str(filename))
        loaded_data = db[loadkey]
        db.close()
        # Hack to help Enrico convert data to the new structured
        if not isinstance(loaded_data[0].output, AnyPyProcessOutput):
            for task in loaded_data:
                task.output = AnyPyProcessOutput(task.output)
        # Check if the functions is called as an instance method.
        if self is not None:
            self.cached_tasklist = loaded_data
        results = [task.get_output(True) for task in loaded_data]
        return AnyPyProcessOutputList(results)

    def start_macro(self, macrolist=None, folderlist=None, search_subdirs=None,
                    **kwargs):
        """
        app.start_marco(macrolist, folderlist = None, search_subdirs =None )

        Starts a batch processing job. Runs a list of AnyBody Macro commands in
        the current directory, or in the folders specified by folderlist. If
        search_subdirs is a regular expression the folderlist will be expanded
        to include all subdirectories that match the regular expression

        Parameters
        ----------

        macrolist:
            List or generator containing lists of anyscript macro commands
        folderlist:
            List of folders in which to excute the macro commands. If None the
            current working directory is used. This may also be a list of
            tuples to specify a name to appear in the output
        search_subdirs:
            Regular expression used to extend the folderlist with all the
            subdirectories that match the regular expression.
            Defaults to None: No subdirectories are included.

            For example:

            >>> macro=[ ['load "model1.any"', 'operation Main.RunApplication',\
                         'run', 'exit'],\
                        ['load "model2.any"', 'operation Main.RunApplication',\
                         'run', 'exit'],\
                        ['load "model3.any"', 'operation Main.RunApplication',\
                         'run', 'exit'] ]
            >>> folderlist = [('path1/', 'name1'), ('path2/', 'name2')]
            >>> start_macro(macro, folderlist, search_subdirs = "*.main.any")

        """
        # Handle different input types
        if isinstance(macrolist, types.GeneratorType):
            macrolist = list(macrolist)
        if isinstance(macrolist, AnyMacro):
            macrolist = macrolist.create_macros()
        elif isinstance(macrolist, list) and len(macrolist):
            if isinstance(macrolist[0], string_types):
                macrolist = [macrolist]
            if isinstance(macrolist[0], MacroCommand):
                macrolist = [macrolist]
            if isinstance(macrolist[0], list) and len(macrolist[0]):
                if isinstance(macrolist[0][0], MacroCommand):
                    macrolist = [[mc.get_macro(index=0) for mc in elem]
                                 for elem in macrolist]
        elif isinstance(macrolist, string_types):
            if macrolist.startswith('[') and macrolist.endswith(']'):
                macrolist = macrolist.strip('[').rstrip(']')
                macrolist = [macrolist.split(', ')]
            else:
                macrolist = [[macrolist]]
        elif isinstance(macrolist, (type(None), AnyPyProcessOutputList)):
            pass
        else:
            raise ValueError('Wrong input argument for macrolist')
        # Check folderlist input argument
        if not folderlist:
            folderlist = [os.getcwd()]
        if not isinstance(folderlist, list):
            raise TypeError('folderlist must be a list of folders')
        # Extend the folderlist if search_subdir is given
        if (isinstance(search_subdirs, string_types) and
                isinstance(folderlist[0], string_types)):
            folderlist = sum([getsubdirs(d, search_subdirs)
                              for d in folderlist], [])
        # Check the input arguments and generate the tasklist
        if macrolist is None:
            if self.cached_tasklist:
                tasklist = self.cached_tasklist
            else:
                raise ValueError('macrolist argument can only be ommitted if '
                                 'the AnyPyProcess object has cached output '
                                 'to process')
        elif isinstance(macrolist[0], collections.Mapping):
            tasklist = list(_Task.from_output_list(macrolist))
        elif isinstance(macrolist[0], list):
            arg_hash = make_hash([macrolist, folderlist, search_subdirs])
            if self.cached_tasklist and self.cached_arg_hash == arg_hash:
                tasklist = self.cached_tasklist
            else:
                self.cached_arg_hash = arg_hash
                tasklist = list(_Task.from_macrofolderlist(macrolist,
                                                           folderlist))
        else:
            raise ValueError('Nothing to process for ' + str(macrolist))

        self.summery = Summery(have_ipython=_run_from_ipython(),
                               disp=self.disp)

        # Start the scheduler
        process_time = self._schedule_processes(tasklist, self._worker)
        self.cleanup_logfiles(tasklist)
        # Cache the processed tasklist for restarting later
        self.cached_tasklist = tasklist
        self.summery.final_summery(process_time, tasklist)
        task_output = [task.get_output(include_task_info=self.return_task_info)
                       for task in tasklist]
        return AnyPyProcessOutputList(task_output)


#    def _print_summery(self, tasks, duration):
#        unfinished_tasks = [t for t in tasks if t.processtime <= 0]
#        failed_tasks = [t for t in tasks if t.has_error and t.processtime > 0]
#        if len(failed_tasks):
#            _display('Tasks with errors: {:d}'.format(len(failed_tasks)))
#            if not _run_from_ipython():
#                _display('\n'.join([t.summery() for t in failed_tasks]))
#        if len(unfinished_tasks):
#            _display('Tasks that did not complete: '
#                     '{:d}'.format(len(unfinished_tasks)))
#        if duration:
#            _display('Total time: {:.1f} seconds'.format(duration))

    def _worker(self, task, task_queue):
        """ Handles processing of the tasks.
        """
        with _thread_lock:
            task.process_number = self.counter
            self.counter += 1
        if task.output:
            if not task.has_error and task.processtime > 0:
                if not os.path.isfile(task.logfile):
                    task.logfile = ""
                task_queue.put(task)
                return
        try:
            if not os.path.exists(task.folder):
                task.add_error('Could not find folder: {}'.format(task.folder))
                task.logfile = ""
            else:
                with NamedTemporaryFile(mode='a+',
                                        prefix=self.logfile_prefix + '_',
                                        suffix='.log',
                                        dir=task.folder,
                                        delete=False) as logfile:
                    logfile.write('########### MACRO #############\n')
                    logfile.write("\n".join(task.macro))
                    logfile.write('\n\n######### OUTPUT LOG ##########')
                    logfile.flush()
                    task.logfile = logfile.name
                    starttime = time.clock()
                    exe_args = dict(macro=task.macro,
                                    logfile=logfile,
                                    anybodycon_path=self.anybodycon_path,
                                    timeout=self.timeout,
                                    keep_macrofile=self.keep_logfiles,
                                    env=self.env)
                    retcode = _execute_anybodycon(**exe_args)
                    endtime = time.clock()
                    logfile.seek(0)
                    if retcode == _KILLED_BY_ANYPYTOOLS:
                        task.processtime = 0
                        return
                    task.processtime = endtime - starttime
                    task.output = parse_anybodycon_output(
                                      logfile.read(),
                                      self.ignore_errors,
                                      self.warnings_to_include)
        except Exception as e:
            task.add_error(str(type(e)) + str(e))
            logger.debug(str(e))
        finally:
            if not self.keep_logfiles and not task.has_error:
                try:
                    _silentremove(logfile.name)
                    task.logfile = ""
                except OSError as e:
                    pass  # Ignore if AnyBody has not released the log file.
            task_queue.put(task)

    def _schedule_processes(self, tasklist, _worker):
        # Reset the global flag that allows
        global _stop_all_processes
        _subprocess_container.stop_all = False
        # Make a shallow copy of the task list,
        # so we don't mess with the callers list.
        tasklist = copy.copy(tasklist)
        number_tasks = len(tasklist)
        if number_tasks == 0:
            totaltime = 0
            return totaltime
        use_threading = (number_tasks > 1 and self.num_processes > 1)
        starttime = time.clock()
        task_queue = Queue()
        pbar = ProgressBar(number_tasks, self.disp)
        pbar.animate(0)
        processed_tasks = []
        n_errors = 0
        threads = []
        try:
            # run while there is still threads, tasks or stuff in the queue
            # to process
            while threads or tasklist or task_queue.qsize():
                # if we aren't using all the processors AND there is still
                # data left to compute, then spawn another thread
                if (len(threads) < self.num_processes) and tasklist:
                    if use_threading:
                        t = Thread(target=_worker,
                                   args=tuple([tasklist.pop(0), task_queue]))
                        t.daemon = True
                        t.start()
                        threads.append(t)
                    else:
                        _worker(tasklist.pop(0), task_queue)
                else:
                    # In the case that we have the maximum number
                    # of running threads or we run out tasks.
                    # Check if any of them are done
                    for thread in threads:
                        if not thread.isAlive():
                            threads.remove(thread)
                while task_queue.qsize():
                    task = task_queue.get()
                    if task.has_error:
                        n_errors += 1
                    self.summery.task_summery(task)
                    processed_tasks.append(task)
                    pbar.animate(len(processed_tasks), n_errors)

                time.sleep(0.01)
        except KeyboardInterrupt:
            _display('Processing interrupted')
            _subprocess_container.stop_all = True
            # Add a small delay here. It allows the user to press ctrl-c twice
            # to escape this try-catch. This is usefull when if the code is
            # run in an outer loop which we want to excape as well.
            time.sleep(1)
        totaltime = time.clock() - starttime
        return totaltime

    def cleanup_logfiles(self, tasklist):
        for task in tasklist:
            try:
                if not self.keep_logfiles and not task.has_error:
                    if task.logfile:
                        _silentremove(task.logfile)
                        task.logfile = ""
                if task.processtime <= 0 and task.logfile:
                    _silentremove(task.logfile)
                    task.logfile = ""
            except OSError as e:
                logger.debug('Could not remove '
                             '{} {}'.format(task.logfile, str(e)))
            if not self.keep_logfiles:
                try:
                    macrofile = task.logfile.replace('.log', '.anymcr')
                    _silentremove(macrofile)
                except OSError as e:
                    logger.debug('Could not removing '
                                 '{} {}'.format(macrofile, str(e)))


class ProgressBar:
    def __init__(self, iterations, disp=True):
        self.disp = disp
        self.iterations = iterations
        self.prog_bar = '[]'
        self.fill_char = '*'
        self.width = 40
        if _run_from_ipython() and self.disp:
            self.bar_widget = ipywidgets.IntProgress(
                                min=0, max=iterations, value=0)
            display(self.bar_widget)

    def animate(self, val, failed=0):
        if not self.disp:
            return
        if _run_from_ipython():
            self.bar_widget.value = val
            self.bar_widget.description = '%d of %s complete' % (val,
                                                self.iterations)
        else:
            self.update_iteration(val, failed)
            print('\r', end="")
            print(self.prog_bar, end="")
            sys.stdout.flush()

    def update_iteration(self, elapsed_iter, number_failed, tasks=[]):
        self.__update_amount((elapsed_iter / float(self.iterations)) * 100.0)
        self.prog_bar += '  %d of %s complete' % (elapsed_iter,
                                                  self.iterations)
        if number_failed == 1:
            self.prog_bar += ' ({0} Error)'.format(number_failed)
        elif number_failed > 1:
            self.prog_bar += ' ({0} Errors)'.format(number_failed)

    def __update_amount(self, new_amount):
        percent_done = int(round((new_amount / 100.0) * 100.0))
        all_full = self.width - 2
        num_hashes = int(round((percent_done / 100.0) * all_full))
        self.prog_bar = ('[' +
                         self.fill_char * num_hashes +
                         ' ' * (all_full - num_hashes) +
                         ']')
        pct_place = int(len(self.prog_bar) / 2) - len(str(percent_done))
        pct_string = '%d%%' % percent_done
        self.prog_bar = self.prog_bar[0:pct_place] + \
            (pct_string + self.prog_bar[pct_place + len(pct_string):])


if __name__ == '__main__':
    pass
