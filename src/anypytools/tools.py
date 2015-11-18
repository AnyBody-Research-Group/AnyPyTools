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
import copy
import errno
import pprint as _pprint
import logging
import warnings
import functools
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
        if line.endswith(';') and line.count('=') == 1:
            (first, last) = line.split('=')
            first = first.strip()
            last = last.strip(' ;').replace('{','[').replace('}',']')
            if dump_path:
                first = dump_path
                dump_path = None
            try:
                out[first.strip()] = literal_eval(last)
            except (SyntaxError, ValueError):
                if last == '[...]': last = '...'
                last, nrep = re.subn(r'([^\[\],\s]+)', r'"\1"', last)
                if last == '': last = 'None'
                try:
                    out[first.strip()] = literal_eval(last)
                except (SyntaxError, ValueError):
                    print(last)
                    out['ERROR'].append('ERROR parsing console ouput: '+last)

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
    out['WARNING'] = out.pop('WARNING')
    out['ERROR'] = out.pop('ERROR')

    # Remove the ERROR/WARNING key if it does not have any entries
    if not out['ERROR']:
        del out['ERROR']
    if not out['WARNING']:
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
