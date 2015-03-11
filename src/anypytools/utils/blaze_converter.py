# -*- coding: utf-8 -*-
"""
Created on Sun Sep  7 13:25:38 2014

@author: Morten
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *

import numpy as np
from copy import deepcopy
import collections
import logging

from datashape import discover
from datashape.coretypes import (Record, var,Option)
try: 
    from odo import convert 
except ImportError:
    from into import convert
    
from dynd import nd



from ..utils import AnyPyProcessOutputList
logger = logging.getLogger('abt.anypytools')


@convert.register(nd.array, AnyPyProcessOutputList, cost=1.0)
def convert(res, **kwargs):
    prepared_data, ds = convert_and_extract_dshape(res, **kwargs)
    return nd.array(prepared_data, dtype=str(ds))


def convert_to_nested_structure(obj):
    assert isinstance(obj, collections.Mapping)
    for key in obj:
        if '.' in key:
            first, last = key.split('.', 1)
            if first not in obj:
                obj[first] = collections.OrderedDict()
            obj[first][last] = obj.pop(key)
            convert_to_nested_structure(obj[first])

def remove_dots_in_key_names(obj):    
    assert isinstance(obj, collections.Mapping)
    for key in list( obj.keys() ):
        obj[key.replace('.','_')] = obj.pop(key)

def convert_items_to_python_types(obj):
    assert isinstance(obj, collections.Mapping)
    for k in obj:
        if isinstance(obj[k], collections.Mapping):
            convert_items_to_python_types(obj[k])
        else:
            if isinstance(obj[k], np.ndarray):
                obj[k] = obj.pop(k).tolist()
            if not obj[k] and isinstance(obj[k], collections.Iterable):
                obj[k] = None

def update_dict_if(d, u, condition = True ):
    """ Update one nested dictionary 'd' with the keys from another 'u'
        If the keys already exist, then values are only if condition
        function returns true
    """       
    if condition is True:
        condition = lambda old_val, new_val: True
    elif condition is False:
        condition = lambda old_val, new_val: False
    for k in u:
        if isinstance(u[k], collections.Mapping):
            r = update_dict_if(d.get(k, {}), u[k], condition)
            d[k] = r
        elif k in d:
            if condition(d[k], u[k]):
                d[k] = u[k]
        else:
            d[k] = u[k]
    return d        


def build_datashape(sample_data):
    """ Build a datashape from sample_data 
        In case of multiple dimensions, the firt is replace by 'var' to 
        handle varing time samples in models
    """
    if isinstance(sample_data, collections.Mapping):
        return Record((k,build_datashape(v)) for k,v in sample_data.items() )
    else:
        ds = discover(sample_data)
        if len(ds) > 1:
            ds = var *  ds.subarray(1)
        else:
            ds = Option( ds )
        return ds

def clean_sample(mapping, key):
    """ Scrubs the values of a nested data structure, leaving the prototype
        empty values. List are replaced by [] and values by None """
    if isinstance(mapping[key], collections.Mapping):
        for subkey in mapping[key]:
            clean_sample(mapping[key], subkey)
    elif isinstance(mapping[key], collections.Iterable):
        mapping[key] = []
    else:
        mapping[key] = None



def convert_and_extract_dshape(result_list, create_nested_structure = False, **kwargs):

    result_list = deepcopy(result_list)
    
    if create_nested_structure:
        for elem in result_list:
            convert_to_nested_structure(elem)
    else:
        for elem in result_list:
            #pass            
            remove_dots_in_key_names(elem)
                        
    for elem in result_list:
        convert_items_to_python_types(elem)



    def update_check(old_value, new_value):
        if isinstance(old_value, collections.Iterable):
            if not any(old_value):
                return True
        elif not old_value:
            return True
        else: 
            return False

    # Create a sample data structure with the keys from all the results.         
    sample_data = collections.OrderedDict()
    for data_structure in result_list:
        update_dict_if(sample_data, data_structure, update_check)
    
    # If some task info is present set this data so the discover function
    # will always find the correct data type. 
    if 'task_id' in sample_data:
        sample_data['task_macro_hash'] = 42
        sample_data['task_id'] = 42
        sample_data['task_work_dir'] = "string"
        sample_data['task_name'] = "string"
        sample_data['task_processtime'] = 10.1
        sample_data['task_macro'] = ['string', 'string']
        sample_data['task_logfile'] = 'string'
        
        
    
    dshape = build_datashape(sample_data)        
        
      
    
    empty_sample_data = deepcopy( sample_data )
    for key in sample_data:
        clean_sample(empty_sample_data, key)
        
        
    for elem in result_list:
        ## Update_dict_if( ) with a always False condition, will
        ## only add missing keys
        update_dict_if(elem, empty_sample_data, condition=False)        
        
        
    
    return (result_list, dshape)  





#
#def convert_data(result_list, create_nested_structure = True):
#
#    result_list = deepcopy(result_list)
#    def convert_to_nested_structure(obj):
#        assert isinstance(obj, collections.Mapping)
#        for key in obj:
#            if '.' in key:
#                first, last = key.split('.', 1)
#                if first not in obj:
#                    obj[first] = OrderedDict()
#                obj[first][last] = obj.pop(key)
#                convert_to_nested_structure(obj[first])
#    
#    def remove_dots_in_key_names(obj):    
#        assert isinstance(obj, collections.Mapping)
#        for key in list( obj.keys() ):
#            obj[key.replace('.','_')] = obj.pop(key)
#    
#    
#    if create_nested_structure:
#        for elem in result_list:
#            convert_to_nested_structure(elem)
#    else:
#        for elem in result_list:
#            remove_dots_in_key_names(elem)
#                      
#        
#    def convert_items_to_python_types(obj):
#        assert isinstance(obj, collections.Mapping)
#        for k in obj:
#            if isinstance(obj[k], collections.Mapping):
#                convert_items_to_python_types(obj[k])
#            else:
#                if isinstance(obj[k], np.ndarray):
#                    obj[k] = obj.pop(k).tolist()
#                if not obj[k] and isinstance(obj[k], collections.Iterable):
#                    obj[k] = None
#    
#    for elem in result_list:
#        convert_items_to_python_types(elem)
#    
#        
#        
#    def update_dict_if(d, u, condition = None ):
#        """ Update one nested dictionary 'd' with the keys from another 'u'
#            If the keys already exist, then values are only if condition
#            function returns true
#        """       
#        if not condition:
#            condition = lambda old_val, new_val: True
#        for k in u:
#            if isinstance(u[k], collections.Mapping):
#                r = update_dict_if(d.get(k, {}), u[k], condition)
#                d[k] = r
#            elif k in d:
#                if condition(d[k], u[k]):
#                    d[k] = u[k]
#            else:
#                d[k] = u[k]
#        return d        
#        
#        
#    def update_check(old_value, new_value):
#        if isinstance(old_value, collections.Iterable):
#            if not any(old_value):
#                return True
#        elif not old_value:
#            return True
#        else: 
#            return False
#
#    # Create a sample data structure with the keys from all the results.         
#    sample_data = collections.OrderedDict()
#    for data_structure in result_list:
#        update_dict_if(sample_data, data_structure, update_check)
#    
#    # If some task info is present set this data so the discover function
#    # will always find the correct data type. 
#    if 'task_id' in sample_data:
#        sample_data['task_macro_hash'] = 42
#        sample_data['task_id'] = 42
#        sample_data['task_work_dir'] = "string"
#        sample_data['task_name'] = "string"
#        sample_data['task_processtime'] = 10.1
#        sample_data['task_macro'] = ['string', 'string']
#        sample_data['task_logfile'] = 'string'
#        
#        
#    def build_datashape(sample_data):
#        """ Build a datashape from sample_data 
#            In case of multiple dimensions, the firt is replace by 'var' to 
#            handle varing time samples in models
#        """
#        if isinstance(sample_data, collections.Mapping):
#            return Record((k,build_datashape(v)) for k,v in sample_data.items() )
#        else:
#            ds = discover(sample_data)
#            if len(ds) > 1:
#                ds = var *  ds.subarray(1)
#            else:
#                ds = Option( ds )
#            return ds
#    
#    dshape = build_datashape(sample_data)        
#        
#      
#    def clean_sample(mapping, key):
#        """ Scrubs the values of a nested data structure, leaving the prototype
#            empty values. List are replaced by [] and values by None """
#        if isinstance(mapping[key], collections.Mapping):
#            for subkey in mapping[key]:
#                clean_sample(mapping[key], subkey)
#        elif isinstance(mapping[key], collections.Iterable):
#            mapping[key] = []
#        else:
#            mapping[key] = None
#    
#    empty_sample_data = deepcopy( sample_data )
#    for key in sample_data:
#        clean_sample(empty_sample_data, key)
#        
#        
#    for elem in result_list:
#        ## Update_dict_if( ) with a always False condition, will
#        ## only add missing keys
#        update_dict_if(elem, empty_sample_data, condition=lambda x,y:False)        
#        
#        
#    
#    return Data(result_list, dshape = dshape)  
#        
        
