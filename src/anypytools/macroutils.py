# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 21:14:59 2012

@author: Morten
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *
from collections import MutableSequence
import logging

from past.builtins import basestring as string_types


from .utils import define2str, path2str, array2anyscript,pprint
from .utils import Py3kPrettyPrinter

#pprint is used in the doc tests

import sys
from scipy.stats import distributions
if sys.platform.startswith("win"):
    # This is a horrible hack to work around a bug in
    # scipy http://stackoverflow.com/questions/15457786/ctrl-c-crashes-python-after-importing-scipy-stats
    try:
        import thread #, imp, ctypes, os
    except ImportError:
        import _thread as thread 
    import win32api
    def handler(sig, hook=thread.interrupt_main):
        hook()
        return 1
    win32api.SetConsoleCtrlHandler(handler, 1)



import numpy as np
from numpy.random import random, seed

    
from types import GeneratorType
logger = logging.getLogger('abt.anypytools')


def _isgenerator(x):
    return isinstance(x, types.GeneratorType)

class MacroCommand(object):
    def __init__(self, command):
        if not isinstance(command, list):
            self.cmd  = [ command ]
        else: 
            self.cmd = command
            
    def __repr__(self):
        return str( type(self) )
            
    def get_macro(self, index):            
        return '\n'.join(self.cmd)

class Load(MacroCommand):
    def __init__(self, filename, defs = {}, paths = {}):
        self.filename = filename
        self.defs = defs
        self.paths = paths
        
    def get_macro(self, index):
        cmd = ['load "{}"'.format(self.filename)]

        for key in sorted(self.defs):
            value = self.defs[key]
            cmd.append( define2str(key, value) )
        for key in sorted(self.paths):
            value = self.paths[key]
            cmd.append( path2str(key, value))
        
        return ' '.join(cmd)
        
class SetValue(MacroCommand):
    def __init__(self, var, value):
        self.var = var
        self.value = value
        
    def get_macro(self, index):
        if isinstance(self.value, list):
            val = self.value[index % len(self.value)]
        else:
            val = self.value
        
        if isinstance(val, np.ndarray):
            val = array2anyscript(val)
        elif isinstance(val, float):
            val = '{:.12g}'.format(val)
        elif isinstance(val, int):
            val = '{:d}'.format(val)
        
        return 'classoperation {0} "Set Value" --value="{1}"'.format(self.var,val) 

class Dump(MacroCommand):
    def __init__(self, var):
        if not isinstance(var, list):
            self.var_list = [var]
        else:
            self.var_list = var

    def get_macro(self, index):
        cmd = []
        for var in self.var_list:
            cmd.append('classoperation {0} "Dump"'.format(var) )
        return '\n'.join(cmd)


class SaveDesign(MacroCommand):
    def __init__(self, operation, filename):
        self.filename = filename
        self.operation = operation
        
    def get_macro(self, index):
        return 'classoperation {} "Save design" --file="{}"'.format(self.operation, 
                                                                    self.filename)

class LoadDesign(MacroCommand):
    def __init__(self, operation, filename):
        self.filename = filename
        self.operation = operation
     
    def get_macro(self, index):
        return 'classoperation {} "Load design" --file="{}"'.format(self.operation, 
                                                                    self.filename)

class SaveValues(MacroCommand):
    def __init__(self, filename):
        self.filename = filename
    def get_macro(self, index):
        return 'classoperation Main "Save Values" --file="{}"'.format(self.filename)

class LoadValues(MacroCommand):
    def __init__(self, filename):
        self.filename = filename
    
    def get_macro(self, index):
        return 'classoperation Main "Load Values" --file="{}"'.format(self.filename)


class UpdateValues(MacroCommand):
    def __init__(self):
        pass
    
    def get_macro(self, index):
        return 'classoperation Main "Update Values"'


class OperationRun(MacroCommand):
    def __init__(self, operation):
        self.operation = operation
    
    def get_macro(self, index):
        return 'operation {}'.format(self.operation) + '\n' + 'run'



class Macros(MutableSequence):
    """ Macros(*macro_commands, number_of_macros = 1, counter_token = None )  

    Overview
    ----------
    Use the class to build an AnyScript macro. The class have methods for all
    anyscript opertions, and makes it easier to construct a macro with the 
    correct syntax. 
    
    For example:
    
    >>> mcr = Macros(number_of_macros = 10)
    >>> mcr.add( Load('c:/MyModel/model.main.any', defs = {}, paths = {} ) )
    >>> mcr.add( SetValue('Main.myvar', 12.3)  )
    >>> mcr.extend( [RunOperation('Main.Study.Kinematics'), 
                     Dump('Main.Study.Output.MyVar') ] )
    >>> print( mcr )
    [['load "c:/MyModel/model.main.any"',
      'classoperation Main.Study.myvar "Set Value" --value="12.3"',
      'operation Main.Study.Kinematics',
      'run',
      'classoperation Main.Study.Output.MyVar "Dump"']]
            
             
    Parameters
    ----------
    number_of_macros: int
        The number of macros to generate.
    counter_token: string
        A token in the macro commands that will be replace with a counter. If
        the token is '{ID}' then all occurences of '{ID}' in the macros will be
        replaced with a counter. 
    
        
    Returns
    -------
    A Macro object: 
        A Macro object for constructing the macro.       
    """    
    def __init__(self,  *args, **kwargs):# number_of_macros=1, counter_token = None ):
        super(Macros,self).__init__()
        if len(args) == 0:
            self._list = list()
        else: 
            if len(args) == 1 and isinstance(args[0], list):
                args = args[0]
            for arg in args:
                if not isinstance(arg, MacroCommand):
                    raise ValueError('Argument must be valid macro command classes')
            self._list = list(args)
        
        
        
        self.number_of_macros = kwargs.pop("number_of_macros", 1)
        assert(self.number_of_macros > 0)

        self._counter_token = kwargs.pop("counter_token", None)
       
    def __len__(self):
        return len(self._list)
    
    def __getitem__(self, ii):
        return self._list[ii]

    def __delitem__(self, ii):
        del self._list[ii]

    def __setitem__(self, ii, val):
        self._list[ii] = val
        return self._list[ii]

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        printer = Py3kPrettyPrinter(width = 80)
        return printer.pformat( self.tolist() )

    def insert(self, ii, val):
        self._list.insert(ii, val)

    def append(self, val):
        list_idx = len(self._list)
        self.insert(list_idx, val)

    def tolist(self):
        macro_list = []
        for macro_idx in range(self.number_of_macros):
            macro = []
            for elem in self:
                mcr = elem.get_macro(macro_idx)
                if self._counter_token:
                    mcr = mcr.replace(self._counter_token, str(macro_idx))
                macro.extend(mcr.split('\n')  )
            macro_list.append(macro)
        return macro_list
        



    
if __name__ == '__main__':
    
#    mg = PertubationMacroGenerator()
#    mg.add_set_value_designvar('test',1)
#    mg.add_set_value_designvar('test',2)
#
#    pprint(mg.generate_macros())
#    
    import pytest
    pytest.main(str('generate_macros.py --doctest-modules'))

