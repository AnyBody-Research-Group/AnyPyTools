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
import textwrap
import itertools
import contextlib
import subprocess 
from traceback import format_list, extract_tb

import pytest

from anypytools import AnyPyProcess, macro_commands
from anypytools.tools import get_anybodycon_path, replace_bm_constants
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

        
def _read_header(path):
    code = ''
    with open(path) as f:
        for line in f.readlines():
            if line.startswith('//'):
                line = line.strip('//')
                code += line
            else:
                break
    return code


@contextlib.contextmanager
def change_dir(path):
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def pytest_collect_file(parent, path):
    if path.ext.lower() == ".any" and path.basename.lower().startswith("test_"):
        return AnyFile(path, parent)
    elif parent.config.getoption("--collect-main-files"):
        if path.basename.lower().endswith('main.any'):
            return AnyFile(path, parent)

def _format_switches(defs):
    if isinstance(defs, dict):
        defs = [defs]
    elif isinstance(defs, tuple):
        combinations = list(itertools.product(*defs))
        defs = []
        for elem in combinations:
            defs.append({k: v for d in elem for k,v in d.items()})
    elif isinstance(defs, list):
        pass
    else:
        defs = [{}]
    if len(defs) == 0:
        defs = [{}]
    return defs

def _as_absolute_paths(d, start): 
    return {k: os.path.abspath(os.path.relpath(v, start)) for k, v in d.items()}


HEADER_ENSURES = (
    ('define', (dict, list, tuple)),
    ('path', (dict, list, tuple)),
    ('ignore_errors', (list, )),
    ('expect_errors', (list, )),
)

def _parse_header(header):
    ns = {}
    try:
        exec(header, globals(), ns)
    except SyntaxError:
        pass
    if len(ns) == 0:
        try:
            ns['define'] = ast.literal_eval(header)
        except SyntaxError:
            pass
    for name, types in HEADER_ENSURES:
        if name in ns and not isinstance(ns[name], types):
            typestr = ', '.join([t.__name__ for t in types])
            msg = '{} must be one of the following type(s) ({})'.format(name, typestr)
            raise TypeError('define must be a dictionary, list or tuple')
    return ns

class AnyFile(pytest.File):
    def collect(self):
        # Collect define statements from the header
        strheader = _read_header(self.fspath.strpath)
        header = _parse_header(strheader)
        def_list = _format_switches(header.pop('define', {}))
        def_list = [replace_bm_constants(d) for d in def_list]
        path_list = _format_switches(header.pop('path', {}))
        combinations = itertools.product(def_list, path_list)
        # Run though the defines an create a test case for each
        for i, (defs, paths) in enumerate(combinations):
            name = '{}_{}'.format(self.fspath.basename, i)
            if isinstance(defs, dict) and isinstance(paths, dict):
                yield AnyItem(name=name, parent=self, defs=defs, paths=paths, **header)
            else:
                raise ValueError('Malformed input: ', header)


