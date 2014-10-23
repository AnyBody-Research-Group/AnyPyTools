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
from subprocess import Popen
import numpy as np
from tempfile import NamedTemporaryFile, TemporaryFile
from threading import Thread
from functools import wraps
import time 
import signal
import re
import atexit
try:
    import Queue as queue
except ImportError:
    import queue
import sys
import types

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

class _Task():
    """Class for storing processing jobs

    Attributes:
        folder: directory in which the macro is executed
        macro: list of macro commands to executre
        number: id number of the task
        name: name of the task, which is used for printing status informations
    """
    def __init__(self,folder=None, macro = [], 
                 taskname = None, number = 1):
        """ Init the Task class with the class attributes
        """
        self.folder = folder
        if folder is None:
            self.folder = os.getcwd()
        self.macro = macro
        self.output = None
        self.number = number
        self.logfile = None
        self.processtime = 0
        self.name = taskname
        self.error = False
        if taskname is None:
            head, folder = os.path.split(folder)
            parentfolder = os.path.basename(head)
            self.name = parentfolder+'/'+folder + str(number)
    
                             
    def get_output(self, task_info = False):
        out = self.output
        if task_info is True:
            out['task_info']  = dict(logfile = self.logfile,
                                processtime = self.processtime,
                                taskname = self.name,
                                macro = self.macro,
                                index = self.number,
                                workdir = self.folder)
        return out
            
    
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
                 keep_logfiles = False, logfile_prefix = '', cache_dir = None):
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
        self.cache_dir = None

    
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

    
    
    
    #@cache_results(1,2,3)
    def start_macro(self, macrolist, folderlist = None, search_subdirs = None,
                    number_of_macros = None, cache_mode = 'r',**kwargs ):
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
        cache_mode: 
            Determines the mode when cache_results
                        
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

        if folderlist is None:
            folderlist = [os.getcwd()]
            

        if not isinstance(folderlist,list):
            raise TypeError('folderlist must be a list of folders')
            
        if isinstance(macrolist, types.GeneratorType) and number_of_macros is None:
            raise ValueError('number_of_macros must be specified if\
                              macrolist is a generator' )            
            
        #create a list of tasks
        tasklist = []
        
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
            number_of_macros = len(macrolist)
                    
        def generate_tasks(macros, folders):
            taskid = 0
            for i_macro, macro in enumerate(macros):
                for folder in folders:
                    if isinstance(folder ,tuple) and len(folder) ==2:
                        folder, taskname = folder
                        if number_of_macros > 1:
                            taskname = taskname + ' macro '+str(i_macro) 
                    else:
                        taskname = None
                    yield _Task(folder, macro, taskname = taskname,
                                    number = taskid)
                    taskid += 1


        tasklist = list(generate_tasks(macrolist, folderlist) )
        assert len(tasklist) == number_of_macros * len(folderlist)
        
        process_time = self._schedule_processes(tasklist, self._worker)
        
        self._print_summery(tasklist,process_time)
        
                
        return [task.get_output(task_info = self.return_task_info ) for task in tasklist]
        
        
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
        for task in unfinished_tasks:
            _display( _summery(task) ) 

        if duration is not None:
            print( 'Total time: {:d} seconds'.format(duration))


    def _worker (self, task, task_queue):
        """ Executes AnyBody console application on the task object
        """
