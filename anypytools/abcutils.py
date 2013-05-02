# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 21:14:59 2012

@author: Morten
"""

import os
from subprocess import Popen
#import threading
#import time
import numpy as np
#import multiprocessing
from tempfile import NamedTemporaryFile, TemporaryFile
from threading import Thread, Lock
import time 
import signal
import re
import atexit
import Queue
import sys

try:
    from IPython.core.display import clear_output
    have_ipython = True
except ImportError:
    have_ipython = False
    
    

print_lock = Lock()

_pids = set()
def _kill_running_processes():
    """ Clean up and shut down any running processes
    """
    # Kill any rouge processes that are still running.
    for pid in _pids:
        try:
            os.kill(pid, signal.SIGTERM)
            print 'Kill AnyBodyCon Process. PID: ', pid, ' : Done'
        except:
            pass
    _pids.clear()
atexit.register(_kill_running_processes)


def get_anybodycon_path():
    """  Return the path to default AnyBody console application 
    """
    import _winreg
    abpath = _winreg.QueryValue(_winreg.HKEY_CLASSES_ROOT,
                    'AnyBody.AnyScript\shell\open\command').rsplit(' ',1)[0]
    return os.path.join(os.path.dirname(abpath),'AnyBodyCon.exe')

def get_ncpu():
    """ Return the number of CPUs in the computer 
    """
    from multiprocessing import cpu_count
    return cpu_count()

def run_from_ipython():
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
        if isinstance(value,basestring):
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

    

def _getsubdirs(toppath, search_string = "."):
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
    def __init__(self,folder=os.getcwd(), macro = [], 
                 taskname = None, outputs = [], number = 1,
                 keep_logfiles = False):
        """ Init the Task class with the class attributes
        """
        self.folder = folder
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
    AnyPyProcess(basepath = cwd, subdir_search = None, num_processes = nCPU,\
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
    basepath:
        directory to execute anybody console application
    subdir_search:
        regular expression string to search for sub
        directories. This is used find multiple folder for batch processing. 
        ``Setting subdir_search = '.'`` will include all subfolders.
    num_processes:
        number of anybody models to start in parallel.
        This defaults to the number of CPU in the computer. 
    anybodycon_path:
        Overwrite the default anybodycon.exe file to 
        use in batch processing
    timeout:
        maximum time a model can run until it is terminated. 
        Defaults to 1 hour
    disp:
        set to False to disable status messages.
        
    Returns
    -------
    AnyPyProcess object: 
        a AnyPyProcess object for running batch processing, parameter
        studies and pertubation jobs.       
    """    
    def __init__(self, basepath = os.getcwd(), subdir_search = None,
                 num_processes = get_ncpu(), 
                 anybodycon_path = get_anybodycon_path(), stop_on_error = True,
                 timeout = 3600, disp = True, keep_logfiles = False):
        self.basepath = os.path.abspath(basepath)
        self.anybodycon_path = anybodycon_path
        self.stop_on_error = stop_on_error
        self.num_processes = num_processes
        self.counter = 0
        self.disp = disp
        self.timeout = timeout
        self.keep_logfiles = keep_logfiles
        self.batch_folder_list = _getsubdirs(self.basepath,subdir_search)
    

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
        >>> app = anypytools.abcutils.AnyPyProcess()        
        >>> loadmcr = ['load "mymodel.main.any"]
        >>> mainmcr = ['operation Main.study.Inversedynamics', 'run']
        >>> in = [('Main.study.param1',1.4), ('Main.study.param2',3.1)]
        >>> out = ['Main.study.output.MaxMuscleActivty']
        >>> (obj, pert) = app.start_pertubation_job(loadmcr,mainmcr,in,out)
        >>> objective = obj[ out[0] ]
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
        
        
    def start_param_job(self, loadmacro, mainmacro, inputs = {}, outputs = []):
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
            
            >>>inputs = [ ('Main.study.param1',[1.4,1.6,1.8]),
                          ('Main.study.param2',[3.1,3.5,3.9])  ]
        
        outputs: List of anybody variables to observe the output.
                 For example: ``['Main.study.output.MaxMuscleActivty']``
        
        Returns
        -------
        result :           
            dictionary object with an entry for each output variable. The
            dictionary holds lists with output variables for each time the model
            is run
        """        
        
        if isinstance(loadmacro, basestring):
            loadmacro = loadmacro.splitlines()
        if isinstance(mainmacro, basestring):
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
            newtask = _Task(folder = self.batch_folder_list[0], 
                           macro = loadmacro+inputmacro+mainmacro+outputmacro+['exit'],  
                           taskname = str(itask), outputs = outputs,
                           number = itask, keep_logfiles = self.keep_logfiles )
            tasklist.append(newtask)             
            
        try:
            _schedule_processes(tasklist, self._worker, self.num_processes)
        except KeyboardInterrupt:
            print 'User interuption: Kiling running processes'
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

    
    
    def start_macro(self, macrolist, folder = None):
        """ 
        app.start_marco(macro)        
        
        Starts a batch processing job. Runs an anybody macro base_path of the 
        parent class. 
        
        Parameters
        ----------
        macrolist: list of macros
            list containing lists of macro commands that loads and run models
        folder:
            
            For example:
            >>> macro=[ ['load "model1.any"', 'operation Main.RunApplication', 'run', 'exit'],
                        ['load "model2.any"', 'operation Main.RunApplication', 'run', 'exit'],
                        ['load "model3.any"', 'operation Main.RunApplication', 'run', 'exit'] ]
        """        

        if folder is None:
            folder = self.batch_folder_list[0]

        #create a list of tasks
        tasklist = []
        self.results = dict()
        
        if isinstance(macrolist[0], basestring):
            macrolist = [macrolist]
        
        for i, macro in enumerate(macrolist):
            newtask = _Task(folder, macro, taskname = '', number = i,
                            keep_logfiles=self.keep_logfiles)
            tasklist.append(newtask)
        if self.disp:
            print 'Starting', len(tasklist), 'instances.'
        # Start batch processing
        try:
            _schedule_processes(tasklist, self._worker, self.num_processes)
        except KeyboardInterrupt:
            print 'User interuption: Kiling running processes'
        _kill_running_processes()    
        
        output = []
        for i in range(len(self.results)):
            if self.results.has_key(i):
                output.append(self.results[i])
        
        return output
    
    
    def start_batch_job(self, macro, special_dir = None):
        """ 
        app.start_batch_job(macro, special_dir = None)        
        
        Starts a batch processing job. Runs an anybody macro on the 
        batch_folder_list in the parent class. 
        
        Parameters
        ----------
        macro: string or list
            string or list of macro commands that loads and run the model
            
            For example:
            >>> macro = ['load "mymodel.main.any"',
                         'operation Main.study.Inversedynamics',
                         'run'
                         'exit']
            
        special_dir: directory
            overide the batch_folder_list of the parent class, and 
            run the macro on a specific folder. 
        """        
        if special_dir is None:
            folderlist = self.batch_folder_list
        elif os.path.isdir(special_dir):
            folderlist = [special_dir]
        else:
            raise TypeError('Special_dir must be a directory' ) 
                            
        self.kill_all = False
        # Convert macro to a list 
        if isinstance(macro, basestring):
            macro = [macro.splitlines()]
        #create a list of tasks
        tasklist = []
        for folder in folderlist:
            newtask = _Task(folder,macro, keep_logfiles=self.keep_logfiles)
            tasklist.append(newtask)
        if self.disp:
            print 'Starting', len(tasklist), 'instances.'
        # Start batch processing
        try:
            _schedule_processes(tasklist, self._worker, self.num_processes)
        except KeyboardInterrupt:
            print 'User interuption: Kiling running processes'
        _kill_running_processes()
        
    def _worker (self, task, queue=None):
        """ Executes AnyBody console application on the task object
        """
#        task = task[0]        
        process_number = self.counter 
        self.counter += 1
        
        macrofile = NamedTemporaryFile(mode='w+b',
                                         prefix ='macro_',
                                         suffix='.anymcr',
                                         dir = task.folder,
                                         delete = False)
        macrofile.write('\n'.join(task.macro))
        macrofile.flush()
            
        anybodycmd = self._create_anybodycon_cmd(macrofile.name,task)
        tmplogfile = TemporaryFile(mode='w+b',
                                         prefix ='output_',
                                         suffix='.log',
                                         dir = task.folder)            
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
                tmplogfile.write('ERROR: Timeout. Terminate by batch processor')
                break
            time.sleep(0.3)
        else:
            if proc.pid in _pids:
                _pids.remove(proc.pid)
        
        processtime = int(time.clock()-starttime)
        
        tmplogfile.seek(0)
        rawoutput = "\n".join(tmplogfile.readlines())
        tmplogfile.close()
        macrofile.close()
                
        output = _parse_anybodycon_output(rawoutput)
        
        if task.keep_logfiles or output.has_key('ERROR'):
            with NamedTemporaryFile(mode='w+b', prefix ='output_',
                                         suffix='.log',  dir = task.folder,
                                         delete = False) as logfile:
                logfile.write(rawoutput)
                logfile_path = logfile.name
        else:
            logfile_path = None
        
        task.processtime = processtime
        task.log = logfile_path
        task.error = output.has_key('ERROR')
        task.process_number =process_number
        queue.put(task)
        
        try:
            os.remove(macrofile.name) 
        except:
            print 'Error removing macro file'

        if not hasattr(self, 'results'):
            self.results = dict()        
#        for outvar in task.outputs:
#            if output.has_key(outvar):
        if not self.results.has_key(task.number):
            self.results[task.number] = dict()
        self.results[task.number] = output  





            
    
    def _create_anybodycon_cmd(self, macro_filename, task):
        cmd = [self.anybodycon_path, '--macro=', macro_filename, '/ni', ' '] 
        return cmd
        
def _printresult(no, time, text = '', log = None, error = False ):
    status = 'n={0!s} : {1!s}sec : {2}'.format(no, time, text)            
        
    if log is not None:
        status += ' ( {0} )'.format(os.path.basename(log))
    
    with print_lock:
        if error:
            print 'Failed : ',status,' '*10
        else:
            print 'Completed : ',status,' '*10
        sys.stdout.flush()


def _schedule_processes(tasklist, _worker, num_processes):
    queue = Queue.Queue()
    
#    # Schedule serially if no multitasking is needed.
#    if num_processes == 1 or len(tasklist) == 1:
#        for task in tasklist:
#            _worker(task,queue)
#        return
    
    pbar = ProgressBar(len(tasklist))
    pbar.animate(0)

    
    # #lse start the tasks in threads
    threads = []
    errorlist = []
    
    counter = 1
    
    # run until all the threads are done, and there is no data left
    while threads or tasklist:
        # if we aren't using all the processors AND there is still data left to
        # compute, then spawn another thread
        if (len(threads) < num_processes) and tasklist:
            t = Thread(target=_worker, args=tuple([tasklist.pop(0),queue]))
            t.daemon = True
            t.start()
            threads.append(t)
		# in the case that we have the maximum number of threads check if any of them
		# are done. (also do this when we run out of data, until all the threads are done)
        else:
            for thread in threads:
                if not thread.isAlive():
                    threads.remove(thread)
                while queue.qsize() > 0:
                    task = queue.get()
                    pbar.animate(counter)
                    counter+=1
                    if task.error:
                        errorlist.append(task)

                    
            time.sleep(0.5)
    
    for failedtask in errorlist:
        _printresult(failedtask.number, failedtask.processtime, failedtask.name,
                      log = failedtask.log,
                      error = failedtask.error)

def _parse_anybodycon_output(strvar):
    out = {};
    for line in strvar.splitlines():
        if line.endswith(';'):
            (first, last) = line.split('=')
            first = first.strip()
            last = last.strip(' ;').replace('{','[').replace('}',']')
            out[first.strip()] = eval(last)
        if line.startswith('ERROR') or line.startswith('Error'): 
            if line.endswith('Path does not exist.'):
                continue # hack to avoid detecting #path error this error which is always present
            if not out.has_key('ERROR'): out['ERROR'] = []
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
        self.__update_amount(0)
        self.animate = self.animate_ipython

    def animate_ipython(self, iter):
        try:
            if run_from_ipython():
                clear_output()
        except ValueError:
            # terminal IPython has no clear_output
            pass
        print '\r', self,
        sys.stdout.flush()
        self.update_iteration(iter + 1)

    def update_iteration(self, elapsed_iter):
        self.__update_amount((elapsed_iter / float(self.iterations)) * 100.0)
        self.prog_bar += '  %d of %s complete' % (elapsed_iter, self.iterations)

    def __update_amount(self, new_amount):
        percent_done = int(round((new_amount / 100.0) * 100.0))
        all_full = self.width - 2
        num_hashes = int(round((percent_done / 100.0) * all_full))
        self.prog_bar = '[' + self.fill_char * num_hashes + ' ' * (all_full - num_hashes) + ']'
        pct_place = (len(self.prog_bar) / 2) - len(str(percent_done))
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
    
    print 'Test param job'
    basepath = op.join( op.dirname(abcutils.__file__), 'test_models')
    app = AnyPyProcess(basepath, num_processes = 10, keep_logfiles = False)
    loadmcr = ['load "Demo.Arm2D.any"']
    mainmcr = ['operation ArmModelStudy.InverseDynamics',
              'run']
#    invars= {'Main.ArmModel.Loads.HandLoad.F': [array([0,0,-40]),array([10,0,-40])],
#              'Main.ArmModel.Segs.LowerArm.Brachialis.sRel': [array([-0.1, 0, 0 ]),array([-0.09, 0, 0 ]) ] }
    invars = {'Main.ArmModel.Segs.LowerArm.Brachialis.sRel':
                  list( array([-0.1,0,0]) +  0.03* random.randn(100,1)) }
    outvars = [ 'Main.ArmModelStudy.Output.Model.Muscles.Brachialis.Activity']
    res = app.start_param_job(loadmcr, mainmcr, invars, outvars)   
    print("")
    
    
    import matplotlib.pyplot as plt 
    plt.plot(res.values()[0][3],'r--', linewidth=6)

    for data in res.values()[0]:
        plt.plot(data)
    #plt.axis([0,100 , 0, 1])
    plt.show()




if __name__ == '__main__':
#    for data,header,filename in csv_trial_data('C:\Users\mel\SMIModelOutput', DEBUG= True):
#        print header
    test()    
#    outvars = ['/Output/Validation/EMG'] 
        