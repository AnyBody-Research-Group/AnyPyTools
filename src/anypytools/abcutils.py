# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 21:14:59 2012

@author: Morten
"""
from __future__ import division, absolute_import, print_function, unicode_literals
try:
    from .utils.py3k import * # @UnusedWildImport
except (ValueError, SystemError):
    from utils.py3k import * # @UnusedWildImport




import os
from subprocess import Popen
import numpy as np
from tempfile import NamedTemporaryFile, TemporaryFile
from threading import Thread
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
            print('Kill AnyBodyCon Process. PID: ', pid, ' : Done')
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
 


def create_define_load_string(defines):
    """ Creates a string for setting defines statements in AnyBody Macros.    
    
    Args: 
        defines: dictionary with {define_variable: Define value/string}
    Returns: 
        formatted string for setting the define statements in a macro 
        load command    
    """
    if not isinstance(defines, dict):
        raise TypeError 
    cmd_list = []        
    for key,value in defines.iteritems():   
        if isinstance(value,string_types):
            cmd_list.append('-def %s=---"\\"%s\\""'% (key, value) )
        else:
            cmd_list.append('-def %s="%d"'% (key, value) )
    return ' '.join(cmd_list)

def create_path_load_string(paths):
    """ Creates a string for setting path statements in AnyBody Macros.    
    
    Args: 
        defines: dictionary with path staments {path_variable: directory_path}
    Returns: 
        formatted string for setting the path statements in a macro 
        load command    
    """    
    if not isinstance(paths, dict):
        raise TypeError 
    cmd_list = []        
    for key,value in paths.iteritems():   
        cmd_list.append('-p %s=---"%s"'% (key, value.replace('\\','\\\\')) )
    return ' '.join(cmd_list)

    

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
        outputs: list of anybody variables to collect from the console output
        number: id number of the task
        keep_logfiles: true if log files should not be deleted
        name: name of the task, which is used for printing status informations
    """
    def __init__(self,folder=None, macro = [], 
                 taskname = None, outputs = [], number = 1,
                 keep_logfiles = False):
        """ Init the Task class with the class attributes
        """
        self.folder = folder
        if folder is None:
            self.folder = os.getcwd()
        self.macro = macro
        self.outputs = outputs
        self.number = number
        self.keep_logfiles = keep_logfiles
        self.name = taskname
        if taskname is None:
            head, folder = os.path.split(folder)
            parentfolder = os.path.basename(head)
            self.name = parentfolder+'/'+folder

            
    
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
    disp:
        Set to False to suppress output
    verbose:
        Set to True to enable more display masseges
        
    Returns
    -------
    AnyPyProcess object: 
        a AnyPyProcess object for running batch processing, parameter
        studies and pertubation jobs.       
    """    
    def __init__(self, num_processes = get_ncpu(), 
                 anybodycon_path = get_anybodycon_path(), stop_on_error = True,
                 timeout = 3600, disp = True, verbose = False, ignore_errors = [],
                 keep_logfiles = False):
        self.anybodycon_path = anybodycon_path
        self.stop_on_error = stop_on_error
        self.num_processes = num_processes
        self.counter = 0
        self.disp = disp
        self.verbose = verbose
        self.timeout = timeout
        self.ignore_errors = ignore_errors
        self.keep_logfiles = keep_logfiles
    

    def start_pertubation_job(self, loadmacro, mainmacro, inputs, outputs,
                            perturb_factor = 10e-5):
        """ Starts a pertubation batch job and return a list petubated ouputs.
        
        Runs an AnyBody model while pertubing the inputs to find the 
        sensitivity of the given outputs. This is usefull to calculate 
        the gradient when wrapping AnyBody models in an optimization loop.

        Parameters
        ----------
        loadmacro : list of strings
                list of macro commands that load the anybody 
                model. I.e. 'load "MyModel.main.any'
        mainmacro : list of strings 
                list with macro commands that execute the anybody model.
        inputs :  List of tuples   
                List of tuples specifying the anybody input variables and
                their values. For example:
                ``[('Main.study.param1',1.4), ('Main.study.param2',3.1)]``
        outputs : list of strings
                List of anybody variables to observe the output.
                For example: ``['Main.study.output.MaxMuscleActivty']``
        pertub_factorn : float, optional
                The value used to perturb the input variables. 
                
        Returns
        -------
        (objective, pertubations) :
            objective : dictionary
                dictionary object with an entry for each output variable.
                The dictionary holds the value of the output variable after
                evalutation at the input variables. 
            pertubations: dictionary
                dictionary object with an entry for each output
                variable. Each enrty holds a list with the same length as 
                'inputs', with the model's responce to the pertubed inputs. 
                
        Examples
        --------
        >>> import anypytools
        >>> app = anypytools.abcutils.AnyPyProcess()        
        >>> loadmcr = ['load "mymodel.main.any"']
        >>> mainmcr = ['operation Main.study.Inversedynamics', 'run']
        >>> input = [('Main.study.param1',1.4), ('Main.study.param2',3.1)]
        >>> out = ['Main.study.output.MaxMuscleActivty']
        >>> (objval, pert) = app.start_pertubation_job(loadmcr,mainmcr,input,out)
        >>> objective = objval[ out[0] ]
        >>> pertubation = pert[ out[0] ]
        """
        from collections import OrderedDict        
        if isinstance(inputs, dict):
            raise TypeError('inputs argument must be a list of tuples')
        
        inputs = OrderedDict(inputs)        
        # inputs must be an ordered dictionary in order to interpret the 
        for k,v in inputs.iteritems():
            if isinstance(v,list):
                if len(v) != 1:
                    raise TypeError('inputs argument have the incorrect type')
            else:
                inputs[k]=[inputs[k]]
        for index in range(len(inputs)):
            for i,key in enumerate(inputs.keys() ):
                unpert_value = inputs[key][0]
                if i ==index:
                    inputs[key].append(unpert_value*(1+perturb_factor))
                else:
                    inputs[key].append(unpert_value)
        
        result =  self.start_param_job(loadmacro, mainmacro, inputs, outputs)
        objective = dict()
        pertubations = dict()
        # All the first elements correspond to objective functions                                  
        for key in result.keys():
            objective[key] = result[key][0]
            pertubations[key] = result[key][1:]
        
        return (objective, pertubations)
        
        
    def start_param_job(self, loadmacro, mainmacro, inputs = {}, outputs = [],
                        folder = None):
        """ start_param_job(loadmacro, mainmacro, inputs = {}, ouputs = {})
        
        Starts a parameter job. Runs an AnyBody model multiple times with a 
        number of different input parameters.
        
        Parameters
        ----------
        loadmacro: list of strings
            list of macro commands that load the anybodymodel. 
            I.e. ``load "MyModel.main.any"``
        mainmacro: list of strings
            string or list with macro commands that execute the  anybody model.
            For example: ``['operation Main.study.Inversedynamics', 'run']``
        inputs: list of tuples
            List of tuples specifying the anybody input variables and
            a list of values to evalutate. For example: the following will
            run the model three times each time setting the two parameters.
            
            >>>inputs = [ ('Main.study.param1',[1.4,1.6,1.8]), ('Main.study.param2',[3.1,3.5,3.9])  ]


        outputs: List of anybody variables to observe the output.
                 For example: ``['Main.study.output.MaxMuscleActivty']``
        
        Returns
        -------
        result :           
            dictionary object with an entry for each output variable. The
            dictionary holds lists with output variables for each time the model
            is run
        """        
        
        if isinstance(loadmacro, string_types):
            loadmacro = loadmacro.splitlines()
        if isinstance(mainmacro, string_types):
            mainmacro = mainmacro.splitlines()
        
        if not isinstance(inputs,dict):
            inputs= dict(inputs)
               
        # Check format of inputs
        ntask = None
        if len(inputs) > 0:
            for key, value in inputs.iteritems():
                if isinstance(value, list ):
                    pass
                else:
                    value = [value]
                    inputs[key] = value
                if ntask is None: ntask = len(value)
                if ntask != len(value):
                    raise ValueError('All inputs must have the same length')
        else:
            ntask = 1
        self.results = dict()
        tasklist = []
        outputmacro = []
        if len(outputs):
            for varname in outputs:
                outputmacro.append('classoperation %s "Dump All" ' % varname)        
        for itask in range(ntask):
            inputmacro = []
            if len(inputs):
                for varname, value in inputs.iteritems():
                    valuestr = _list2anyscript(value[itask])
                    inputmacro.append('classoperation %s "Set Value" --value="%s"' %(varname,valuestr) )
#                inputmacro.append('classoperation Main "Update Values"')
            newtask = _Task(folder, macro = loadmacro+inputmacro+mainmacro+outputmacro+['exit'],  
                           taskname = str(itask), outputs = outputs,
                           number = itask, keep_logfiles = self.keep_logfiles )
            tasklist.append(newtask)             
            
        try:
            self._schedule_processes(tasklist, self._worker)
        except KeyboardInterrupt:
            print('User interuption: Kiling running processes')
            _kill_running_processes()
            raise KeyboardInterrupt
        
        # Collect results        
        returnvar = dict()
        if len(self.results):
            for outvar in outputs:
                if not returnvar.has_key(outvar): returnvar[outvar] = []
                for itask in range(ntask):
                    if self.results.has_key(itask):
                        vararray = np.array(self.results[itask][outvar] )
                        returnvar[outvar].append(vararray)
                    else:
                        returnvar[outvar].append(None)
        return returnvar

    
    
    def start_macro(self, macrolist, folderlist = None, search_subdirs = None,
                    number_of_macros = None):
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

        if folderlist is None:
            folderlist = [os.getcwd()]
            

        if not isinstance(folderlist,list):
            raise TypeError('folderlist must be a list of folders')
            
        if isinstance(macrolist, types.GeneratorType) and number_of_macros is None:
            raise ValueError('number_of_macros must be specified if\
                              macrolist is a generator' )            
            
        #create a list of tasks
        tasklist = []
        self.results = dict()
        
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
            
        number_of_tasks = number_of_macros * len(folderlist)
        
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
                                    number = taskid,
                                    keep_logfiles=self.keep_logfiles)
                    taskid += 1

        tasklist = list(generate_tasks(macrolist, folderlist) )
        
        
        # Start batch processing
        try:
            (completed,failed, duration) = self._schedule_processes(tasklist,
                                                                self._worker)
            self._print_summery(completed,failed,duration)
        except KeyboardInterrupt:
            print('User interuption: Kiling running processes')
        _kill_running_processes()    
        
        
        output = []
        for i in range(len(self.results)):
            if i in self.results:
                output.append(self.results[i])
        
        return output
    
    def _print_summery(self, completed_tasks, failed_tasks,duration):
        if self.disp is False:
            return
        
        if self.verbose is True:
            tasklist = completed_tasks + failed_tasks
        else:
            tasklist = failed_tasks
        print('')
        for entry in _summery(tasklist,duration ):
            if  _run_from_ipython():
                display(HTML(entry))
            else:
                print(entry)



        
    def _worker (self, task, task_queue):
        """ Executes AnyBody console application on the task object
        """
#        task = task[0]        
        process_number = self.counter 
        self.counter += 1
        
        if not os.path.exists(task.folder):
            raise IOError('Unable to find folder: ' + task.folder)
        
        macrofile = NamedTemporaryFile(mode='w+b',
                                         prefix ='macro_',
                                         suffix='.anymcr',
                                         dir = task.folder,
                                         delete = False)
        macrofile.write( '\n'.join(task.macro).encode('UTF-8') )
        macrofile.flush()
            
        anybodycmd = [os.path.realpath(self.anybodycon_path), '--macro=', macrofile.name, '/ni', ' '] 
        
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
        
        processtime = int(time.clock()-starttime)
        
        tmplogfile.seek(0)
        rawoutput = "\n".join( s.decode('UTF-8') for s in tmplogfile.readlines() )
        tmplogfile.close()
        macrofile.close()
                
        output = _parse_anybodycon_output(rawoutput)
        
        # Remove any ERRORs which should be ignored
        if 'ERROR' in output:
            def check_error(error_string):
                return all( [(err not in error_string) for err in self.ignore_errors])
            output['ERROR'][:] = [_ for _ in output['ERROR'] if check_error(_)]

            if len( output['ERROR'] ) == 0:
                del output['ERROR']
        
        
        if task.keep_logfiles or 'ERROR' in output:
            with NamedTemporaryFile(mode='w+b', prefix ='output_',
                                    suffix='.log',  dir = task.folder,
                                    delete = False) as logfile:
                logfile.write(rawoutput.encode('UTF-8'))
                logfile_path = logfile.name
        else:
            logfile_path = None
        
        task.processtime = processtime
        task.log = logfile_path
        task.error = 'ERROR' in output
        task.process_number =process_number
        
        
        try:
            os.remove(macrofile.name) 
        except:
            print( 'Error removing macro file')

        if not hasattr(self, 'results'):
            self.results = dict()        
#        for outvar in task.outputs:
#            if output.has_key(outvar):
        if task.number not in self.results:
            self.results[task.number] = dict()
        self.results[task.number] = output  
        task_queue.put(task)


            
    
       

    def _schedule_processes(self, tasklist, _worker):
        if len(tasklist) == 0:
            return ([],[], 0)
        starttime = time.clock()    
        task_queue = queue.Queue()
        totaltasks = len(tasklist)
        pbar = ProgressBar(totaltasks)
        if self.disp:
            pbar = ProgressBar(totaltasks)
            pbar.animate(0)
        threads = []
        completed_tasks = []
        failed_tasks = []
        
        
        # #lse start the tasks in threads
    
        
        # run until all the threads are done, and there is no data left
        while threads or tasklist or task_queue.qsize():
            # if we aren't using all the processors AND there is still data left to
            # compute, then spawn another thread
            if (len(threads) < self.num_processes) and tasklist:
                if self.num_processes > 1 and totaltasks > 1:
                    t = Thread(target=_worker, args=tuple([tasklist.pop(0),task_queue]))
                    t.daemon = True
                    t.start()
                    threads.append(t)
                else:
                    _worker(tasklist.pop(0),task_queue)
    		# in the case that we have the maximum number of threads check if any of them
    		# are done. (also do this when we run out of data, until all the threads are done)
            else:
                for thread in threads:
                    if not thread.isAlive():
                        threads.remove(thread)
            while task_queue.qsize() > 0:
                task = task_queue.get() 
                if task.error:
                    failed_tasks.append( task )
                else:
                    completed_tasks.append(task )
                if self.disp:
                    pbar.animate(len(completed_tasks)+len(failed_tasks), 
                             len(failed_tasks))
            time.sleep(0.5)
                
        totaltime = int(time.clock()-starttime)
        return (completed_tasks, failed_tasks, totaltime)
    
    
def _summery(tasks,duration=None):

    summery = []
    for task in tasks:
        entry = ''
        if task.error:
            entry += 'Failed '
        else:
            entry += 'Completed '
            
        entry += '{2!s}sec :{0} n={1!s} : '.format(task.name,
                                                    task.number,
                                                    task.processtime)            
        if task.log is not None:
            if _run_from_ipython():
                entry += '(<a href= "{0}">{1}</a> \
                                    <a href= "{2}">dir</a>)\
                                   '.format(task.log,
                                        os.path.basename(task.log),
                                        os.path.dirname(task.log) )
            else:                        
                entry += '( {0} )'.format(os.path.basename(task.log))
        summery.append(entry)
    
    if duration is not None:
        summery.append('Total time: {0} seconds'.format(duration))
    
    return summery

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
        
def _list2anyscript(arr):
    def createsubarr(arr):
        outstr = ""
        if isinstance(arr, np.ndarray):
            if len(arr) == 1:
                return str(arr[0])
            outstr += '{'
            for row in arr:
                outstr += createsubarr(row)
            outstr = outstr[0:-1] + '},'
            return outstr
        else:
            return outstr + str(arr)+','      
    if isinstance(arr, np.ndarray) :
        return createsubarr(arr)[0:-1]
    else:
        return str(arr)


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


def test():
#    ap =AnyProcess('test.any')
#    design1= DesignVar('Main.TestVar1', 1)
#    design2 = DesignVar('Main.TestVar2', np.random.rand(1,3))
#
#    
#    out =  ap.start(inputs = [design1,design2],
#                   macrocmds= ['operation MyStudy.Kinematics',\
#                               'run'],
#                   outputs = [ 'Main.MyStudy.Output.Abscissa.t',\
#                               'Main.MyStudy.nStep']
#                  )    

    # test batch processor
    from anypytools import abcutils 
    from numpy import array, random
    import os.path as op
    
#    print 'Test batch job'
#    basepath = op.join( op.dirname(abcutils.__file__), 'test_models')
#    app = AnyPyProcess(basepath, num_processes = 1)
#    mcr = ['load "Demo.Arm2D.any"',
#           'operation ArmModelStudy.InverseDynamics',
#           'run',
#           'exit']
#    app.start_batch_job(mcr)
    
    print('Test param job')
    basepath = op.join( op.dirname(abcutils.__file__), 'test_models')
    app = AnyPyProcess(num_processes = 10, keep_logfiles = False)
    loadmcr = ['load "Demo.Arm2D.any"']
    mainmcr = ['operation ArmModelStudy.InverseDynamics',
              'run']
#    invars= {'Main.ArmModel.Loads.HandLoad.F': [array([0,0,-40]),array([10,0,-40])],
#              'Main.ArmModel.Segs.LowerArm.Brachialis.sRel': [array([-0.1, 0, 0 ]),array([-0.09, 0, 0 ]) ] }
    invars = {'Main.ArmModel.Segs.LowerArm.Brachialis.sRel':
                  list( array([-0.1,0,0]) +  0.03* random.randn(100,1)) }
    outvars = [ 'Main.ArmModelStudy.Output.Model.Muscles.Brachialis.Activity']
    res = app.start_param_job(loadmcr, mainmcr, invars, outvars, folder=basepath)   
    print("")
    
    try:
        import matplotlib.pyplot as plt 
        plt.plot(res.values()[0][3],'r--', linewidth=6)
    
        for data in res.values()[0]:
            plt.plot(data)
        #plt.axis([0,100 , 0, 1])
        plt.show()
    except ImportError:
        pass




if __name__ == '__main__':
#    for data,header,filename in csv_trial_data('C:\Users\mel\SMIModelOutput', DEBUG= True):
#        print header
    test()    
#    outvars = ['/Output/Validation/EMG'] 
        