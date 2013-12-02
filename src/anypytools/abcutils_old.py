# -*- coding: utf-8 -*-
"""
Created on Thu Sep 22 09:55:13 2011

@author: melund
"""

import os
import subprocess
#import threading
#import time
import numpy as np
#import multiprocessing
import tempfile
import threading
import time
import signal
import shutil 
import re

def getAnyBodyConsole():
	import _winreg
	abpath = _winreg.QueryValue(_winreg.HKEY_CLASSES_ROOT,
			'AnyBody.AnyScript\shell\open\command').rsplit(' ',1)[0]
	return os.path.join(os.path.dirname(abpath),'AnyBodyCon.exe')

def getNumberOfProcessors():
    from multiprocessing import cpu_count
    return cpu_count()


class AnyBatchProcess():
    # This anybodycon on in all subfolder of a directory tree with a given macro.
    def __init__(self, basepath = os.getcwd(), searchfile = None,
        num_processes = getNumberOfProcessors(), abcpath = getAnyBodyConsole(),
         stop_on_error = True,  defines=dict(), paths=dict() ):
        self.definedict = defines
        self.pathdict = paths
        self.basepath = os.path.abspath(basepath)
        self.abcpath = abcpath
        self.searchfile = searchfile
        self.stop_on_error = stop_on_error
        self.abcpath = abcpath
        self.num_processes = num_processes
        self.counter = 0
        self.pids = set()

	
	# Function that runs the anybody model
    def worker(self,workdir, macrolist):
        head, trialname = os.path.split(workdir)
        subjectname = os.path.basename(head)
        processcount = self.counter
        self.counter += 1

        macrofile = open(os.path.join(workdir,'tmp_macro.anymcr'),'w')
#        macrofile = tempfile.NamedTemporaryFile(mode='w+b', suffix='.anymcr', delete=False)

        tmplogfile = tempfile.NamedTemporaryFile(mode='w+b', suffix='.log')
#        tmplogfile = open(os.path.join(workdir,'tmp_log.txt'),'w')
        # Save macrofile to disk
        macrofile.write("\n".join( macrolist ) )
        macrofile.close()
        # Construct command to launch anybodycon
        cmd = [self.abcpath, '--macro=', macrofile.name, "--dir=", workdir.replace('\\','/'),
               '/ni', ' '] 
        for k,v in self.definedict.iteritems():
            cmd.append('/def')            
            cmd.append('%s=%s'%(k,v))
        for k,v in self.pathdict.iteritems():
            cmd.append('/p')            
            cmd.append("%s=%s"%(k,v))

               
        proc = subprocess.Popen(cmd, stdout=tmplogfile, stderr=tmplogfile,shell= False)
        self.pids.add(proc.pid)
        starttime = time.clock()
        timeout =starttime + self.timeout
        while proc.poll() is None:
            if time.clock() > timeout:
                proc.terminate()
                proc.communicate()
                tmplogfile.seek(0,2)
                tmplogfile.write('ERROR: Timed out. Terminated by batch processor')
                tmplogfile.flush()
                break
        else:
            # Remove process from set of runing processes
            self.pids.remove(proc.pid)
        
        processtime = int(time.clock()-starttime)
        
        logfilename_completed = os.path.join(workdir,'outputlog.txt')
        logfilename_error  = os.path.join(workdir,'outputlog_ERROR.txt')
        
        if os.path.exists(logfilename_completed):
            os.remove(logfilename_completed)
        if os.path.exists(logfilename_error):
            os.remove(logfilename_error)
        
        # Load logfile and parse the results            
        tmplogfile.seek(0)
        logoutput = "\n".join(tmplogfile.readlines())
        tmplogfile.close()

        output = parseAnyScriptVars( logoutput )
        # Check if process had any Errors
        if output.has_key('ERROR'):
            with open(logfilename_error,'w+') as f:
                f.write(logoutput)
                #shutil.copyfileobj(tmplogfile,f)
            print 'Error' + ':' + str(processcount) + ':'+ str(processtime)+'s:'\
            +subjectname +'/' +  trialname 
        else:
            with open(logfilename_completed,'w+') as f:
                f.write(logoutput)
                #shutil.copyfileobj(tmplogfile,f)
            print 'Completed' + ':' + str(processcount) + ':'+ str(processtime)+'s:'\
            +subjectname +'/' +  trialname 
        
        try:
            os.remove(macrofile.name)
        except:
            pass


    def start(self, macro, timeout = 60*60): 
        self.timeout = timeout
        self.counter = 0
        self.kill_all = False
        if isinstance(macro, basestring):
            macro = [macro.splitlines()]
        dirlist = getsubdirs(self.basepath,self.searchfile)
        tasklist = zip(dirlist, [macro]*len(dirlist))
        print 'Start processing ' + str(len(tasklist)) + ' files'
        try:
            if self.num_processes == 1:
                for task in tasklist:
                    self.worker(task[0], task[1])
            else:
                scheduleProcesses(tasklist, self.worker, self.num_processes)
        except KeyboardInterrupt:
            print 'Stopping'
        # Kill any rouge processes that are still running.
        for pid in self.pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print 'Kill AnyBodyProcess. PID: ' + str(pid)+ ' : Done'
            except:
                print 'Kill AnyBodyProcess. PID: ' + str(pid)+ ' : Already killed'


