# -*- coding: utf-8 -*-
"""
Created on Sun Sep  7 13:25:38 2014

@author: Morten
"""
# Python 2/3 compatibility imports
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *
from past.builtins import basestring as string_types

# Standard lib imports
import os
import re
import sys
import xml
import copy
import errno
import pprint as _pprint
import logging
import datetime
import warnings
import functools
import subprocess
import collections
from ast import literal_eval
from _thread import get_ident as _get_ident

#external imports
import numpy as np


logger = logging.getLogger('abt.anypytools')


# This hacks pprint to always return strings witout u' prefix
# important when running doctest in both python 2 og python 3
class Py3kPrettyPrinter(_pprint.PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        try:
            if isinstance(object, unicode):
                rep = u"'"  + object + u"'"
                return ( rep.encode('utf8'), True, False)
        except NameError:
            pass
        return _pprint.PrettyPrinter.format(self, object, context, maxlevels, level)

def py3k_pprint(s):
    printer = Py3kPrettyPrinter(width = 110)
    printer.pprint(s)

pprint = py3k_pprint



def run_from_ipython():
    try:
        __IPYTHON__
        return True
    except NameError:
        return False


class mixedmethod(object):
    """This decorator mutates a function defined in a class into a 'mixed' class and instance method.

    Usage:
        class Spam:
            @mixedmethod
            def egg(self, cls, *args, **kwargs):
                if self is None:
                    pass # executed if egg was called as a class method (eg. Spam.egg())
                else:
                    pass # executed if egg was called as an instance method (eg. instance.egg())

    The decorated methods need 2 implicit arguments: self and cls, the former being None when
    there is no instance in the call. This follows the same rule as __get__ methods in python's
    descriptor protocol.
    """
    def __init__(self, func):
        self.func = func
    def __get__(self, instance, cls):
        return functools.partial(self.func, instance, cls)

ANYBODYCON_VERSION_RE = re.compile(r'.*version\s:\s(?P<version>(?P<v1>\d)\.\s(?P<v2>\d)'
                                   r'\.\s(?P<v3>\d)\.\s(?P<build>\d+)\s\((?P<arc>.*)\))')
def anybodycon_version(anybodyconpath):
    """ Calls AnyBodyCon and extract version"""
    if anybodyconpath is None:
        anybodyconpath = get_anybodycon_path()
    out = subprocess.check_output([anybodyconpath, '-ni'], universal_newlines=True)
    m = ANYBODYCON_VERSION_RE.search(out)
    if m is not None:
        return m.groupdict()['version']

AMMR_VERSION_RE = re.compile(r'.*AMMR_VERSION\s"(?P<version>.*)"')

def ammr_any_version(fpath):
    with open(fpath) as f:
        out = f.read()
    match = AMMR_VERSION_RE.search(out)
    if match:
        return match.groupdict()['version']
    else:
        return "Unknown AMMR version"

def amm_xml_version(fpath):
    try:
        tree = xml.etree.ElementTree.parse(fpath)
        version = tree.getroot()
        v1, v2, v3 = version.find('v1').text, version.find('v2').text, version.find('v3').text
        return "{}.{}.{}".format(v1, v2, v3)
    except:
        vstring = "Unknown AMMR version"
    return vstring

def find_ammr_version(folder):
    """ Return the AMMR version if possible.
        The function will walk up a directory tree looking
        for a ammr_verion.any file to parse"""
    any_version_file = 'AMMR.version.any'
    xml_version_file = 'AMMR.version.xml'
    for basedir, dirs, files in walk_up(folder.strpath):
        if any_version_file in files:
            return ammr_any_version(os.path.join(basedir, any_version_file))
        elif xml_version_file in files:
            return amm_xml_version(os.path.join(basedir, xml_version_file))
    else:
        return ""




def walk_up(bottom):
    """ 
    mimic os.walk, but walk 'up'
    instead of down the directory tree
    """
    bottom = os.path.realpath(bottom)
    #get files in current dir
    names = os.listdir(bottom)
    dirs, nondirs = [], []
    for name in names:
        if os.path.isdir(os.path.join(bottom, name)):
            dirs.append(name)
        else:
            nondirs.append(name)
    yield bottom, dirs, nondirs
    new_path = os.path.realpath(os.path.join(bottom, '..'))
    # see if we are at the top
    if new_path == bottom:
        return
    for x in walk_up(new_path):
        yield x

def get_current_time():
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def get_tag(project_name=None):
    info = get_git_commit_info(project_name)
    parts = [info['id'], get_current_time()]
    if info['dirty']:
        parts.append("uncommited-changes")
    return "_".join(parts)

def get_git_project_name():
    cmd = 'git config --local remote.origin.url'.split()
    try:
        output = subprocess.check_output(cmd, universal_newlines=True)
    except subprocess.CalledProcessError:
        name = None
    else:
        name = re.findall(r'/([^/]*)\.git', output)[0]
    return name if name is not None else os.path.basename(os.getcwd())


def get_git_branch_info():
    """ return the branch name for git repository"""
    cmd = 'git rev-parse --abbrev-ref HEAD'
    try:
        branch = subprocess.check_output(cmd, universal_newlines=True).strip()
    except subprocess.CalledProcessError as e:
        branch = 'unknown'
    else:
        if branch == 'HEAD':
            return '(detached head)'
    return branch


def get_git_commit_info(project_name=None):
    dirty = False
    commit = 'unversioned'
    project_name = project_name or get_git_project_name()
    branch = get_git_branch_info()
    cmd = 'git describe --dirty --always --long --abbrev=6'.split()
    try:
        output = subprocess.check_output(cmd, universal_newlines=True).strip()
    except subprocess.CalledProcessError as e:
        pass
    else:
        try:
            output = output.split('-')
            if output[-1].strip() == 'dirty':
                dirty = True
                output.pop()
            commit = output[-1].strip('g')
        except Exception as e:
            commit = 'unknown'
    return dict(id=commit, dirty=dirty, project=project_name, branch=branch)


def get_first_key_match(key, names):
    if key in names:
        return key
    matching = [v for v in names if key in v]
    if not matching:
        raise KeyError('The key "{}" could not be found'.format(key))

    if len(matching) > 1:
        print('WARNING: "{}" key is not unique.'
              ' Using the first match'.format(key), file=sys.stderr)
        print('-> ' + matching[0], file=sys.stderr)
        for match in matching[1:]:
            print(' * '+match, file=sys.stderr)

    return matching[0]

class AnyPyProcessOutputList(collections.MutableSequence):
    """ List like class to wrap the output of model simulations.

        The class behaves as a normal list but provide
        extra function to easily access data.
    """
    def __init__(self, *args):
        self.list = list()
        for elem in args:
            self.extend(list(elem))


    def check(self, v):
        if not isinstance(v, collections.MutableSequence) :
            v = [v]
        for e in v:
            if not isinstance(e, collections.OrderedDict):
                raise(TypeError(e))

    def __len__(self): return len(self.list)

    def __getitem__(self, i):
        if isinstance(i, string_types):
            # Find the entries where i matches the keys
            key = get_first_key_match(i, self.list[0])
            try:
                data = np.array(
                    [super(AnyPyProcessOutput, e).__getitem__(key) for e in self.list]
                     )
            except KeyError:
                raise KeyError(" The key '{}' is not present "
                               "in all elements of the output.".format( key ) )
            if data.dtype == np.dtype('O'):
                # Data will be stacked as an array of objects, if the
                # time dimension is not consistant. Warn that some numpy
                # featurs will not be avaiable.
                warnings.warn('\n\nSimulation time varies across macros. '
                      'Numpy does not support ragged arrays. Data is returned  '
                      'as an array of array objects' )
            return data
        else:
            return type(self)(self.list[i]) if isinstance(i, slice) else self.list[i]



    def __delitem__(self, i): del self.list[i]

    def __setitem__(self, i, v):
        self.check(v)
        if isinstance(i, slice):
            self.list[i] = v
        else:
            self.list[i] = v

    def insert(self, i, v):
        self.check(v)
        self.list.insert(i, v)

    def __str__(self):
        return str(self.list)

    def __repr__(self):
        def create_repr(maxlength = 500):
            repr_list = []
            for elem in self.list:
                if not isinstance(elem, AnyPyProcessOutput):
                    repr_list.append( '  ' + _pprint.pformat(elem))
                    continue
                for line in elem._repr_gen(prefix = ' '):
                    repr_list.append(line)
                    if maxlength and len(repr_list) > maxlength:
                        repr_list.append('  ...')
                        return repr_list
                if repr_list and not repr_list[-1].endswith(','):
                    repr_list[-1] = repr_list[-1] + ','

            if len(repr_list):
                repr_list[-1] = repr_list[-1].rstrip(',')
                repr_list[0] = '[' + repr_list[0][1:]
                repr_list[-1] = repr_list[-1] + ']'
            else:
                repr_list.append('[]')
            return repr_list

        repr_str = '\n'.join(create_repr(500))
        if repr_str.endswith('...'):
            np.set_printoptions(threshold = 30)
            repr_str = '\n'.join(create_repr(1000))
            np.set_printoptions()
        return repr_str

    def filter(self, func):
        """ Constructs a AnyPyProcessOutputList object from those elements
        where function returns true.
        """
        return AnyPyProcessOutputList(filter(func, self))


    def to_dynd(self, **kwargs):
        try:
            from .utils.blaze_converter import convert
            return convert(self.list,**kwargs)
        except ImportError:
            raise ImportError('The packages libdynd, dynd-python, datashape, '
                               'odo/into must be installed to convert data ' )

    def shelve(self, filename, key='results'):
        import shelve
        db = shelve.open(filename)
        db[key] = self
        db.close()

    @classmethod
    def from_shelve(cls, filename, key='results'):
        import shelve
        db = shelve.open(filename)
        out = db[key]
        db.close()
        return out



def get_anybodycon_path():
    """  Return the path to default AnyBody console application
    """
    try:
        import winreg
    except ImportError:
        import _winreg as winreg
    try:
        abpath = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                        'AnyBody.AnyScript\shell\open\command')
    except WindowsError:
        raise WindowsError('Could not locate AnyBody in registry')
    abpath = abpath.rsplit(' ',1)[0].strip('"')
    return os.path.join(os.path.dirname(abpath),'AnyBodyCon.exe')


