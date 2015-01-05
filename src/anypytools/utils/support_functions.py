# -*- coding: utf-8 -*-
"""
Created on Sun Sep  7 13:25:38 2014

@author: Morten
"""

from __future__ import division, absolute_import, print_function, unicode_literals
try:
    from .py3k import * # @UnusedWildImport
except (ValueError, SystemError):
    from py3k import * # @UnusedWildImport

import os
import numpy as np
import copy
from collections import OrderedDict



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

def parse_anybodycon_output(strvar):
    """ Parses the AnyBody console ouput and returns a dictionary with data
    """
    out = {};
    full_variable_name = None
    for line in strvar.splitlines():
        if line.count('#### Macro command') and line.count('"Dump"'):
            me = re.search('Main[^ \"]*', line)
            if me is not None :
                full_variable_name = me.group(0)
        if line.endswith(';') and line.count('=') == 1:
            (var_name, var_data) = line.split('=')
            var_name = var_name.strip()
            var_data = var_data.strip(' ;').replace('{','[').replace('}',']')
            if full_variable_name is not None:
                var_name = full_variable_name
                full_variable_name = None
            out[var_name.strip()] = np.array(eval(var_data))
        
        if line.startswith('ERROR') or line.startswith('Error'): 
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
        
def _get_datashape(result_list):
    try: 
        from datashape import discover
        from datashape.coretypes import (Record, var,Option,
                                        int64,string, float64, Fixed)
    except ImportError:
        import warnings
        warnings.warn('blaze and datashape packages must be installed,' 
                      ' to convert data to the blaze format.',
                      ImportWarning)
        raise ImportWarning

    fields = OrderedDict()
    for result in result_list:
        for key in result.keys():
            if key not in fields:
                dshape = discover(result[key])
                if len(dshape) > 1:
                    dshape = var * dshape.subarray(1) 
                else:
                    dshape = dshape
                fields[key] = dshape
    
    def update_fields(key, ds):
        if key in fields:
            del fields[key]
            fields[key] = ds
    
    update_fields('ERROR', var*string )
    update_fields('task_macro_hash',  Fixed(1) *int64 ) 
    update_fields('task_id',   Fixed(1) *int64 )
    update_fields('task_work_dir',  Fixed(1) *string )
    update_fields('task_name',  Fixed(1) *string )
    update_fields('task_processtime', Fixed(1) *float64 )
    update_fields('task_macro', var*string ) 
    
    if not fields:
        return Fixed(len(result_list)) * Option(float64)
    else:
        return ( Fixed(len(result_list)) * 
                 Record( tuple( (k, v) for k, v in fields.items()) ) )
        
        
def convert_to_blaze_data(result_list):
    from blaze import Data
    
    # Remove all '.' in keys
    for result in result_list:
        for key in result.keys():
            if '.' in key:
                result[key.replace('.','_')] = result.pop(key)
                
    datashape = _get_datashape( result_list ) 

    # Create a set of all keys in all results
    fields_set = set()
    for result in result_list:
        fields_set.update( result.keys() ) 
    # Ensure that these keys are present in all results.
    for result in result_list:
        for field in fields_set:
            if field not in result:
                result[field] = []
    # If there are no keys, just make the result a list of 
    # None instead of list empty dicts
    
    if not fields_set:
        return None
    
    return  Data(result_list, dshape = datashape)  
    
    
    
    
    
    
        
        
        
def make_hash(o):

  """
  Makes a hash from a dictionary, list, tuple or set to any level, that contains
  only other hashable types (including any lists, tuples, sets, and
  dictionaries).
  http://stackoverflow.com/questions/5884066/hashing-a-python-dictionary
  """

  if isinstance(o, (set, tuple, list)):

    return tuple([make_hash(e) for e in o])    

  elif not isinstance(o, dict):

    return hash(o)

  new_o = copy.deepcopy(o)
  for k, v in new_o.items():
    new_o[k] = make_hash(v)

  return hash(tuple(frozenset(sorted(new_o.items()))))
