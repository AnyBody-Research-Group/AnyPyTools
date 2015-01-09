# -*- coding: utf-8 -*-
"""
Created on Mon Sep  1 12:44:36 2014

@author: Morten
"""
from __future__ import division, absolute_import, print_function, unicode_literals
try:
    from ..utils.py3k import * # @UnusedWildImport
    from ..utils import make_hash
except (ValueError, SystemError):
    from anypytools.utils.py3k import * # @UnusedWildImport
    from anypytools.utils import make_hash


import pytest
import shutil
import os
from anypytools.abcutils import AnyPyProcess,get_anybodycon_path
from anypytools.generate_macros import MacroGenerator
import subprocess 


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
        if isinstance(value, string_types):
            defstr =  '-def %s=---"\\"%s\\""'% (key, value)
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