def define2str(key,value=None):
    if isinstance(value, string_types):
        if value.startswith('"') and value.endswith('"'):
            defstr = '-def %s=---"\\"%s\\""'% (key, value[1:-1].replace('\\','\\\\'))
        else:
            defstr = '-def %s="%s"'% (key, value)
    elif value is None:
        defstr = '-def %s=""'% (key)
    elif isinstance(value,float) :
        defstr =  '-def %s="%g"'% (key, value)
    else:
        defstr = '-def %s="%d"'% (key, value)
    return defstr

def path2str(key,path='.'):
    return '-p %s=---"%s"'% (key, path.replace('\\','\\\\'))


def getsubdirs(toppath, search_string = "."):
    """ Find all directories below a given top path.

    Args:
        toppath: top directory when searching for sub directories
        search_string: Limit to directories matching the this regular expression
    Returns:
        List of directories
    """
    if not search_string:
        return [toppath]
    reg_prog = re.compile(search_string)
    dirlist = []
    if search_string == ".":
        dirlist.append(toppath)
    for root, dirs, files in os.walk(toppath):
        for fname in files:
            if reg_prog.search(os.path.join(root,fname)):
                dirlist.append(root)
                continue
    uniqueList = []
    for value in dirlist:
        if value not in uniqueList:
            uniqueList.append(value)
    return uniqueList