def scheduleProcessesDEBUG(tasklist,worker,num_processes):
    for task in tasklist:
        worker(task[0],task[1])
        

def scheduleProcesses(tasklist, worker, num_processes):
    threads = []
    # run until all the threads are done, and there is no data left
    while threads or tasklist:
        # if we aren't using all the processors AND there is still data left to
        # compute, then spawn another thread
        if (len(threads) < num_processes) and tasklist:
            args = tasklist.pop()
            if not isinstance(args, tuple):
                args = (args)
            t = threading.Thread(target=worker, args=args)
            t.daemon = True
            t.start()
            threads.append(t)

		# in the case that we have the maximum number of threads check if any of them
		# are done. (also do this when we run out of data, until all the threads are done)
        else:
            for thread in threads:
                if not thread.isAlive():
                    threads.remove(thread)	
            time.sleep(0.5)

                      
	

class AnyProcess():
    
    def __init__(self,mainfile,  num_processes = None, abcpath = None, workdir = os.getcwd() ):
        self.mainfile = os.path.abspath(mainfile)
        self.abcpath = abcpath
        if abcpath is None:
            import _winreg
            abpath = _winreg.QueryValue(_winreg.HKEY_CLASSES_ROOT,
                    'AnyBody.AnyScript\shell\open\command').rsplit(' ',1)[0]
            self.abcpath = os.path.join(os.path.dirname(abpath),'AnyBodyCon.exe')
        self.workdir = workdir
        self.results = {}
        if num_processes == None:
            from multiprocessing import cpu_count
            self.num_processes =  cpu_count()
        else:        
            self.num_processes = num_processes

            
    
#==============================================================================
#     def getReults(consoleOut):
#         self.results.append(parseAnyScriptVars(consoleOut[0]))
#==============================================================================
        
        


    def start(self,inputs,macrocmds,outputs, taskdim = 1):
    #    pool = multiprocessing.Pool(None)
        self.macrocmds = macrocmds
        self.outputlist = outputs
        self.results = {}

        tasklist = []
       