#        task = task[0]        
        process_number = self.counter 
        self.counter += 1
        
        if not os.path.exists(task.folder):
            raise IOError('Unable to find folder: ' + task.folder)
        
        macrofile = NamedTemporaryFile(mode='w+b',
                                         prefix ='{}'.format(self.logfile_prefix+'_'),
                                         suffix='.anymcr',
                                         dir = task.folder,
                                         delete = False)
        macrofile.write( '\n'.join(task.macro).encode('UTF-8') )
        macrofile.flush()
            
        anybodycmd = [os.path.realpath(self.anybodycon_path), '--macro=', macrofile.name, '/ni'] 
        
        tmplogfile = TemporaryFile()            
        proc = Popen(anybodycmd, stdout=tmplogfile,
                                stderr=tmplogfile,shell= False)                      
        _pids.add(proc.pid)
        starttime = time.clock()
        timeout =starttime + self.timeout
        while proc.poll() is None:
            if time.clock() > timeout:
                proc.terminate()
                proc.communicate()
                tmplogfile.seek(0,2)
                tmplogfile.write('ERROR: Timeout. Terminate by batch processor'.encode('UTF-8') )
                break
            time.sleep(0.3)
        else:
            if proc.pid in _pids:
                _pids.remove(proc.pid)
        
        processtime = round(time.clock()-starttime, 2)
        
        tmplogfile.seek(0)
        rawoutput = "\n".join( s.decode('UTF-8') for s in tmplogfile.readlines() )
        tmplogfile.close()
        macrofile.close()
                
                
        output = _parse_anybodycon_output(rawoutput)

        # Remove any ERRORs which should be ignored
        if 'ERROR' in output:
            def check_error(error_string):
                return all( [(err not in error_string) for err in self.ignore_errors])
            output['ERROR'][:] = [err for err in output['ERROR'] if check_error(err)]

            if not output['ERROR']:
                del output['ERROR']
        
        logfile_path = None
        if self.keep_logfiles or 'ERROR' in output:
            with open(os.path.splitext(macrofile.name)[0]+'.log','w+b') as logfile:
                logfile.write(rawoutput.encode('UTF-8'))
                logfile_path = logfile.name
        else:
            try:
                os.remove(macrofile.name) 
            except:
                print( 'Error removing macro file')
        
        task.processtime = processtime
        task.logfile = logfile_path
        task.error = 'ERROR' in output
        task.process_number = process_number
        


        task.output = output
        task_queue.put(task)


            
    
       

    def _schedule_processes(self, tasklist, _worker):
        # Make a shallow copy of the task list, so we don't mess with the callers
        # list. 
        number_tasks = len(tasklist)
        tasklist = copy.copy(tasklist)
        if len(tasklist) == 0:
            return 0
            
        if number_tasks > 1 and self.num_processes > 1:
            use_threading = True
        else: 
            use_threading = False
            
        starttime = time.clock()    
        task_queue = queue.Queue()
        if self.disp:
            pbar = ProgressBar(number_tasks)
            pbar.animate(0)
        
        processed_tasks = []
        no_erros = 0
        threads = []

        
        try:
            # run until all the threads are done, and there is no data left in
            # the queue
            while threads or tasklist or task_queue.qsize():
                # if we aren't using all the processors AND there is still data left to
                # compute, then spawn another thread
                if (len(threads) < self.num_processes) and tasklist:
                    if use_threading == True:
                        t = Thread(target=_worker, 
                                   args=tuple([tasklist.pop(0),task_queue]))
                        t.daemon = True
                        t.start()
                        threads.append(t)
                    else:
                        _worker(tasklist.pop(0),task_queue)
        		# in the case that we have the maximum number of running threads
                 # or we run out tasks. Check if any of them are done. 
                else:
                    for thread in threads:
                        if not thread.isAlive():
                            threads.remove(thread)
                while task_queue.qsize() > 0:
                    task = task_queue.get() 
                    processed_tasks.append(task)
                    if task.error:
                        no_erros += 1
                    if self.disp:
                        pbar.animate( len(processed_tasks),  no_erros)
                time.sleep(0.2)
        except KeyboardInterrupt:
            if len(processed_tasks) < number_tasks:
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
    if task.logfile is not None:
        if _run_from_ipython():
            entry += '(<a href= "{0}" target="_blank">{1}</a> \
                                <a href= "{2}" target="_blank">dir</a>)\
                               '.format(task.logfile,
                                    os.path.basename(task.logfile),
                                    os.path.dirname(task.logfile) )
        else:                        
            entry += '( {0} )'.format(os.path.basename(task.logfile))
    
    return entry

def _parse_anybodycon_output(strvar):
    out = {};
    dump_path = None
    for line in strvar.splitlines():
        if line.count('#### Macro command') and line.count('"Dump"'):
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
            out[first.strip()] = np.array(eval(last))
        if line.startswith('ERROR') or line.startswith('Error'): 
            if line.endswith('Path does not exist.'):
                continue # hack to avoid detecting #path error this error which is always present
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
        