def array2anyscript(arr):
    """ Format a numpy array as an anyscript variable
    """
    def tostr(v):
        if np.isreal(v):
            return '{:.12g}'.format(v)
        elif isinstance(v, (string_types, np.str_)):
            return '"{}"'.format(v)

    def createsubarr(arr):
        outstr = ""
        if isinstance(arr, np.ndarray):
            if len(arr) == 1 and not isinstance(arr[0], np.ndarray):
                return '{'+tostr(arr[0]) + '},'
            outstr += '{'
            for row in arr:
                outstr += createsubarr(row)
            outstr = outstr.strip(',') + '},'
            return outstr
        else:
            return outstr + tostr(arr)+','
    if isinstance(arr, np.ndarray) and not arr.shape:
        return tostr(arr.tolist())
    elif isinstance(arr, np.ndarray) :
        return createsubarr(arr).strip(',')
    elif isinstance( arr, float):
        return tostr(arr)
    else:
        return str(arr)

class AnyPyProcessOutput(collections.OrderedDict):
    """Subclassed OrderedDict which supports partial key access"""
    def __getitem__(self,  key ):
        try:
            return super(AnyPyProcessOutput,self).__getitem__(key)
        except KeyError:
            first_key_match = get_first_key_match(key,
                                              super(AnyPyProcessOutput,self).keys())
            return super(AnyPyProcessOutput,self).__getitem__(first_key_match)

    def _repr_gen(self,prefix):
        items = self.items()
        if not items:
            yield prefix + '{}'
            return

        indent = prefix + '{'
        for i, (key,val) in enumerate(items):
            if i == len(self.keys())-1:
                end = '}'
            else:
                end = ','
            key_str = "'"+key+"'" + ': '
            val_str = _pprint.pformat(val)
            if len(prefix) + len(key_str) + len(val_str) < 80:
                yield indent + key_str + val_str + end
            else:
                yield indent + key_str
                indent = prefix + '   '
                for l in val_str.split('\n'):
                   yield indent + l if l.endswith(',') else indent + l + end
            indent = prefix + ' '



    def __repr__(self, _repr_running={}, prefix = '' ):
        call_key = id(self), _get_ident()
        if _repr_running is None:
            _repr_running = {}
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if self is None:
                return '%s()' % (self.__class__.__name__,)
            return '\n'.join(self._repr_gen(prefix))
        finally:
            del _repr_running[call_key]


