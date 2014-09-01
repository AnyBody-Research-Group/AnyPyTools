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

        
@pytest.yield_fixture(scope='module')
def copyfiles(request, test_dir):
    if request.config.getoption('--inplace'):
        # No need to copy files if test is allready run inplace.
        yield
    model_folder = request.fspath.new(basename='')
    src_files = os.listdir( str( model_folder) )
    for file_name in src_files:
        if file_name.endswith('.py') and file_name.find('test') != -1:
            continue
        full_file_name = os.path.join( str( model_folder), file_name)
        if (os.path.isfile(full_file_name) and file_name.find('_test')):
            shutil.copy(full_file_name, str(test_dir))
        if os.path.isdir(full_file_name):
            dest = os.path.join(str(test_dir), file_name)
            shutil.copytree(full_file_name,dest, 
                            ignore=shutil.ignore_patterns('test_*.py','*_test.py'))
    yield

@pytest.yield_fixture(scope='module')
def test_dir(request):
    model_folder = request.fspath.new(basename='')
    if request.config.getoption('--inplace'):
        yield model_folder
    else:
        tempdir = request.config._tmpdirhandler.mktemp(model_folder.basename,
                                                   numbered=True)
        yield tempdir

def pytest_addoption(parser):
    parser.addoption("--ammr", action="store", default="built-in",
        help="AMMR used in test: built-in or path-to-ammr")
    parser.addoption("--anybodycon", action="store", default="default",
        help="anybodycon.exe used in test: default or path-to-anybodycon")
    parser.addoption("--inplace", action="store_true",
        help="Run test in place, i.e. do not copy folder")


@pytest.yield_fixture()
def anymocap(request, scope="session"):  
    anymocap_path = os.path.join(os.getcwd(), 'Model', 'AnyMocapModel.any')
    yield anymocap_path
        

  
def pytest_report_header(config):
    return '\nAnyPyTools Test Plugin\n'
    


def pytest_configure(config):
    anybodycon_path = config.getoption("--anybodycon")
    if anybodycon_path == 'default':
        anybodycon_path = get_anybodycon_path()

    ammr_path = config.getoption("--ammr")
    if ammr_path == 'built-in':
        ammr_path = os.path.join(os.path.dirname(get_anybodycon_path()),'AMMR')

    if not os.path.exists(ammr_path):
        raise IOError('Cound not find: {}'.format(ammr_path))
    if not os.path.isfile(anybodycon_path):
        raise IOError('Cound not find: {}'.format(anybodycon_path))
    
    console_output = subprocess.check_output([anybodycon_path, '/ni'])
    ams_version = console_output.splitlines()[2].decode()[23:]
    ammr_version = get_ammr_version(ammr_path)
    setattr(config, 'ammr_path', ammr_path)
    setattr(config, 'ammr_version', ammr_version)
    setattr(config, 'anybodycon_version', ams_version)
    setattr(config,'anybodycon_path', anybodycon_path)
    

class AnyTestFixture():
    def __init__(self, test_dir, model_dir, app, ammr, anymocap):
        self.app = app
        self.ammr = ammr
        self.anymocap = anymocap
        self.model_path = model_dir
        self.test_dir = test_dir
        self.macro_gen = MacroGenerator()

       
    def load_macro(self,mainfile,define={},path={}):
        main_path = os.path.join(self.model_path,mainfile)
        load_str = 'load "{}" '.format(main_path)
        path['AMMR_PATH'] = self.ammr
        path['ANYMOCAP'] = self.anymocap
        path['TEMP_PATH'] = self.test_dir
        path['ANYBODY_PATH_OUTPUT'] = self.test_dir
        for key,value in path.items():
            load_str += self.path2str(key,value)+" "
        for key,value in define.items():
            load_str += self.define2str(key,value)+" "
        return load_str

    def check_output_log(self,result_list):
        __tracebackhide__ = True
        for result in result_list:
            if 'ERROR' in result:
                for err in result['ERROR']:
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
        
        
        
        
@pytest.yield_fixture()
def anytest(request, anymocap, test_dir):  
    #global _anybodycon_path, _ammr_path
    
    ammr = request.config.ammr_path
    model_dir = request.fspath.new(basename='')
    
    app = AnyPyProcess( anybodycon_path = request.config.anybodycon_path,
                        keep_logfiles=True,
                        logfile_prefix = request.function.__name__, 
                        disp=False)
    
    atf = AnyTestFixture(str(test_dir), str(model_dir), app, ammr, anymocap)
    with test_dir.as_cwd():
        yield atf
