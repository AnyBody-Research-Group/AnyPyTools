# -*- coding: utf-8 -*-
"""
Created on Sun Sep  7 13:25:38 2014

@author: Morten
"""

from __future__ import division, absolute_import, print_function, unicode_literals
try:
    from .py3k import * # @UnusedWildImport
except (ValueError, SystemError):
    from py3k import *  # @UnusedWildImport

import os
import numpy as np
import copy
from collections import OrderedDict
from ast import literal_eval
import collections

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
    if isinstance(arr, np.ndarray) :
        return createsubarr(arr).strip(',')
    elif isinstance( arr, float):
        return tostr(arr)
    else:
        return str(arr)

def _parse_anybodycon_output(strvar):
    out = OrderedDict();
    dump_path = None
    for line in strvar.splitlines():
        if line.count('#### Macro command') and line.count('"Dump"'):
            me = re.search('Main[^ \"]*', line)
            if me is not None :
                dump_path = me.group(0)
        if line.endswith(';') and line.count('=') == 1:
            (first, last) = line.split('=')
            first = first.strip()
            last = last.strip(' ;').replace('{','[').replace('}',']')
            if dump_path is not None:
                first = dump_path
                dump_path = None
            try:
                out[first.strip()] = np.array(literal_eval(last))
            except SyntaxError:
                pass

        if ( line.startswith('ERROR') or
             line.startswith('Error') or 
             line.startswith('Model loading skipped')) : 
            if 'ERROR' not in out:
                out['ERROR'] = []
            out['ERROR'].append(line)
    return out
    
    
def get_anybodycon_path():
    """  Return the path to default AnyBody console application 
    """
    try: 
        import winreg
    except ImportError:
        import _winreg as winreg
    
    abpath = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT,
                    'AnyBody.AnyScript\shell\open\command')
    abpath = abpath.rsplit(' ',1)[0].strip('"')
    return os.path.join(os.path.dirname(abpath),'AnyBodyCon.exe')

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