dump_pattern = re.compile(r'Main.*=.*;$')

def parse_anybodycon_output(strvar, errors_to_ignore=None,
                            warnings_to_include = None):
    if errors_to_ignore is None:
        errors_to_ignore = []
    if warnings_to_include is None:
        warnings_to_include = []

    out = AnyPyProcessOutput(  );
    out['ERROR'] = []
    out['WARNING'] = []

    dump_path = None
    for line in strvar.splitlines():
        if '#### Macro command' in line and "Dump" in line:
            me = re.search('Main[^ \"]*', line)
            if me:
                dump_path = me.group(0)
        if dump_pattern.match(line):
            (first, last) = line.split('=',1)
            last = last.strip(' ;')
            var_name = first.strip()
            value_str = last
            if value_str.startswith('{') and value_str.endswith('}'):
                value_str = value_str.replace('{','[').replace('}',']')
            if dump_path:
                var_name = dump_path
                dump_path = None
            try:
                out[var_name.strip()] = literal_eval(value_str)
            except (SyntaxError, ValueError):
                if value_str == '[...]': value_str = '...'
                value_str, nrep = re.subn(r'([^\[\]",\s]+)', r"'''\1'''", value_str)
                if value_str == '': value_str = 'None'
                if value_str.startswith('"') and value_str.endswith('"'):
                    value_str = "'''" + value_str[1:-1] + r"'''"
                try:
                    out[var_name.strip()] = literal_eval(value_str)
                except (SyntaxError, ValueError):
                    out[var_name.strip()] = last
                    warnings.warn('\n\nCould not parse console output:\n'+ line)
        line_has_errors = (line.startswith('ERROR') or line.startswith('Error') or
                           line.startswith('Model loading skipped'))
        if line_has_errors:
            for err_str in errors_to_ignore:
                if err_str in line: break
            else:
                # This is run if we never break,
                #i.e. err was not in the list of errors_to_ignore
                out['ERROR'].append(line)
        line_has_warning = line.startswith(('WARNING','Failed'))
        if line_has_warning:
            for warn_str in warnings_to_include:
                if warn_str in line:
                    out['WARNING'].append(line)
                    break
    # Convert all list object to numpy arrays
    for k,v in out.items():
        if isinstance(v,list):
            out[k] = np.array(v)

    # Move 'ERROR' and 'WARNING' entry to the last position in the ordered dict
    out['WARNING'] = out.pop('WARNING').tolist()
    out['ERROR'] = out.pop('ERROR').tolist()

    # Remove the ERROR/WARNING key if it does not have any entries
    if len(out['ERROR']) == 0:
        del out['ERROR']
    if len(out['WARNING']) == 0:
        del out['WARNING']
    return out