#        # Costruct a list of tuples [(var,value),(..),...]  with design values 
#        for i in range(1,len( inputs[0] )):
#            design = [(_[0],_[i]) for _ in inputs ]
#            tasklist.append(design)
#        # Run AnyBodyCon on all data
#        
        for k,v in inputs.items():
            inputs[k] = np.array(v)
        
        no_tasks = inputs.values()[0].shape[0]

        tasklist = [[None]]*no_tasks
        for i in range(no_tasks):
            tasklist[i] = []
            for name, array in inputs.items():
                if taskdim == 1:
                    tasklist[i].append( (name, array[i]) )
                elif taskdim == 2:
                    tasklist[i].append( (name,array[:,i]) )
                elif taskdim == 3:
                    tasklist[i].append( ( name, array[:,:,i]) )
        
        
        threads = []
        
        if len(tasklist) == 1:
            self.worker(tasklist.pop())
            return self.results
        # run until all the threads are done, and there is no data left
        
        while threads or tasklist:
            # if we aren't using all the processors AND there is still data left to
            # compute, then spawn another thread
            if (len(threads) < self.num_processes) and tasklist:
                t = threading.Thread(target=self.worker, args=[ tasklist.pop() ])
                t.setDaemon(True)
                t.start()
                threads.append(t)
        
            # in the case that we have the maximum number of threads check if any of them
            # are done. (also do this when we run out of data, until all the threads are done)
            else:
                for thread in threads:
                    if not thread.isAlive():
                        threads.remove(thread)
                time.sleep(0.5)
        return self.results


         
    def worker(self,designvars):
        mcrlist = ['load "%s"' % self.mainfile]
        for var in designvars:
            varname = var[0]
            valueStr = list2anyscript(var[1])
            mcrlist.append('classoperation %s "Set Value" --value=%s' % (varname, valueStr ) )
        mcrlist.extend(self.macrocmds)
        for var in self.outputlist:
            mcrlist.append( 'classoperation %s "Dump All" ' % var)
        mcrlist.append('exit')
        tmpfile = tempfile.NamedTemporaryFile(mode='w+b', suffix='.anymcr', delete=False)
        tmpfile.write("\n".join( mcrlist ) )
        tmpfile.close()
        cmd = [self.abcpath,'/m', tmpfile.name, '/d', self.workdir]   
        out_raw = subprocess.check_output(cmd, shell=False)   
        output = parseAnyScriptVars( out_raw  )
        
        if output.has_key('ERROR'):
            print output['ERROR']
        else:
            for outvar in self.outputlist:
                if output.has_key(outvar):
                    if not self.results.has_key(outvar): self.results[outvar] = []
                    self.results[outvar].append( np.array(output[outvar]) )
                    #print len(self.results[outvar])
                else:
                    pass
                    # Something wrong


  
def parseAnyScriptVars(strvar):
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
        
    
def list2anyscript(arr):
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

def getsubdirs(toppath, search_string = "."):
    reg_prog = re.compile(search_string)    
    dirlist = set()
    for root, dirs, files in os.walk(toppath):
        for fname in files:
            if reg_prog.search(os.path.join(root,fname)) is not None:
                dirlist.add(root)
                continue
    return dirlist
		
		
		
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

    from anypytools import abcutils 
    from numpy import array, random
    import os.path as op
    
    testmodel = op.join( op.dirname(abcutils.__file__), 'test_models', 'Demo.Arm2D.any'   )
    ap = abcutils.AnyProcess(testmodel, num_processes = 6)
    
    design1= {'Main.ArmModel.Loads.HandLoad.F': array([[0,0,-40],[10,0,-40]]),
              'Main.ArmModel.Segs.LowerArm.Brachialis.sRel': array([[-0.1, 0, 0 ],[-0.09, 0, 0 ]] )}
    
    designRand = {'Main.ArmModel.Segs.LowerArm.Brachialis.sRel':
                  array([-0.1,0,0]) +  0.1* random.randn(100,1) }
    
    
    out =  ap.start(inputs = designRand,
                   macrocmds= ['operation ArmModelStudy.InverseDynamics',\
                               'run'],
                   outputs = [ 'Main.ArmModelStudy.Output.Model.Muscles.BicepsLong.Activity']
                  )
           
           
           
           
    
    
    import matplotlib.pyplot as plt 
    for data in out.values()[0]:
        plt.plot(data)
    #plt.axis([0,100 , 0, 1])
    plt.show()


if __name__ == "__main__":
    # from abcutils import AnyProcess
    test()
