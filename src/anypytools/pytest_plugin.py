# -*- coding: utf-8 -*-
"""
Created on Mon Sep  1 12:44:36 2014

@author: Morten
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *

import os
import re
import ast
import glob
import shutil
import textwrap
import itertools
import contextlib
import subprocess
from traceback import format_list, extract_tb

import h5py
import pytest

from anypytools import AnyPyProcess, macro_commands
from anypytools.tools import (
    get_anybodycon_path, replace_bm_constants,
    anybodycon_version, find_ammr_version, get_tag
)
from anypytools.generate_macros import MacroGenerator

@contextlib.contextmanager
def cwd(path):
    oldpwd=os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)



class AnyTestSession(object):
    """ Class for storing configuation of the AnyTest plugin to pytest. """ 

    def __init__(self):
        self.ammr_version = ''
        self.ams_version = ''
        self.basefolder = ''
        self.anytest_compare_dir = ''
        self.current_run_folder = None
        self.save = ''
        self.last_number = None
        self.last_session = None
        self.compare_session = None

    def configure(self, config):
        """ Configures the AnyTestSession object. This can't be in __init__()
            since it is instantiated and added to the pytest namespace very
            early in the pytest startup.
        """
        self.basefolder = config.getoption("--anytest-storage")
        if not os.path.exists(self.basefolder):
            os.makedirs(self.basefolder)
        self.save = config.getoption("--anytest-save") or config.getoption("--anytest-autosave")
        ammr_path = config.getoption("--ammr") or config.rootdir.strpath
        self.ammr_version = find_ammr_version(ammr_path)
        self.ams_version = anybodycon_version(anybodycon_path(config))
        self.compare_session = self.get_compare_session(config)
        self.run_compare_test = bool(self.save or self.compare_session)


    def get_compare_session(self, config):
        """ Get the session to compare against """
        comp = config.getoption("--anytest-compare")
        if not comp:
            return None
        elif isinstance(comp, str) and comp.isdigit():
            session = self._get_storage_folder(int(comp))
        else:
            session = self._get_storage_folder()
        if not session:
            raise ValueError('Could not find any stored test runs to compare against')
        return session

    def finalize(self, config):
        if self.save:
            storage_folder = os.path.join(self.basefolder, self.session_name)
            if os.path.exists(self.current_run_folder):
                shutil.copytree(self.current_run_folder, storage_folder)


    @property
    def session_name(self):
        if self.save:
            return '{:0>4d}_{}'.format(self.last_number + 1, self.save)


    def get_compare_params(self):
        """ Return (base, h5) for every file compare store. """ 
        if self.compare_session is None:
            return []
        with cwd(self.compare_session):
            stored_h5files = glob.glob('**/*.anydata.h5')
        return zip([self.compare_session]*len(stored_h5files), stored_h5files)



    def _get_largest_prefix(self):
        """ Return the heights prefix number for folders
            in the self.basedir
        """
        subdirs = next(os.walk(self.basefolder))[1]
        prefixes = [s.split('_')[0] for s in subdirs]
        numbers = [int(s) for s in prefixes if s.isdigit()]
        return max(numbers + [0])

    def _get_storage_folder(self, number=None):
        """ Return the full folder name starting with num in
            self.basedir
        """
        if not number:
            number = self._get_largest_prefix()
        if number is None:
            return None
        folder = glob.glob('{}\\{:0>4d}_*\\'.format(self.basefolder, number))
        if len(folder) > 1:
            raise ValueError('More folders with the same'
                             ' number prefix in {}'.format(self.basefolder))
        elif len(folder) == 0:
            return None
        else:
            return folder[0]

    def get_compare_fname(self, name, id, study):
        """ Return the name of the compare h5file, and ensure the parent folder exists"""
        # Initialize and empty the current_run folder.
        if not self.current_run_folder:
            self.current_run_folder = os.path.join(self.basefolder, 'current_run')
            if os.path.exists(self.current_run_folder):
                shutil.rmtree(self.current_run_folder)
        if id > 0:
            compare_test_name = '{}_{}'.format(name, id)
        else:
            compare_test_name = '{}'.format(name)
        compare_test_folder = os.path.join(self.current_run_folder, compare_test_name)
        studyname = '{}.anydata.h5'.format(study)
        return os.path.join(compare_test_folder, studyname)





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


def _read_header(fpath):
    """ Read the commented header of anyscript
        file and return it with leading '//' comments
        removed"""
    code = ''
    with open(fpath) as f:
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


def pytest_generate_tests(metafunc):
    if 'anytest_compare' in metafunc.fixturenames:
        params = pytest.anytest.get_compare_params()
        metafunc.parametrize("anytest_compare",
                             params, indirect=True)


@pytest.fixture
def anytest_compare(request):
    import ipdb;ipdb.set_trace()
    storage_folder, h5file = request.param
    current_folder = pytest.anytest.current_run_folder
    current_fname = os.path.join(current_folder, h5file)
    if os.path.exists(current_fname):
        current_h5 = h5py.File(current_fname)
        stored_h5 = h5py.File(os.path.join(storage_folder, h5file))
        yield current_h5, stored_h5
    else:
        pytest.skip('No matching h5 file found')
        yield (None, None)


def pytest_collect_file(parent, path):
    if path.ext.lower() == ".any" and path.basename.lower().startswith("test_"):
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

def _as_absolute_paths(d, start=os.getcwd()):
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

def pytest_collection_modifyitems(session, config, items):
    first = []
    last = []
    other = []
    for item in items:
        if hasattr(item, 'fixturenames') and 'anytest_compare' in item.fixturenames:
            last.append(item)
        elif item.get_marker('stores_h5'):
            first.append(item)
        else:
            other.append(item)
    items[:] = first + other + last

def pytest_namespace():
    """ Add an instance of the AnyTestSession class to
        to the pytest name space """
    return {'anytest': AnyTestSession()}


def pytest_configure(config):
    pytest.anytest.configure(config)

def pytest_unconfigure(config):
    pytest.anytest.finalize(config)
    #config.anytest_abc_version = anybodycon_version(config.getoption("--anybodycon"))
    #config.anytest_ammr_version = find_ammr_version(config.rootdir)


def write_macro_file(path, name, macro):
    filename = os.path.join(path, name + '.anymcr')
    with open(filename, 'w') as f:
        f.writelines([str(mcr)+'\n' for mcr in macro])
    return filename

def anybodycon_path(config):
    path = config.getoption("--anybodycon")
    if path is None:
        path = get_anybodycon_path()
    return path

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
            if isinstance(defs, dict) and isinstance(paths, dict):
                yield AnyItem(name=self.fspath.basename, id=i, parent=self,
                              defs=defs, paths=paths, **header)
            else:
                raise ValueError('Malformed input: ', header)


class AnyItem(pytest.Item):
    def __init__(self, name, id, parent, defs, paths, **kwargs):
        test_name = '{}_{}'.format(name, id)
        super().__init__(test_name, parent)
        self.defs = defs
        self.defs['TEST_NAME'] = '"{}"'.format(test_name)
        if self.config.getoption("--ammr"):
            paths['AMMR_PATH'] = self.config.getoption("--ammr")
        self.paths = _as_absolute_paths(paths, start=self.config.rootdir.strpath)
        self.name = test_name
        self.expect_errors = kwargs.get('expect_errors', [])
        self.ignore_errors = kwargs.get('ignore_errors', [])
        self.compare_study = kwargs.get('compare_study', None)
        if self.compare_study:
            self.add_marker('stores_h5')
        self.timeout = self.config.getoption("--timeout")
        self.errors = []
        self.macro = [macro_commands.Load(self.fspath.strpath,
                                          self.defs, self.paths)]
        self.compare_filename = None
        self.macro_file = None
        self.anybodycon_path = anybodycon_path(self.config)
        self.apt_opts = {
            'return_task_info': True,
            'silent': True,
            'anybodycon_path': self.anybodycon_path,
            'ignore_errors': self.ignore_errors,
            'timeout': self.timeout
        }
        if not self.config.getoption("--only-load"):
            self.macro.append(macro_commands.OperationRun('Main.RunTest'))
        if pytest.anytest.run_compare_test and self.compare_study:
            # Add compare test to the test macro
            self.compare_filename = pytest.anytest.get_compare_fname(name, id, self.compare_study)
            save_str = 'classoperation {}.Output "Save data" --type="Deep" --file="{}"'
            save_str = save_str.format(self.compare_study, self.compare_filename)
            self.macro.append(macro_commands.MacroCommand(save_str))



    def runtest(self):
        tmpdir = self.config._tmpdirhandler.mktemp(self.name)
        if self.compare_filename:
            os.makedirs(os.path.dirname(self.compare_filename))
        with change_dir(tmpdir.strpath):
            app = AnyPyProcess(**self.apt_opts)
            result = app.start_macro(self.macro)[0]
            self.app = app
        # Ignore error due to missing Main.RunTest
        if 'ERROR' in result:
            for i, err in enumerate(result['ERROR']):
                runtest_errros = ('Error : Main.RunTest : Unresolved object',
                                  'Main.RunTest : Select Operation is not expected')
                if any(s in err for s in runtest_errros):
                    del result['ERROR'][i]
                    break
        # Check that the expected errors are present
        if self.expect_errors:
            error_list = result.get('ERROR', [])
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
        # Add info to the hdf5 file if compare output was set
        if self.compare_filename is not None:
            import h5py
            f = h5py.File(self.compare_filename, 'a')
            f.attrs['anytest_processtime'] = result['task_processtime']
            f.attrs['anytest_macro'] = '\n'.join(result['task_macro'][:-1])
            f.attrs['anytest_ammr_version'] = pytest.anytest.ammr_version
            f.attrs['anytest_ams_version'] = pytest.anytest.ams_version
            f.close()
            basedir = os.path.dirname(self.compare_filename)
            macrofile = write_macro_file(basedir, self.compare_study, self.macro[:-1])
            with open(os.path.join(basedir, self.compare_study + '.bat'), 'w') as f:
                anybodygui = re.sub(r"(?i)anybodycon\.exe", r"anybody\.exe", self.anybodycon_path)
                f.write('"{}" -m "{}"'.format(anybodygui, macrofile))
        
        if len(self.errors) > 0:
            if self.config.getoption("--create-macros"):
                macro_name = write_macro_file(self.fspath.dirname, self.name, self.macro)
                self.macro_file = macro_name
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


    


def parse_save_name(stringval):
    if not stringval:
        raise argparse.ArgumentTypeError("Argument can't be empty.")
    not_allowed = ''.join(c for c in r"\/:*?<>|" if c in stringval)
    if not_allowed:
        raise argparse.ArgumentTypeError("The following characters are not allowed: "
                                         "/:*?<>|\\ (it has %r)" % not_allowed)
    return stringval

def pytest_addoption(parser):
    group = parser.getgroup("anypytools", "testing AnyBody models")

    group.addoption("--anybodycon", action="store", metavar="path",
        help="anybodycon.exe used in test: default or path-to-anybodycon")
    group.addoption("--ammr", action="store", metavar="path",
        help="Can be used to specify which AnyBody Managed Model Repository (AMMR) "
             "to use. Setting this will pass a 'AMMR_PATH' path statement for all "
             "models")
    group.addoption("--only-load", action="store_true",
        help="Only run a load test. I.e. do not run the 'RunTest' macro")
    group._addoption("--timeout", default=3600, type=int,
        help="terminate tests after a certain timeout period")
    tag = get_tag()
    group.addoption("--anytest-save", metavar="NAME", type=parse_save_name,
        help='Save the current run into folder `~/.anytest/counter-NAME/`.'
        'Default: `<commitid>_<date>_<time>_<isdirty>`, example: `%s`.'% tag)
    group.addoption( "--anytest-autosave", action='store_const', const=tag,
        help="Autosave the current run into folder'~/.anytest/counter_%s/" % tag)
    group.addoption("--create-macros", action="store_true",
        help="Create a macro file if the test fails. This makes it easy to re-run "
             "the failed test in the gui application.")
    group.addoption("--anytest-compare",
        metavar="NUM", nargs="?", default=[], const=True,
        help="Compare the current run against run NUM or the latest "
             "saved run if unspecified.")
    group.addoption("--anytest-storage",
        metavar="path", default=os.path.expanduser("~/.anytest"),
        help="Specify a path to store the runs (when --anytest-save "
             "or --benchmark-autosave are used). Default: %(default)r."
    )
    
    #parser.addini('ammrdirs', 'list of ammr paths to test against.', type="pathlist")


#def pytest_report_header(config):
#    return '\nAnyPyTools Test Plugin\n'
#    

    

        