def get_ncpu():
    """ Return the number of CPUs in the computer
    """
    from multiprocessing import cpu_count
    return cpu_count()


def silentremove(filename):
    """ Removes a file ignoring cases where the file does not exits.  """
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:  # errno.ENOENT : no such file or directory
            logging.debug('Error removing file: ' + filename)
            raise  # re-raise exception if a different error occured



def _run_from_ipython():
    """ Return True if run from IPython
    """
    try:
         __IPYTHON__
         return True
    except NameError:
        return False


def make_hash(o):

  """
  Makes a hash from a dictionary, list, tuple or set to any level, that contains
  only other hashable types (including any lists, tuples, sets, and
  dictionaries).
  http://stackoverflow.com/questions/5884066/hashing-a-python-dictionary
  """

  if isinstance(o, (set, tuple, list)):

    return hash( tuple([make_hash(e) for e in o]) )

  elif not isinstance(o, dict):

    return hash(o)

  new_o = copy.deepcopy(o)
  for k, v in new_o.items():
    new_o[k] = make_hash(v)

  return hash(tuple(frozenset(sorted(new_o.items()))))


_BM_CONSTANTS = {
'ON': '1',
'OFF': '0',
'CONST_MUSCLES_NONE': '0',
'CONST_MUSCLES_SIMPLE': '1',
'CONST_MUSCLES_3E_HILL': '2',
'CONST_HAND_SIMPLE': '0',
'CONST_HAND_DETAILED': '1',
'CONST_LEG_MODEL_OFF': '"OFF"',
'CONST_LEG_MODEL_Leg': '"Leg"',
'CONST_LEG_MODEL_TLEM': '"TLEM"',
'CONST_MORPH_NONE': '0',
'CONST_MORPH_TRUNK_TO_LEG': '1',
'CONST_MORPH_LEG_TO_TRUNK': '2',
'CONST_PELVIS_DISPLAY_NONE': '0',
'CONST_PELVIS_DISPLAY_LEGPELVIS_ONLY': '1',
'CONST_PELVIS_DISPLAY_LEGANDTRUNKPELVIS': '2',
'CONST_SCALING_CUSTOM': '-1',
'CONST_SCALING_STANDARD': '0',
'CONST_SCALING_UNIFORM': '1',
'CONST_SCALING_LENGTHMASS': '2',
'CONST_SCALING_LENGTHMASSFAT': '3',
'CONST_SCALING_UNIFORM_EXTMEASUREMENTS': '4',
'CONST_SCALING_LENGTHMASS_EXTMEASUREMENTS': '5',
'CONST_SCALING_LENGTHMASSFAT_EXTMEASUREMENTS': '6',
'CONST_SCALING_LENGTHMASSFAT_MULTIDOFS': '7',
}

def replace_bm_constants(d):
    for k, v in d.items():
        if v in _BM_CONSTANTS:
            d[k] = _BM_CONSTANTS[v]
    return d
