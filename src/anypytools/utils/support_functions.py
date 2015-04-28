# -*- coding: utf-8 -*-
"""
Created on Sun Sep  7 13:25:38 2014

@author: Morten
"""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *
from past.builtins import basestring as string_types


import os
import numpy as np
import copy
from ast import literal_eval
import pprint
import collections
import re
import logging
import warnings


logger = logging.getLogger('abt.anypytools')

string_types =  (str, bytes)


# This hacks pprint to always return strings witout u' prefix 
# important when running doctest in both python 2 og python 3
import pprint as _pprint
class MyPrettyPrinter(_pprint.PrettyPrinter):
    def format(self, object, context, maxlevels, level):
        try:
            if isinstance(object, unicode):
                rep = u"'"  + object + u"'"
                return ( rep.encode('utf8'), True, False)
        except NameError:
            pass
        return _pprint.PrettyPrinter.format(self, object, context, maxlevels, level)

def py3k_pprint(s):
    printer = MyPrettyPrinter(width = 110)
    printer.pprint(s)

pprint = py3k_pprint


class AnyPyProcessOutputList(list):
    def __repr__(self):
        rep =  _pprint.pformat([dict(l) for l in self])
        if rep.count('\n') > 50:
            rep = ( "\n".join(rep.split('\n')[:20]) 
                    + "\n\n...\n\n" + 
                    "\n".join(rep.split('\n')[-20:]) )
        return rep
    
    def __getitem__(self,index):
        if isinstance(index, string_types):
            # Find the entries where index matches the keys
            matching = [s for s in self[0] if index in s]
            if matching:
                if len(matching) > 1: 
                    warnings.warn("Key is not unique. Returning first match")
                # Return the stacked data for the first match found 
                try: 
                    return np.row_stack( (elem[matching[0]] for elem in self))
                except ValueError:
                    # if the array is ragged try to assemble it as an array of objects
                    return np.array([elem[matching[0]] for elem in self])
            else:
                raise KeyError('Could not find key in the data')
            return np.row_stack( (elem[key] for elem in self))
        else:
            return super(AnyPyProcessOutputList, self).__getitem__(index)

    def to_dynd(self, **kwargs):
        try:
            from .blaze_converter import convert
            return convert(self,**kwargs)
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

def parse_anybodycon_output(strvar, errors_to_ignore = [] ):
    out = collections.OrderedDict(  );
    out['ERROR'] = []
    
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
                out[first.strip()] = np.array(literal_eval(last))
            except SyntaxError as e:
                out['ERROR'].append(str(e))

        line_has_errors = (line.startswith('ERROR') or line.startswith('Error') or 
                           line.startswith('Model loading skipped'))             
        if line_has_errors : 
            for err_str in errors_to_ignore:
                if err_str in line: break
            else:
                # This is run if we never break,
                #i.e. err was not in the list of errors_to_ignore
                out['ERROR'].append(line)
    
    # Move 'ERROR' entry to the last position in the ordered dict
    out['ERROR'] = out.pop('ERROR')
    
    # Remove the ERROR key if it does not have any error entries        
    if not out['ERROR']:
        del out['ERROR']

    return out
    
    

def get_ncpu():
    """ Return the number of CPUs in the computer 
    """
    from multiprocessing import cpu_count
    return cpu_count()

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
