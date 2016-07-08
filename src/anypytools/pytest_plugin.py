# -*- coding: utf-8 -*-
"""
Created on Mon Sep  1 12:44:36 2014

@author: Morten
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *

import os
import ast
import shutil
import itertools
import contextlib
import subprocess 
from traceback import format_list, extract_tb

import pytest

from anypytools import AnyPyProcess, macro_commands
from anypytools.tools import get_anybodycon_path
from anypytools.generate_macros import MacroGenerator


def _limited_traceback(excinfo):
    """ Return a formatted traceback with all the stack
        from this frame (i.e __file__) up removed
    """
    tb = extract_tb(excinfo.tb)
    try:
        idx = [__file__ in e for e in tb].index(True)
        return format_list(tb[idx+1:])
    except ValueError:
        return format_list(tb)

        
@contextlib.contextmanager        
def change_dir(path):
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)    
     

def pytest_collect_file(parent, path):
    if path.ext.lower() == ".any" and path.basename.startswith("test_"):
            return AnyFile(path, parent)
    elif parent.config.getoption("--collect-main-files"):
        if path.basename.lower().endswith('main.any'):
            return AnyFile(path, parent)
        
        
class AnyFile(pytest.File):
    def collect(self):
        # Collect define statements from the header
        name = self.fspath.basename
        define_str = ''
        with self.fspath.open() as f:
            for line in f.readlines():
                if line.startswith('//'):
                    line = line.strip('//').strip()
                    define_str += line
                else:
                    break
        # Evaluate the collected header
        defs_list = None
        if define_str:
            try:
                defs_list = ast.literal_eval(define_str)
            except SyntaxError:
                pass
        #Check the types of the defines collected from the header
        if isinstance(defs_list, dict):
            defs_list = [defs_list]
        elif isinstance(defs_list, tuple):
            combinations = list(itertools.product(*defs_list))
            defs_list = []
            for elem in combinations:
                defs_list.append({k:v for d in elem for k,v in d.items()})
        elif isinstance(defs_list, list):
            pass
        else:
            defs_list = [{}]
        # Run though the defines an create a test case for each
        for i, defs in enumerate(defs_list):
            if isinstance(defs, dict):
                yield AnyItem('{}_{}'.format(name,i), self, defs)
            else:
                raise ValueError('Malformed input: ', define_str)

                
class AnyItem(pytest.Item):
    def __init__(self, name, parent, defs):
        super().__init__(name, parent)
        self.defs = defs
        self.name = name
        self.errors = None

    def runtest(self):
        anybodycon = self.config.getoption("--anybodycon")
        anybodycon = None if anybodycon == 'default' else anybodycon
        macro_load = [macro_commands.Load(self.fspath.strpath)]
        macro_runapp = [macro_commands.OperationRun('Main.RunApplication')]
        if self.config.getoption("--only-load"):
            macro = macro_load
        else:
            macro = macro_load + macro_runapp
        tmpdir = self.config._tmpdirhandler.mktemp(self.name)
        with change_dir(tmpdir.strpath):
            app = AnyPyProcess(return_task_info=True,
                               silent=True,
                               anybodycon_path=anybodycon)
            result = app.start_macro(macro)[0]
            if (self.config.getoption("--collect-main-files") and
                not self.name.startswith('test_') and 
                not self.config.getoption("--only-load")):
                # Rerun any collected main files if they fail because of a 
                # missing RunApplication operation
                if any('Error : Main.RunApplication : Unresolved object' in e 
                        for e in result.get('ERROR',[])):
                    result = app.start_macro(macro_load)[0]
                
        if 'ERROR' in result:
            self.errors = result['ERROR']
            raise  AnyException(self, self.name, self.defs, self.errors)
        return
        
    def repr_failure(self, excinfo):
        """ called when self.runtest() raises an exception. """
        if isinstance(excinfo.value, AnyException):
            return "\n".join([
                "usecase execution failed",
                "   Name: %r" % excinfo.value.args[1],
                "   Defines: %r" % excinfo.value.args[2],
                "   AMS errors: %r" % excinfo.value.args[3]
            ])

    def reportinfo(self):
        return self.fspath, 0, "usecase: %s" % self.name

        
class AnyException(Exception):
    """ custom exception for error reporting. """

    
def get_ammr_version(ammr_path):
    import xml.etree.ElementTree as ET
    version_file = os.path.join(ammr_path,'AMMR.version.xml')
    try:
        tree = ET.parse(version_file)
        version = tree.getroot()
        vstring = "{}.{}.{}".format(version.find('v1').text,
                                    version.find('v2').text,
                                    version.find('v3').text )
    except:
        vstring = "Unknown AMMR version"
    return vstring


def copy_files(src_dir, dst_dir):
    src_dir = str(src_dir)
    dst_dir = str(dst_dir)
    dirlist = os.listdir( src_dir )
    for name in dirlist:
        if name.endswith('.py') and name.find('test') != -1:
            continue
        full_name = os.path.join( src_dir, name)
        if (os.path.isfile(full_name) and name.find('_test')):
            shutil.copy(full_name, dst_dir)
        if os.path.isdir(full_name):
            dst_subdir = os.path.join(dst_dir, name)
            shutil.copytree(full_name,dst_subdir, 
                            ignore=shutil.ignore_patterns('test_*.py','*_test.py'))

        
@pytest.fixture(scope='module')
def copyfiles(request, test_dir):
    if request.config.getoption('--inplace') or request.config.getoption('--copyfiles'):
        # No need to copy files if test is allready run inplace, or if it
        # is done as a global option.
        pass
    else:
        model_folder = request.fspath.new(basename='')
        copy_files(model_folder, test_dir)
    return test_dir


@pytest.fixture(scope='module')
def test_dir(request):
    model_folder = request.fspath.new(basename='')
    if ( request.config.getoption('--inplace') 
         and not request.config.getoption('--copyfiles')):
        return model_folder
    else:
        tempdir = request.config._tmpdirhandler.mktemp(model_folder.basename,
                                                   numbered=True)
        return tempdir

        
@pytest.fixture(scope='module')
def model_dir(request, test_dir):
    model_folder = request.fspath.new(basename='')
    if (request.config.getoption('--copyfiles') ):
        copy_files(model_folder, test_dir)
        model_folder = test_dir
    return model_folder


def pytest_addoption(parser):
    group = parser.getgroup("anypytools", "testing AnyBody models")

    group._addoption("--ammr", action="store", default="built-in", metavar="path",
        help="AMMR used in test: built-in or path-to-ammr")
    group._addoption("--anybodycon", action="store", default="default", metavar="path",
        help="anybodycon.exe used in test: default or path-to-anybodycon")
    group._addoption("--collect-main-files", action="store_true",
        help="Also collect any files called ending in 'main.any'")
    group._addoption("--only-load", action="store_true",
        help="Only run a load test. I.e. do not run the 'RunApplication' macro")
    group._addoption("--inplace", action="store_true",
        help="Run tests in place. The macro file will be placed together with "
             "the model files. It becomes the responsobility of the model to "
             "ensure that the correct path statements are set.")
    group._addoption("--copyfiles", action="store_true",
        help=("Copy all test files to temp dir before test." 
              "This option has no effect if --inplace is set.") )
    group._addoption("--ammrdirs", action="append", default=[], metavar="path",
           help="add AMMR path to test for. (still under test)")
    
    parser.addini('ammrdirs', 'list of ammr paths to test against.', type="pathlist")


#def pytest_report_header(config):
#    return '\nAnyPyTools Test Plugin\n'
#    


def pytest_configure(config):
    anybodycon_path = config.getoption("--anybodycon")
    if anybodycon_path == 'default':
        anybodycon_path = get_anybodycon_path()

    if not os.path.isfile(anybodycon_path):
        raise IOError('Cound not find: {}'.format(anybodycon_path))
    
    console_output = subprocess.check_output([anybodycon_path, '/ni'])
    ams_version = console_output.splitlines()[2].decode()[23:]
    setattr(config, 'anybodycon_version', ams_version)
    setattr(config,'anybodycon_path', anybodycon_path)
    

class AnyTestFixture():
    def __init__(self, test_dir, model_dir, app, ammr):
        self.app = app
        self.ammr = ammr
        self.model_path = model_dir
        self.test_dir = test_dir
        self.macro_gen = MacroGenerator()
        self.path_kw = {'AMMR_PATH':ammr,
                        'TEMP_PATH': test_dir, 
                        'ANYBODY_PATH_OUTPUT':test_dir}
        self.define_kw = {}

       
    def load_macro(self,mainfile,define={},path={}):
        main_path = os.path.join(self.model_path,mainfile)
        load_str = 'load "{}" '.format(main_path)
        self.path_kw.update(path)
        self.define_kw.update(define)
        for key,value in self.path_kw.items():
            load_str += self.path2str(key,value)+" "
        for key,value in self.define_kw.items():
            load_str += self.define2str(key,value)+" "
        return load_str

    def check_output_log(self,result_list):
        __tracebackhide__ = True
        for result in result_list:
            if 'ERROR' in result:
                for err in result['ERROR']:
                    pytest.fail(err)
    
    def check_model_load_failure(self, result_list):
        __tracebackhide__ = True
        for result in result_list:
            if 'ERROR' in result:
                for err in result['ERROR']:
                    if 'Model loading skipped' in err:
                        pytest.fail(err)
    
    
    def define2str(self,key,value=None):
        if isinstance(value, str):
            if value.startswith('"') and value.endswith('"'):
                defstr = '-def %s=---"\\"%s\\""'% (key, value[1:-1])
            else:
                defstr = '-def %s="%s"'% (key, value)
        elif value is None:
            defstr = '-def %s=""'% (key)
        elif isinstance(value,float) :
            defstr =  '-def %s="%g"'% (key, value) 
        else:
            defstr = '-def %s="%d"'% (key, value) 
        return defstr 
        
    def path2str(self,key,path='.'):
        return '-p %s=---"%s"'% (key, path.replace('\\','\\\\')) 
        
        
        
        
@pytest.fixture(scope='session')
def ammr(request):
    ammr_path = request.config.getoption("--ammr")
    if ammr_path == 'built-in':
        ammr_path = os.path.join(os.path.dirname(get_anybodycon_path()),'AMMR')
    if not os.path.exists(ammr_path):
        raise IOError('Cound not find: {}'.format(ammr_path))
    ammr_version = get_ammr_version(ammr_path)

    return ammr_path
        
        
@pytest.fixture(scope='session')
def anybodycon(request):
    anybodycon_path = request.config.getoption("--anybodycon")
    if anybodycon_path == 'default':
        anybodycon_path = get_anybodycon_path()
    if not os.path.isfile(anybodycon_path):
        raise IOError('Cound not find: {}'.format(anybodycon_path))
    console_output = subprocess.check_output([anybodycon_path, '/ni'])
    ams_version = console_output.splitlines()[2].decode()[23:]
    return anybodycon_path
        

        
@pytest.yield_fixture()
def anytest(request, test_dir, model_dir, ammr, anybodycon):  
    #global _anybodycon_path, _ammr_path
    
    ammr_path = ammr
    abc_path = anybodycon
    
    if (request.config.getoption('--inplace') 
          and not request.config.getoption('--copyfiles') ):
        # Don't keep log files if test are not copied and inplace option is set.
        # This avoids clutter in the model directory
        keep_files = False
    else:
        keep_files = True
        
    
    
    app = AnyPyProcess( anybodycon_path = abc_path,
                        keep_logfiles = keep_files,
                        logfile_prefix = request.function.__name__, 
                        disp=False)
    
    atf = AnyTestFixture(str(test_dir), str(model_dir), app, ammr_path)
    if request.config.getoption('--inplace'):
        atf.path_kw = {}
        atf.model_path = ''
        
    
    with test_dir.as_cwd():
        yield atf