class AnyItem(pytest.Item):
    def __init__(self, name, parent, defs, paths, **kwargs):
        super().__init__(name, parent)
        self.defs = defs
        self.defs['TEST_NAME'] = '"{}"'.format(name)
        self.paths = _as_absolute_paths(paths, self.fspath.dirname)
        self.name = name
        self.expect_errors = kwargs.get('expect_errors', [])
        self.ignore_errors = kwargs.get('ignore_errors', [])
        self.timeout = self.config.getoption("--timeout")
        self.errors = []
        self.macro = [macro_commands.Load(self.fspath.strpath,
                                          self.defs, self.paths)]
        self.macro_file = None
        if not self.config.getoption("--only-load"):
            self.macro.append(macro_commands.OperationRun('Main.RunTest'))
            user_macro = self.config.getoption("--run-macro")
            if user_macro is not None:
                self.macro.append(macro_commands.OperationRun(user_macro))
        self.apt_opts = {
            'return_task_info': True,
            'silent': True,
            'anybodycon_path': self.config.getoption("--anybodycon"),
            'ignore_errors': self.ignore_errors,
            'timeout': self.timeout
            }


    def runtest(self):
        tmpdir = self.config._tmpdirhandler.mktemp(self.name)
        with change_dir(tmpdir.strpath):
            app = AnyPyProcess(**self.apt_opts)
            result = app.start_macro(self.macro)[0]
            self.app = app
        # Ignore error due to missing Main.RunTest
        if 'ERROR' in result:
            for i, e in enumerate(result['ERROR']):
                if 'Error : Main.RunTest : Unresolved object' in e:
                    del result['ERROR'][i]
                    break
        # Check that the expected errors are present
        if self.expect_errors is not None:
            if 'ERROR' in result:
                # Remove any failures due to RunTest not working on failed models
                for i, e in enumerate(result['ERROR']):
                    if 'Main.RunTest : Select Operation is not expected' in e:
                        del result['ERROR'][i]
                        break
                error_list = result['ERROR']
            else:
                error_list = []
            for xerr in self.expect_errors:
                xerr_found = False
                for i, error in enumerate(error_list):
                    if xerr in error:
                        xerr_found = True
                        del error_list[i]
                if not xerr_found:
                    self.errors.append('TEST ERROR: Expected error not '
                                        'found: "{}"'.format(xerr))
        # Add remaining errors to item's error list
        if 'ERROR' in result and len(result['ERROR']) > 0:
            self.errors.extend(result['ERROR'])
        if len(self.errors) > 0:
            if self.config.getoption("--create-macros"):
                macro_file = 'run_{}.anymcr'.format(self.name)
                macro_file = os.path.join(self.fspath.dirname, macro_file)
                with open(macro_file,'w') as f:
                    f.writelines([str(mcr)+'\n' for mcr in self.macro])
                self.macro_file = macro_file
            raise  AnyException(self)
        return
        
    def repr_failure(self, excinfo):
        """ called when self.runtest() raises an exception. """
        if isinstance(excinfo.value, AnyException):
            rtn = 'Execution failed:\n'
            for elem in self.errors:
                rtn += textwrap.fill(elem, 80, 
                                     initial_indent='  *',
                                     subsequent_indent='   ')
                rtn += '\n'
            rtn += "\nMain file:\n"
            rtn += "  {}\n".format(self.fspath.strpath.replace(os.sep,os.altsep))
            rtn += "AnyBody Console:\n"
            rtn += "  {}\n".format(self.app.anybodycon_path.replace(os.sep, os.altsep))
            rtn += "Special model configuration:\n"
            for k,v in self.defs.items():
                rtn += "  #define {} {}\n".format(k,v)
            for k,v in self.paths.items():
                rtn += "  #path {} {}\n".format(k,v)
            if self.macro_file is not None:
                macro_file = self.macro_file.replace(os.sep,os.altsep)
                rtn += 'Macro:\n'
                rtn += '  anybody.exe -m "{}" &\n'.format(macro_file)
            return rtn
        else:
            return str(excinfo.value)

    def reportinfo(self):
        return self.fspath, 0, "AnyBody Simulation: %s" % self.name

        
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
    group._addoption("--anybodycon", action="store", metavar="path",
        help="anybodycon.exe used in test: default or path-to-anybodycon")
    group._addoption("--collect-main-files", action="store_true",
        help="Also collect any files called ending in 'main.any'")
    group._addoption("--only-load", action="store_true",
        help="Only run a load test. I.e. do not run the 'RunTest' macro")
    group._addoption("--timeout", default=3600, type=int,
        help="terminate tests after a certain timeout period")
    group._addoption("--run-macro", action="store", default=None,
        help="Specify a special macro to run")
    group._addoption("--create-macros", action="store_true",
        help="Create a macro file if the test fails. This makes it easy to re-run "
             "the failed test in the gui application.")
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
    if anybodycon_path is None:
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
    if anybodycon_path == None:
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
