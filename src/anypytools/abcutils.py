# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 21:14:59 2012

@author: Morten
"""
from __future__ import division, absolute_import, print_function, unicode_literals
try:
    from .utils.py3k import * # @UnusedWildImport
    from .utils import make_hash
except (ValueError, SystemError):
    from utils.py3k import * # @UnusedWildImport
    from utils import make_hash

import copy



import os
from subprocess import Popen, CREATE_NEW_PROCESS_GROUP
import numpy as np
from tempfile import NamedTemporaryFile, TemporaryFile
from threading import Thread
from functools import wraps
import collections
import time 
import signal
import re
import atexit
from ast import literal_eval
try:
    import Queue as queue
except ImportError:
    import queue
import sys
import types
import ctypes



try:
    from IPython.display import clear_output, HTML, display, FileLinks
    have_ipython = True
except ImportError:
    have_ipython = False
    


#print_lock = Lock()

_pids = set()
def _kill_running_processes():
    """ Clean up and shut down any running processes
    """
    # Kill any rouge processes that are still running.
    for pid in _pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print('Kill AnyBodyCon Process. PID: ', pid)
        except:
            pass
    _pids.clear()
atexit.register(_kill_running_processes)


def get_anybodycon_path():
    """  Return the path to default AnyBody console application 
    """
    try: 
        import winreg
    except ImportError:
        import _winreg as winreg
    
    abpath = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                    'AnyBody.AnyScript\shell\open\command')
    abpath = abpath.rsplit(' ',1)[0].strip('"')
    return os.path.join(os.path.dirname(abpath),'AnyBodyCon.exe')

def get_ncpu():
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
 


def getsubdirs(toppath, search_string = "."):
    """ Find all directories below a given top path. 
    
    Args: 
        toppath: top directory when searching for sub directories
        search_string: Limit to directories matching the this regular expression
    Returns:
        List of directories
    """
    if search_string is None:
        return [toppath]
    reg_prog = re.compile(search_string)    
    dirlist = []
    if search_string == ".":
        dirlist.append(toppath)
    for root, dirs, files in os.walk(toppath):
        for fname in files:
            if reg_prog.search(os.path.join(root,fname)) is not None:
                dirlist.append(root)
                continue
    uniqueList = []
    for value in dirlist:
        if value not in uniqueList:
            uniqueList.append(value)    
    return uniqueList


def _execute_anybodycon( macro, logfile, anybodycon_path, timeout):
    """ Launches the AnyBodyConsole applicaiton with the specified macro
        saving the result to logfile
    """
    with open(os.path.splitext(logfile.name)[0] + '.anymcr', 'w+b' ) as macrofile:
        macrofile.write( '\n'.join(macro).encode('UTF-8') )
        macrofile.flush()
    anybodycmd = [os.path.realpath(anybodycon_path), 
                  '--macro=', macrofile.name, '/ni'] 
   
   
    if sys.platform.startswith("win"):
        # Don't display the Windows GPF dialog if the invoked program dies.
        # See comp.os.ms-windows.programmer.win32
        # How to suppress crash notification dialog?, Jan 14,2004 -
        # Raymond Chen's response [1]
        SEM_NOGPFAULTERRORBOX = 0x0002 # From MSDN
        ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX);
        subprocess_flags = 0x8000000 #win32con.CREATE_NO_WINDOW?
    else:
        subprocess_flags = 0
            
    proc = Popen(anybodycmd, stdout=logfile, 
                            stderr=logfile, 
                            creationflags=subprocess_flags)                      
    _pids.add(proc.pid)
    timeout_time =time.clock() + timeout
    
    while proc.poll() is None:
        if time.clock() > timeout_time:
            proc.terminate()
            proc.communicate()
            logfile.seek(0,2)
            logfile.write('ERROR: Timeout. Terminated by'
                             ' AnyPyTools'.encode('UTF-8') )
            break
        time.sleep(0.3)
    else:
        if proc.pid in _pids:
            _pids.remove(proc.pid)
    
    os.unlink(macrofile.name)


class AnyPyProcessOutputList(list):
    pass



class _Task():
    """Class for storing processing jobs

    Attributes:
        folder: directory in which the macro is executed
        macro: list of macro commands to executre
        number: id number of the task
        name: name of the task, which is used for printing status informations
    """
    def __init__(self,folder=None, macro = [], 
                 taskname = None, number = 1, return_task_info = True):
        """ Init the Task class with the class attributes
        """
        self.folder = folder
        if folder is None:
            self.folder = os.getcwd()
        self.macro = macro
        self.output = collections.OrderedDict()
        self.number = number
        self.logfile = ""
        self.processtime = 0
        self.name = taskname
        self.return_task_info = return_task_info
        if taskname is None:
            head, folder = os.path.split(folder)
            parentfolder = os.path.basename(head)
            self.name = parentfolder+'/'+folder + '_'+ str(number)
    
    @property
    def error(self):
        return 'ERROR' in self.output
                         
    def get_output(self):
        out = self.output
#        if 'ERROR' not in out:
#            out['ERROR'] = []
        if self.return_task_info is True:           
            out['task_macro_hash'] =  make_hash(self.macro)  
            out['task_id'] =  self.number
            out['task_work_dir'] =   self.folder 
            out['task_name'] =   self.name 
            out['task_processtime'] = self.processtime
            out['task_macro'] =  self.macro
            out['task_logfile'] = self.logfile
        return out
      
    @staticmethod
    def init_from_output( task_output):
        if not _Task.is_valid( task_output):
            raise ValueError('Output can only be reprocessed, if "Task info" is '
                             'included in the output.')
        
        task = _Task(folder = task_output['task_work_dir'], 
                     macro = task_output['task_macro'],
                     taskname = task_output['task_name'], 
                     number = task_output['task_id'])
        task.processtime = task_output['task_processtime']
        task.output = task_output
        return task
        
        
    @staticmethod
    def is_valid(output_elem):
        keys =  ( 'task_macro_hash','task_id','task_work_dir','task_name',
                  'task_processtime','task_macro','task_logfile')
        return all(k in output_elem for k in keys)
        
        
class AnyPyProcess():
    """
    AnyPyProcess(num_processes = nCPU,\
                 anybodycon_path = 'installed version', stop_on_error = True,\
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
        
    Returns
    -------
    AnyPyProcess object: 
        a AnyPyProcess object for running batch processing, parameter
        studies and pertubation jobs.       
    """    
    def __init__(self, num_processes = get_ncpu(), 
                 anybodycon_path = get_anybodycon_path(), stop_on_error = True,
                 timeout = 3600, disp = True, ignore_errors = [],
                 return_task_info = False,
                 keep_logfiles = False, logfile_prefix = '', blaze_ouput = False):
        self.anybodycon_path = anybodycon_path
        self.stop_on_error = stop_on_error
        self.num_processes = num_processes
        self.counter = 0
        self.disp = disp
        self.timeout = timeout
        self.return_task_info = return_task_info 
        self.ignore_errors = ignore_errors
        self.keep_logfiles = keep_logfiles
        self.logfile_prefix = logfile_prefix
        self.blaze_output = blaze_ouput
        self.cached_arg_hash = None
        self.cached_output = None

    
    def cache_results(arg1, arg2, arg3):
        def _cach_result(f):
            #print( "Inside wrap()")
            @wraps(f)
            def wrapper(self, *args, **kwargs):
                #print("Inside wrapped_f()" )
                #print("Decorator arguments:", arg1, arg2, arg3 )
                macro = args[0]
                if 'cache_mode' in kwargs:
                    pass
                    #print(kwargs['cache_mode'])
                print( make_hash(macro) ) 
                output = f(self,*args,**kwargs)
                return output
                #print("After f(*args)")
            return wrapper
        return _cach_result

    def set_cached_output(self, results):
        self.cached_output = results
        self.cached_arg_hash = None
    
    
    #@cache_results(1,2,3)
    def start_macro(self, macrolist, folderlist = None, search_subdirs = None,
                    number_of_macros = 0,**kwargs ):
        """ 
        app.start_marco(macrolist, folderlist = None, search_subdirs =None )        
        
        Starts a batch processing job. Runs an list of AnyBody Macro commands in 
        the current directory, or in the folders specified by folderlist. If 
        search_subdirs is a regular expression the folderlist will be expanded
        to include all subdirectories that match the regular expression
        
        Parameters
        ----------
        
        macrolist:
            List or generator containing lists of anyscript macro commands
        folderlist:
            list of folders in which to excute the macro commands. If None the
            current working directory is used. This may also be a list of
            tuples to specify a name to appear in the output
        search_subdirs:
            Regular expression used to extend the folderlist with all the
            subdirectories that match the regular expression. 
            Defaults to None: subdirectories are included.
        number_of_macros:
            Number of macros in macrolist. Must be specified if macrolist
            is a genertors expression. 
                        
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
        if isinstance(macrolist, types.GeneratorType):
            macrolist = list(macrolist)
        assert isinstance(macrolist, collections.Iterable), "Macrolist must be iterable"
        
        if not isinstance(macrolist[0], collections.Mapping) :
            cached_arg_hash = make_hash([macrolist, folderlist, search_subdirs])
            if self.cached_output and cached_arg_hash == self.cached_arg_hash:
                macrolist = self.cached_output
            else:
                self.cached_arg_hash = cached_arg_hash
        

        if folderlist is None:
            folderlist = [os.getcwd()]
            
        if not isinstance(folderlist,list):
            raise TypeError('folderlist must be a list of folders')
        
        # Extend the folderlist if search_subdir is given
        if isinstance(search_subdirs,string_types) and isinstance(folderlist[0], string_types):
            tmplist = []
            for folder in folderlist:
               tmplist.extend(getsubdirs(folder, search_string = search_subdirs) )
            folderlist = tmplist
        
        # Wrap macro in extra list if necessary
        if isinstance(macrolist, list):
            if isinstance(macrolist[0], string_types):
                macrolist = [macrolist]
             
             
        if isinstance(macrolist[0], collections.Mapping):
            # start_macro was called with the result of a previous analysis
            tasklist = [_Task.init_from_output(t) for t in macrolist] 
        else:
            tasklist = self._create_task_list(macrolist, folderlist)
            assert len(tasklist) == len(macrolist) * len(folderlist)
        
        process_time = self._schedule_processes(tasklist, self._worker)
        
        self._print_summery(tasklist,process_time)
               
        return_data = AnyPyProcessOutputList([task.get_output() for task in tasklist])

        if self.blaze_output:
            from .utils.blaze_converter import convert_data
            return_data = convert_data(return_data) 

        if self.return_task_info:
            self.cached_output = return_data
        else:
            self.cached_output = None
        
        return return_data
   
     
   
   
    def _create_task_list(self, macrolist , folderlist ) :
        def generate_tasks(macros, folders):
            taskid = 0
            number_of_macros = len(macrolist)
            for i_macro, macro in enumerate(macros):
                for folder in folders:
                    if isinstance(folder ,tuple) and len(folder) ==2:
                        folder, taskname = folder
                        if number_of_macros > 1:
                            taskname = taskname + ' macro '+str(i_macro) 
                    else:
                        taskname = None
                    yield _Task(folder, macro, 
                                taskname = taskname,
                                number = taskid,
                                return_task_info=self.return_task_info)
                    taskid += 1
        if not macrolist:
            return []
        else:
            return list(generate_tasks(macrolist, folderlist) )        
        
        
        
    def _print_summery(self, tasks ,duration):
        if self.disp is False:
            return
        print('')
        unfinished_tasks = [t for t in tasks if t.processtime == 0]
        failed_tasks = [t for t in tasks if t.error ]
        
        def _display(line):
            if  _run_from_ipython():
                display(HTML('<div STYLE="font-family: Courier; line-height:90%;">'+line+'</div>'))
            else:
                print(line)
            
        if len(failed_tasks):
            print('Tasks with errors: {:d}'.format(len(failed_tasks)) )
        for task in failed_tasks:
            _display( _summery(task) ) 
        
        if len(unfinished_tasks):
            print('Tasks that did not complete: {:d}'.format(len(unfinished_tasks)) )
#        for task in unfinished_tasks:
#            _display( _summery(task) ) 

        if duration is not None:
            print( 'Total time: {:d} seconds'.format(duration))




    def _worker (self, task, task_queue):
        """ Handles processing of the tasks.  
        """
 
        task.process_number = self.counter 
        self.counter += 1
 
        if task.output:
            if not 'ERROR' in task.output and task.processtime > 0:
                if not os.path.isfile(task.logfile):
                    task.logfile = ""
                task_queue.put(task)
                return
            

        starttime = time.clock()
        if not os.path.exists(task.folder):
            task.output = {'ERROR':' Could not find folder: {}'.format(task.folder)} 
            task.logfile = None
        else:
            with NamedTemporaryFile(mode='a+',
                                    prefix =self.logfile_prefix + '_' ,
                                    suffix='.log',
                                    dir = task.folder,
                                    delete = False) as logfile:
                logfile.write('########### MACRO #############\n')
                logfile.write("\n".join(task.macro))
                logfile.write('\n\n######### OUTPUT LOG ##########')
                logfile.flush()
                
                _execute_anybodycon( macro = task.macro, 
                                     logfile = logfile, 
                                     anybodycon_path = self.anybodycon_path,
                                     timeout = self.timeout )            
    
                logfile.seek(0)
                task.output = _parse_anybodycon_output(logfile.read() )
                task.logfile = logfile.name

        # Remove any ERRORs which should be ignored
        if 'ERROR' in task.output:
            def check_error(error_string):
                return all( [(err not in error_string) for err in self.ignore_errors])
            task.output['ERROR'][:] = [err for err in task.output['ERROR'] if check_error(err)]

            if not task.output['ERROR']:
                del task.output['ERROR']
        
        task.processtime = time.clock() - starttime
        
        task_queue.put(task)
         
       

    def _schedule_processes(self, tasklist, _worker):
        # Make a shallow copy of the task list, so we don't mess with the callers
        # list. 
        tasklist = copy.copy(tasklist)
        
        number_tasks = len(tasklist)
        
        if number_tasks == 0:
            totaltime = 0
            return totaltime
            
        use_threading = ( number_tasks > 1 and self.num_processes > 1 )
            
        starttime = time.clock()    
        task_queue = queue.Queue()
        
        if self.disp:
            pbar = ProgressBar(number_tasks)
            pbar.animate(0)
        
        processed_tasks = []
        n_errors = 0
        threads = []
        try:
            # run while there is still threads, tasks or stuff in the queue
            # to process
            while threads or tasklist or task_queue.qsize():
                # if we aren't using all the processors AND there is still data left to
                # compute, then spawn another thread
                if (len(threads) < self.num_processes) and tasklist:
                    if use_threading:
                        t = Thread(target=_worker, 
                                   args=tuple([tasklist.pop(0),task_queue]))
                        t.daemon = True
                        t.start()
                        threads.append(t)
                    else:
                        _worker(tasklist.pop(0),task_queue)
                else:
        		# in the case that we have the maximum number of running threads
                 # or we run out tasks. Check if any of them are done. 
                    for thread in threads:
                        if not thread.isAlive():
                            threads.remove(thread)
                while task_queue.qsize():
                    task = task_queue.get() 
                    if task.error:
                        n_errors += 1
                    elif not self.keep_logfiles:
                        if os.path.isfile(task.logfile):
                            try:
                                os.unlink(task.logfile)
                                task.logfile = ""
                            except:
                                print('Could not remove logfile: ' + task.logfile )
                    processed_tasks.append(task)
                    if self.disp:
                        pbar.animate( len(processed_tasks),  n_errors)
                time.sleep(0.05)
        except KeyboardInterrupt:
            #if len(processed_tasks) < number_tasks:
            print('\nUser interupted')
            _kill_running_processes()    
        
        totaltime = int(time.clock()-starttime)
        
        return totaltime
    
    
def _summery(task,duration=None):

    entry = ''
    if task.processtime == 0:
        entry += 'Not completed '
    elif task.error:
        entry += 'Failed '
    else:
        entry += 'Completed '
        
    entry += '{2!s}sec :{0} n={1!s} : '.format(task.name,
                                                task.number,
                                                task.processtime)            
    if not task.logfile:
        if _run_from_ipython():
            print_template = ( '(<a href= "file:///{0}" target="_blank">{1}</a>'
                               '<a href= "file:///{2}" target="_blank">dir</a>)' )
            entry += print_template.format(task.logfile,
                                           os.path.basename(task.logfile),
                                           os.path.dirname(task.logfile) )
        else:                        
            entry += '( {0} )'.format(os.path.basename(task.logfile))
    
    return entry

def _parse_anybodycon_output(strvar):
    out = collections.OrderedDict();
    dump_path = None
    for line in strvar.splitlines():
        if '#### Macro command' in line and "Dump" in line:
            me = re.search('Main[^ \"]*', line)
            if me is not None :
                dump_path = me.group(0)
        if line.endswith(';') and line.count('=') == 1:
            (first, last) = line.split('=')
            first = first.strip()
            last = last.strip(' ;').replace('{','[').replace('}',']')
            if dump_path is not None:
                first = dump_path
                dump_path = None
            try:
                out[first.strip()] = np.array(literal_eval(last))
            except SyntaxError:
                pass

        if ( line.startswith('ERROR') or
             line.startswith('Error') or 
             line.startswith('Model loading skipped')) : 
            if 'ERROR' not in out:
                out['ERROR'] = []
            out['ERROR'].append(line)
    return out
        


class ProgressBar:
    def __init__(self, iterations):
        self.iterations = iterations
        self.prog_bar = '[]'
        self.fill_char = '*'
        self.width = 40
        #self.__update_amount(0)

    def animate(self, iter, failed = 0):
        self.update_iteration(iter,failed)
        if _run_from_ipython():
            clear_output(wait=True)
            #clear_output()
        print('\r', self, end="")
        sys.stdout.flush()

    def update_iteration(self, elapsed_iter,number_failed, tasks=[]):
        self.__update_amount((elapsed_iter / float(self.iterations)) * 100.0)
        self.prog_bar += '  %d of %s complete' % (elapsed_iter, self.iterations)
        if number_failed == 1:
            self.prog_bar += ' ({0} Error)'.format(number_failed)
        elif number_failed > 1:
            self.prog_bar += ' ({0} Errors)'.format(number_failed)
            
            
    def __update_amount(self, new_amount):
        percent_done = int(round((new_amount / 100.0) * 100.0))
        all_full = self.width - 2
        num_hashes = int(round((percent_done / 100.0) * all_full))
        self.prog_bar = '[' + self.fill_char * num_hashes + ' ' * (all_full - num_hashes) + ']'
        pct_place = int(len(self.prog_bar) / 2) - len(str(percent_done))
        pct_string = '%d%%' % percent_done
        self.prog_bar = self.prog_bar[0:pct_place] + \
            (pct_string + self.prog_bar[pct_place + len(pct_string):])

    def __str__(self):
        return str(self.prog_bar)




if __name__ == '__main__':
    pass
        