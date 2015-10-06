# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 21:14:59 2012

@author: Morten
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *

import logging

from past.builtins import basestring as string_types


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

#pprint is used in the doc tests
from .tools import pprint, array2anyscript


from types import GeneratorType
logger = logging.getLogger('abt.anypytools')


def _isgenerator(x):
    return isinstance(x, types.GeneratorType)

class MacroGenerator(object):
    """ Base class for generating AnyScript macros

    Overview
    ----------
    Use the class to build an AnyScript macro. The class have methods for all
    anyscript opertions, and makes it easier to construct a macro with the
    correct syntax.

    For example:

    >>> mg = MacroGenerator()
    >>> mg.add_load('c:/MyModel/model.main.any')
    >>> mg.add_set_value('Main.Study.myvar', 12.3)
    >>> mg.add_run_operation('Main.Study.Kinematics')
    >>> pprint( mg.generate_macros() )
    [['load "c:/MyModel/model.main.any"',
      'classoperation Main.Study.myvar "Set Value" --value="12.3"',
      'operation Main.Study.Kinematics',
      'run']]

    If more than one macro is generated the class can construct a python
    generator object which builds the macro (lazily) as they are requested.


    Parameters
    ----------
    number_of_macros: int
        The number of macros to generate.
    counter_token: string
        A token in the macro commands that will be replace with a counter. If
        the token is '{ID}' then all occurences of '{ID}' in the macros will be
        replaced with a counter.
    reset_counter_for_each_batch: Bool
        Specifies if the macro counter is reset if macros are generated in batch
        mode.


    Returns
    -------
    A MacroGenerator object:
        A MacroGenerator object for constructing the macro.
    """
    def __init__(self, number_of_macros=1, counter_token = None,
                 reset_counter_for_each_batch = True):
        assert(number_of_macros > 0)
        self._macro_cmd_list = []
        self.number_of_macros = number_of_macros
        self._counter_token = counter_token
        self._new_batch_resets_counter = reset_counter_for_each_batch
        self.cached_output = None

    def add_macro(self,macro):
        """ Add macro code to the generated macro.

        Parameters
        ----------
        macro:
            A anyscript macro command or a list of anyscript commands


        Examples:
        ---------
            add a single macro command:

            >>> mg = MacroGenerator()
            >>> mg.add_macro('load "model1.any"')

            add several macro commands:

            >>> mg.add_macro(['operation Main.RunApplication', 'run', 'exit'])


        """
        if not isinstance(macro,list):
            macro = [macro]
        for macro_cmd in macro:
            self._macro_cmd_list.append(macro_cmd)

    def add_set_value(self,variable, value):
        """ Add a 'Set Value' macro command where the value is the same in all
        macros.

        Parameters
        ----------
        variable:
            An AnyScript variable or a list of AnyScript variables.
        value:
            A Values assign to the AnyScript variable or a list of values.

        Examples:
        ---------
            Set a single value:

            >>> mg = MacroGenerator()
            >>> mg.add_load('c:/MyModel/model.main.any')
            >>> mg.add_set_value('Main.Study.myvar1', 23.1)
            >>> mg.add_set_value('Main.Study.myvar2', np.array([2,3,4]))
            >>> mg.add_run_operation('Main.Study.Kinematics')
            >>> pprint( mg.generate_macros() )
            [['load "c:/MyModel/model.main.any"',
              'classoperation Main.Study.myvar1 "Set Value" --value="23.1"',
              'classoperation Main.Study.myvar2 "Set Value" --value="{2,3,4}"',
              'operation Main.Study.Kinematics',
              'run']]

            Set variable across different macros

            >>> mg = MacroGenerator(number_of_macros = 3)
            >>> mg.add_load('c:/MyModel/model.main.any')
            >>> mg.add_set_value('Main.Study.myvar1',[1,2,3])
            >>> pprint( mg.generate_macros() )
            [['load "c:/MyModel/model.main.any"', 'classoperation Main.Study.myvar1 "Set Value" --value="1"'],
             ['load "c:/MyModel/model.main.any"', 'classoperation Main.Study.myvar1 "Set Value" --value="2"'],
             ['load "c:/MyModel/model.main.any"', 'classoperation Main.Study.myvar1 "Set Value" --value="3"']]

            The method can also add several macro commands if both variable and
            value are list of the same length

            >>> mg = MacroGenerator()
            >>> mg.add_set_value(['Main.Study.myvar1','Main.Study.myvar1'],[4, 23])
            >>> pprint( mg.generate_macros())
            [['classoperation Main.Study.myvar1 "Set Value" --value="4"',
              'classoperation Main.Study.myvar1 "Set Value" --value="23"']]

        """

        if isinstance(variable,list) and isinstance(value,list):
            if len(variable) != len(value):
                raise ValueError('Lists must be the same length')
            for k,v in zip(variable,value):
                self.add_macro(self._create_set_value_cmd(k,v))

        elif isinstance(variable, string_types) and isinstance(value,list):
            if len(value) != self.number_of_macros:
                raise ValueError("If 'value' is a list it must be the same length\
                                  as the number of macros")
            macro_generator = self._generator_set_value(variable, value)
            self.add_macro(macro_generator)

        else:
            self.add_macro(self._create_set_value_cmd(variable,value))

    def add_set_value_range(self, var, start, stop, endpoint = True ) :
        """ Add a 'Set Value' macro command where the values changes across all
        generated macros. Th values will be evenly spaced over a specified interval.
        Requires that the GenerateMacro object is set to generate more than
        one macro.

        Parameters
        ----------
        start: scalar or array
            The starting value of the sequence.
        stop: scalar or array
            The end value of the sequence, unless endpoint is set to False.
            In that case, the sequence consists of all but the last of num + 1
            evenly spaced samples, so that stop is excluded. Note that the
            step size changes when endpoint is False.
        endpoint: bool, optional
            If True, stop is the last sample. Otherwise, it is not included.
            Default is True.

        Examples:
        ---------
            Set a single value:

            >>> mg = MacroGenerator(number_of_macros = 10)
            >>> mg.add_set_value_range('Main.Study.myvar1', start= 10, stop=100)
            >>> pprint( mg.generate_macros() )
            [['classoperation Main.Study.myvar1 "Set Value" --value="10"'],
             ['classoperation Main.Study.myvar1 "Set Value" --value="20"'],
             ['classoperation Main.Study.myvar1 "Set Value" --value="30"'],
             ['classoperation Main.Study.myvar1 "Set Value" --value="40"'],
             ['classoperation Main.Study.myvar1 "Set Value" --value="50"'],
             ['classoperation Main.Study.myvar1 "Set Value" --value="60"'],
             ['classoperation Main.Study.myvar1 "Set Value" --value="70"'],
             ['classoperation Main.Study.myvar1 "Set Value" --value="80"'],
             ['classoperation Main.Study.myvar1 "Set Value" --value="90"'],
             ['classoperation Main.Study.myvar1 "Set Value" --value="100"']]

        """
        no = self.number_of_macros
        if isinstance(start, np.ndarray):
            assert start.shape == stop.shape, 'Start and stop must be similar'
            valuelist = []
            for start_val, stop_val in zip(start.flatten(), stop.flatten() ):
                arr = np.linspace(start_val,stop_val, self.number_of_macros, endpoint)
                valuelist.append(arr)
            valuelist = np.array(valuelist).T

            valuelist = [subarr.reshape(start.shape) for subarr in valuelist ]
        else:
            valuelist = np.linspace(start,stop, no, endpoint).tolist()

        macro_generator = self._generator_set_value(var, valuelist)
        self.add_macro(macro_generator)


    def _create_set_value_cmd(self,var,val):
        """Creates a set value macro string"""
        if isinstance(val,list):
            val = np.array(val)
        if isinstance(val, np.ndarray):
            val = array2anyscript(val).strip('"')
        if isinstance(val,float):
            val = '{:.12g}'.format(val)
        return 'classoperation {0} "Set Value" --value="{1}"'.format(var,val)

    def _generator_set_value(self, var, values, special_first_values = None):
        """ Creates a generator for the set value macro command """
        if special_first_values is not None:
            yield self._create_set_value_cmd(var, special_first_values)
        for value in values:
            yield self._create_set_value_cmd(var, value)

    def _generator_specific_macro(self, cmd, i_macro):
        """ Generator which only include macro command in the i'th macro"""
        if not isinstance( i_macro, list):
            i_macro = [i_macro]
        for counter in range(self.number_of_macros):
            if counter in i_macro:
                yield cmd
            else:
                yield None


    def add_dump(self, variables, include_in_macro = None):
        """ Create Dump macro command.

        Parameters:
        ----------
        variables: string or list of strings
            The anyscript values to create a 'Dump' macro command for
        include_in_macro: integer or list of integers
            Specifices in which macros [0,1,2....NumberOfMacros] to include the
            dump command.
            If None, the command is included in all macros.


        Examples:
        ---------

        >>> mg = MacroGenerator()
        >>> mg.add_dump('Main.Study.myvar1')
        >>> pprint( mg.generate_macros())
        [['classoperation Main.Study.myvar1 "Dump"']]


        Only include the dump command in the two first macro

        >>> mg = MacroGenerator(number_of_macros = 5)
        >>> mg.add_load('MyModel.any')
        >>> mg.add_dump('Main.Study.myvar1', include_in_macro = [0,1])
        >>> pprint( mg.generate_macros())
        [['load "MyModel.any"', 'classoperation Main.Study.myvar1 "Dump"'],
         ['load "MyModel.any"', 'classoperation Main.Study.myvar1 "Dump"'],
         ['load "MyModel.any"'],
         ['load "MyModel.any"'],
         ['load "MyModel.any"']]

        """
        if not isinstance(variables,list):
            variables = [variables]
        for var in variables:
            if isinstance(var, string_types):
                cmd = 'classoperation {0} "Dump"'.format(var)
                if include_in_macro is not None:
                    self.add_macro( self._generator_specific_macro(cmd, include_in_macro))
                else:
                    self.add_macro(cmd)

    def add_load(self, mainfile, define_kw = {}, path_kw={}):
        """ Create a Load macro command.

        Parameters:
        ----------
        mainfile: string
            Path of the main file of the model
        define_kw: dict
            Dictionary of defines statements to set during load
        path_kw: dict
            Dictionary of path staements to set during load
        counter_token: string
            A string in the macro commands which will be replace with a counter
            for every macro generated

        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> paths = {'DATA':'c:/MyModel/Data'}
        >>> defines = {'EXCLUDE_ARMS':None, 'N_STEP':20}
        >>> mg.add_load('c:/MyModel/model.main.any', defines, paths)
        >>> pprint( mg.generate_macros())
        [['load "c:/MyModel/model.main.any" -def EXCLUDE_ARMS="" -def N_STEP="20" -p DATA=---"c:/MyModel/Data"']]

        >>> mg = MacroGenerator( number_of_macros = 3, counter_token='{COUNTER}' )
        >>> mg.add_load('c:/MyModel/model_{COUNTER}_.main.any')
        >>> pprint( mg.generate_macros())
        [['load "c:/MyModel/model_0_.main.any"'],
         ['load "c:/MyModel/model_1_.main.any"'],
         ['load "c:/MyModel/model_2_.main.any"']]

        """
        load_cmd = ['load "{}"'.format(mainfile)]

        for key in sorted(define_kw):
            value = define_kw[key]
            if isinstance(value, string_types):
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                    load_cmd.append(
                          '-def %s=---"\\"%s\\""'% (key, value.replace('\\','\\\\') ) )
                else:
                    load_cmd.append('-def %s="%s"'% (key, value))
            elif value is None:
                load_cmd.append('-def %s=""'% (key) )
            elif isinstance(value,float) :
                load_cmd.append('-def %s="%g"'% (key, value) )
            else :
                load_cmd.append('-def %s="%d"'% (key, value) )

        for key in sorted( path_kw ):
            load_cmd.append('-p %s=---"%s"'% (key, path_kw[key].replace('\\','\\\\')) )

        self.add_macro(' '.join(load_cmd))


    def add_save_design(self, operation, filename):
        """ Create a Save Design macro command.

        Parameters:
        ----------
        operation: string
            The AnyScript operation
        filename: string
            The file in which to save the design

        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> mg.add_save_design('Main.MyStudy.Kinematics', 'c:/design.txt')
        >>> pprint( mg.generate_macros())
        [['classoperation Main.MyStudy.Kinematics "Save design" --file="c:/design.txt"']]
        """
        self.add_macro('classoperation {} "Save design" --file="{}"'.format(operation, filename))

    def add_load_design(self, operation, filename):
        """ Create a Load Design macro command.

        Parameters:
        ----------
        operation: string
            The AnyScript operation
        filename: string
            The file from which to load the design

        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> mg.add_load_design('Main.MyStudy.Kinematics', 'c:/design.txt')
        >>> pprint( mg.generate_macros())
        [['classoperation Main.MyStudy.Kinematics "Load design" --file="c:/design.txt"']]
        """
        self.add_macro('classoperation {} "Load design" '
                       '--file="{}"'.format(operation, filename))

    def add_save_values(self, filename):
        """ Create a Save Values macro command.

        Parameters:
        ----------
        filename: string
            The anyset file to save the values to.

        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> mg.add_save_values('c:/values.anyset')
        >>> pprint( mg.generate_macros())
        [['classoperation Main "Save Values" --file="c:/values.anyset"']]
        """
        self.add_macro('classoperation Main "Save Values" --file="{}"'.format(filename))

    def add_load_values(self, filename):
        """ Create a Load Values macro command.

        Parameters:
        ----------
        filename: string
            The anyset file from which to load the values.

        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> mg.add_load_values('c:/values.anyset')
        >>> pprint( mg.generate_macros())
        [['classoperation Main "Load Values" --file="c:/values.anyset"']]
        """
        self.add_macro('classoperation Main "Load Values" --file="{}"'.format(filename))

    def add_update_values(self):
        """ Create a Update Values macro command.

        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> mg.add_update_values()
        >>> pprint( mg.generate_macros())
        [['classoperation Main "Update Values"']]
        """
        self.add_macro('classoperation Main "Update Values"')

    def add_run_operation(self, operation):
        """ Create a macro command to select and run an operation

        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> mg.add_run_operation('Main.MyStudy.Kinematics')
        >>> pprint( mg.generate_macros())
        [['operation Main.MyStudy.Kinematics', 'run']]
        """
        self.add_macro(['operation {}'.format(operation),'run'])


    def _build_macro(self,i ):
        """ Assemble the macro commands for the i'th macro,  """
        macro = []
        for elem in self._macro_cmd_list:
            if isinstance(elem, string_types):
                macro.append(elem)
            elif isinstance(elem, GeneratorType):
                macro_cmd = next(elem)
                if macro_cmd is not None:
                    macro.append( macro_cmd )
            else:
                continue
            if self._counter_token is not None:
                macro[-1] = macro[-1].replace(self._counter_token, str(i) )
        return macro


    def generate_macros(self, batch_size = None):
        """ Generate the macros. Either as list (batch_size = None) or in batches
        as generator object (memory efficient when generating many macros)

        Examples:
        ---------
        >>> mg = MacroGenerator(number_of_macros = 4)
        >>> mg.add_load("c:/Model.main.any")
        >>> mg.add_run_operation('Main.study.Kinematics')
        >>> macros =  mg.generate_macros()
        >>> pprint(macros)
        [['load "c:/Model.main.any"', 'operation Main.study.Kinematics', 'run'],
         ['load "c:/Model.main.any"', 'operation Main.study.Kinematics', 'run'],
         ['load "c:/Model.main.any"', 'operation Main.study.Kinematics', 'run'],
         ['load "c:/Model.main.any"', 'operation Main.study.Kinematics', 'run']]


        Generate macros in batches:
        >>> mg = MacroGenerator(number_of_macros = 6)
        >>> mg.add_load('c:/Model.main.any')
        >>> macro_gen =  mg.generate_macros(batch_size = 2)
        >>> for i, macros in enumerate( macro_gen ):
        ...     print( 'Batch {}'.format(i) )
        ...     pprint(macros)
        Batch 0
        [['load "c:/Model.main.any"'], ['load "c:/Model.main.any"']]
        Batch 1
        [['load "c:/Model.main.any"'], ['load "c:/Model.main.any"']]
        Batch 2
        [['load "c:/Model.main.any"'], ['load "c:/Model.main.any"']]
        """
        if batch_size is None:
            if not self.cached_output:
                self.cached_output = list(self._macro_generator(0))
            return self.cached_output
        else:
            return self._macro_generator(batch_size)


    def _macro_generator(self, batch_size = 0):
        """ Return a macro generator object"""
        assert(batch_size >= 0)

        macro_batch = []
        for i_macro in range(self.number_of_macros):
            if batch_size == 0:
                yield self._build_macro(i_macro)
            else:
                if self._new_batch_resets_counter:
                    macro_counter = i_macro % batch_size
                else:
                    macro_counter = i_macro
                macro_batch.append( self._build_macro(macro_counter) )
                if macro_counter+1 >= batch_size:
                    yield macro_batch
                    macro_batch = []

        if len(macro_batch):
            yield macro_batch


class MonteCarloMacroGenerator(MacroGenerator):
    """ Generates AnyScript macros for monte carlos studies.

    Overview
    ----------
    Class for building AnyScript macros for Monte Carlo parameter studies.
    This class extends the MacroGenerator class with methods, which can randomly
    vary parameters across the generated macros.

    The class contributes the following mehtods:

     - add_set_value_random_uniform()
         Create a set value macro with a uniform random distribution across
         macros

     - add_set_value_random_norm()
         Create a set value macro with a random distribution across
         macros

     - add_set_value_random()
         Create a Set Value operation with custom frozen distribution
         (see  scipy.stats.distributions)

    If 'many' macros should be generated the class can construct a python
    generator object which builds the macro (lazily) as they are requested (see
    the GenerateMacros() method )

    Parameters
    ----------
    number_of_macros:
        The number of macros to generate.

    Returns
    -------
    A MonteCarloMacroGenerator object:
        A MonteCarloMacroGenerator object for constructing the macros


    Examples:
    ---------

    >>> seed(1)
    >>> mg = MonteCarloMacroGenerator(number_of_macros=4)
    >>> mg.add_load('c:/MyModel/model.main.any')
    >>> mg.add_set_value_random_norm('Main.Study.myvar', means = 2, stdvs = 0.1)
    >>> mg.add_run_operation('Main.Study.Kinematics')
    >>> pprint( mg.generate_macros())
    [['load "c:/MyModel/model.main.any"',
      'classoperation Main.Study.myvar "Set Value" --value="2"',
      'operation Main.Study.Kinematics',
      'run'],
     ['load "c:/MyModel/model.main.any"',
      'classoperation Main.Study.myvar "Set Value" --value="1.97904821591"',
      'operation Main.Study.Kinematics',
      'run'],
     ['load "c:/MyModel/model.main.any"',
      'classoperation Main.Study.myvar "Set Value" --value="2.05838057443"',
      'operation Main.Study.Kinematics',
      'run'],
     ['load "c:/MyModel/model.main.any"',
      'classoperation Main.Study.myvar "Set Value" --value="1.63150523305"',
      'operation Main.Study.Kinematics',
      'run']]

    Generate macros using a custom distribtuion from scipy.stats.distribtuion.
    In this example we use a logistic distribution

    >>> seed(1)
    >>> from scipy.stats.distributions import logistic
    >>> log_dist = logistic( loc= [2,4,10],scale = [0.1,0.5,1] )
    >>> mg = MonteCarloMacroGenerator(number_of_macros=4)
    >>> mg.add_set_value_random('Main.MyVar', log_dist)
    >>> pprint( mg.generate_macros())
    [['classoperation Main.MyVar "Set Value" --value="{2,4,10}"'],
     ['classoperation Main.MyVar "Set Value" --value="{1.96649895478,4.47303588492,0.924084750004}"'],
     ['classoperation Main.MyVar "Set Value" --value="{1.91637851212,3.11986245798,7.71459079162}"'],
     ['classoperation Main.MyVar "Set Value" --value="{1.8525504037,3.68069479813,9.58104766459}"']]

    """

    def __init__(self, *args, **kwargs):
        super(self.__class__,self).__init__(*args, **kwargs)

    def add_set_value_random_uniform(self, variable, means, scale ):
        """ Add a 'Set Value' macro command where the value is chosen from a
        random uniform distribution.

        Parameters
        ----------
        variable: string
            An AnyScript variable or a list of AnyScript variables.
        means: int,float, numpy.ndarray
            The mean value of the random number
        scale: The range of the random variable [ means-scale/2 , means+scale/2]


        Examples:
        ---------
            Set variable across different macros

        >>> seed(1)
        >>> mg = MonteCarloMacroGenerator(number_of_macros=5)
        >>> mg.add_set_value_random_uniform('Main.Study.myvar', means = 2, scale = 0.1)
        >>> for line in mg.generate_macros(): pprint(line)
        ['classoperation Main.Study.myvar "Set Value" --value="2"']
        ['classoperation Main.Study.myvar "Set Value" --value="1.99170220047"']
        ['classoperation Main.Study.myvar "Set Value" --value="2.02203244934"']
        ['classoperation Main.Study.myvar "Set Value" --value="1.95001143748"']
        ['classoperation Main.Study.myvar "Set Value" --value="1.98023325726"']

        """
        dist = distributions.uniform(means-scale/2.0,scale)
        self.add_set_value_random(variable,dist)

    def add_set_value_random_norm(self, variable, means, stdvs ) :
        """ Add a 'Set Value' macro command where the value is chosen from a
        random normal distribution.

        Parameters
        ----------
        variable: string
            An AnyScript variable or a list of AnyScript variables.
        means: int,float, numpy.ndarray
            The mean value of the random number
        stdvs: The standar deviation of the random variable


        Examples:
        ---------
            Set variable across different macros

        >>> seed(1)
        >>> mg = MonteCarloMacroGenerator(number_of_macros=5)
        >>> mg.add_set_value_random_norm('Main.Var', means = [1,2,4], stdvs = [0.1,0.5,2])
        >>> for line in mg.generate_macros(): pprint(line)
        ['classoperation Main.Var "Set Value" --value="{1,2,4}"']
        ['classoperation Main.Var "Set Value" --value="{0.979048215908,2.29190287213,-3.36989533908}"']
        ['classoperation Main.Var "Set Value" --value="{0.948229648476,1.47477555917,1.34701845466}"']
        ['classoperation Main.Var "Set Value" --value="{0.910823783045,1.80133318708,3.47655384811}"']
        ['classoperation Main.Var "Set Value" --value="{1.00974531575,1.8980227331,4.96468967866}"']

        """
        dist = distributions.norm(means,stdvs)
        self.add_set_value_random(variable,dist)

    def add_set_value_random(self, variable, frozen_dist ) :
        """ Add a 'Set Value' macro command where the value is chosen from a
        distibution in scipy.stats.distributions.

        Parameters
        ----------
        variable: string
            An AnyScript variable or a list of AnyScript variables.
        frozen_dist: <scipy.stats.distributions.rv_frozen>
            A frozen distribution from scipy.stats.distributions

        Examples:
        ---------
        >>> seed(1)
        >>> from scipy.stats.distributions import logistic
        >>> log_dist = logistic( loc= [1,3,4],scale = [0.1,0.5,1] )
        >>> mg = MonteCarloMacroGenerator(number_of_macros=4)
        >>> mg.add_set_value_random('Main.MyVar', log_dist)
        >>> for line in mg.generate_macros(): pprint(line)
        ['classoperation Main.MyVar "Set Value" --value="{1,3,4}"']
        ['classoperation Main.MyVar "Set Value" --value="{0.966498954775,3.47303588492,-5.07591525}"']
        ['classoperation Main.MyVar "Set Value" --value="{0.916378512121,2.11986245798,1.71459079162}"']
        ['classoperation Main.MyVar "Set Value" --value="{0.852550403705,2.68069479813,3.58104766459}"']

        """
        if not isinstance(frozen_dist, distributions.rv_frozen):
            raise TypeError('frozen_dist must be frozen distribtuion from \
                            scipy.stats.distributions' )
        mean_value = frozen_dist.mean()
        if isinstance(mean_value,np.ndarray):
            shape = mean_value.shape
        else:
            shape = None
        random_values = (frozen_dist.ppf(random(shape)) for _ in \
                                    range(self.number_of_macros-1) )
        macro_generator = self._generator_set_value(variable,
                                                    random_values,
                                                    special_first_values= mean_value)
        self.add_macro(macro_generator)


class LatinHyperCubeMacroGenerator(MacroGenerator):
    """ Generates AnyScript macros for parameter studies using Latin hyper cube
    sampling  .

    Overview
    ----------
    Class for building AnyScript macros for parameter studies with Latin
    Hypercube Sampling (LHS) of the parameter space. The number of generated
    macros determined the number of LHS samples.

    The class uses pyDOE package to generate the LHS data.

    This class extends the MacroGenerator class with the following methods:

     - add_set_value_LHS_uniform()
         Create a Set Value macro  command where the parameters are uniformly
         sampled using Latin Hypercube sampling across the macros

     - add_set_value_LHS()
         Create a Set Value macro command where the parameters are sampled from
         custom distribution using Latin Hypercube sampling across the macros

    If 'many' macros should be generated the class can construct a python
    generator object which builds the macro (lazily) as they are requested (see
    the GenerateMacros() method )

    Parameters
    ----------
    number_of_macros:
        The number of macros to generate.
    criterion:
        A a string that specifies how points are sampled
        (see: http://pythonhosted.org/pyDOE/randomized.html)

        - None: Default, points are randomizes within the intervals

        - "center" or "c": center the points within the sampling intervals

        - "maximin" or "m": maximize the minimum distance between points, but place
           the point in a randomized location within its interval

        - "centermaximin" or "cm": same as “maximin”, but centered within the intervals

        - "corr": minimize the maximum correlation coefficient

    iterations: int
        Specifies how many iterations are used to accomplished the selected criterion


    Returns
    -------
    A LatinHyperCubeMacroGenerator object:

    """

    def __init__(self, number_of_macros = 1, criterion = None, iterations = None, **kwargs ):
        super(LatinHyperCubeMacroGenerator, self).__init__(number_of_macros, **kwargs)
        self.LHS_factors = 0
        self.lhd = np.zeros((2,100))
        self.criterion = criterion
        self.iterations = iterations


    def add_set_value_LHS_uniform(self, variable, loc, scale ) :
        """ Add a 'Set Value' macro command where the values are uniformly
        chosen from the  interval [loc - loc + scale]
        using a Latin Hyper Cube sampler.

        Parameters
        ----------
        variable: string
            An AnyScript variable or a list of AnyScript variables.
        loc: int,float, numpy.ndarray
            The start of the interval for uniform sampling.
        scale: The range of the sample interval


        Examples:
        ---------
            Set variable across different macros

        >>> seed(1)
        >>> mg = LatinHyperCubeMacroGenerator(number_of_macros=8)
        >>> mg.add_set_value_LHS_uniform('Main.myvar1',1,2)
        >>> mg.add_set_value_LHS_uniform('Main.myvar2',10,10)
        >>> pprint( mg.generate_macros() )
        [['classoperation Main.myvar1 "Set Value" --value="2"',
          'classoperation Main.myvar2 "Set Value" --value="15"'],
         ['classoperation Main.myvar1 "Set Value" --value="2.09919186856"',
          'classoperation Main.myvar2 "Set Value" --value="12.6154232435"'],
         ['classoperation Main.myvar1 "Set Value" --value="1.79656505284"',
          'classoperation Main.myvar2 "Set Value" --value="15.6735209175"'],
         ['classoperation Main.myvar1 "Set Value" --value="2.3547986286"',
          'classoperation Main.myvar2 "Set Value" --value="14.1819509088"'],
         ['classoperation Main.myvar1 "Set Value" --value="1.5366889727"',
          'classoperation Main.myvar2 "Set Value" --value="10.9004056168"'],
         ['classoperation Main.myvar1 "Set Value" --value="1.10425550118"',
          'classoperation Main.myvar2 "Set Value" --value="18.5976467955"'],
         ['classoperation Main.myvar1 "Set Value" --value="2.55111306243"',
          'classoperation Main.myvar2 "Set Value" --value="19.5880843877"'],
         ['classoperation Main.myvar1 "Set Value" --value="1.2500285937"',
          'classoperation Main.myvar2 "Set Value" --value="17.1065243755"']]

        """
        if isinstance(loc,list):
            loc = np.array(loc)
        if isinstance(scale,list):
            scale = np.array(scale)
        dist = distributions.uniform(loc,scale)
        self.add_set_value_LHS(variable,dist)


    def add_set_value_LHS(self, var, frozen_dist ) :
        """ Add a 'Set Value' macro command where the values are
        chosen using Latin Hyper Cube Sampling and transformed using custom
        distribution. Note the first generated macro correspond to the mean
        value of the input parameters.

        Parameters
        ----------
        variable: string
            An AnyScript variable or a list of AnyScript variables.
        frozen_dist: <scipy.stats.distributions.rv_frozen>
            A frozen distribution from scipy.stats.distributions


        Examples:
        ---------

        >>> seed(1)
        >>> from scipy.stats.distributions import norm
        >>> normdist = norm( [1,3,4], [0.1,0.5,1] )
        >>> mg = LatinHyperCubeMacroGenerator(number_of_macros=4)
        >>> mg.add_set_value_LHS('Main.myvar1',normdist)
        >>> mg.add_set_value_LHS('Main.myvar2', normdist)
        >>> pprint( mg.generate_macros() )
        [['classoperation Main.myvar1 "Set Value" --value="{1,3,4}"',
          'classoperation Main.myvar2 "Set Value" --value="{1,3,4}"'],
         ['classoperation Main.myvar1 "Set Value" --value="{1.07895227633,3.41996355574,-0.0241255334168}"',
          'classoperation Main.myvar2 "Set Value" --value="{1.24119096808,2.1047636289,2.00615775617}"'],
         ['classoperation Main.myvar1 "Set Value" --value="{1.01284739969,3.29072197649,5.64666114098}"',
          'classoperation Main.myvar2 "Set Value" --value="{0.970685113414,2.81380147984,4.35758342284}"'],
         ['classoperation Main.myvar1 "Set Value" --value="{0.87423296579,2.54247201378,4.01716347152}"',
          'classoperation Main.myvar2 "Set Value" --value="{1.04333421171,3.13228054445,5.42610272557}"']]

        """

        if not isinstance(frozen_dist, distributions.rv_frozen):
            raise TypeError('frozen_dist must be frozen distribtuion from \
                            scipy.stats.distributions' )

        mean_value = frozen_dist.mean()

        if isinstance(mean_value, np.ndarray):
            shape = mean_value.shape
            n_elem = np.prod(shape)
            lhs_slice = np.s_[self.LHS_factors:self.LHS_factors+n_elem]
            # Create a generator which will later be used to generate the values
            # based on the variables in self.lhd matrix
            values = (frozen_dist.ppf(self.lhd[i , lhs_slice ].reshape(shape) )\
                        for i in  range(self.number_of_macros-1) )
        else:
            #shape = None
            n_elem = 1
            lhs_index = self.LHS_factors
            # Create a generator which will later be used to generate the values
            # based on the variables in self.lhd matrix
            values = (frozen_dist.ppf(self.lhd[i , lhs_index ])\
                        for i in range(self.number_of_macros-1) )

        if self.number_of_macros == 1:
            macro_generator = self._generator_set_value(var,  [mean_value])
        else:
            macro_generator = self._generator_set_value(var,  values,
                                                    special_first_values = mean_value)
        self.add_macro(macro_generator)

        self.LHS_factors += n_elem

    def generate_macros(self, batch_size = None):
        try:
            import pyDOE
        except ImportError:
            raise ImportError('The pyDOE package must be install to use this class')

        # Only generate LHS values if user requested more than macros, since the
        # first macro is allways the mean value
        if self.number_of_macros > 1:
            # Create the Latin hyper cube sample matrix. This is used by the
            # individual macro generator functions when macros are created.
            self.lhd = pyDOE.lhs(self.LHS_factors,  samples=self.number_of_macros-1,
                                 criterion = self.criterion,
                                 iterations = self.iterations)

        return super(LatinHyperCubeMacroGenerator,self).generate_macros(batch_size)



class PertubationMacroGenerator(MacroGenerator):
    """ TODO: Make a class that can generate macros for pertubation studies


    """
    def __init__(self, pertubationfactor = 1e-4):
        super(self.__class__,self).__init__(number_of_macros = 1)

        self.pertubationfactor = pertubationfactor


    def _generator_set_value_designvar(self, var, value, i_designvar):
        for counter in range(self.number_of_macros):
            if counter == i_designvar:
                yield self._create_set_value_cmd(var, value+self.pertubationfactor)
            else:
                yield self._create_set_value_cmd(var, value)


    def add_set_value_designvar(self,var, value):

        macro_generator = self._generator_set_value_designvar(var,value,
                                                              self.number_of_macros)
        self.number_of_macros += 1
        self.add_macro(macro_generator)


    def add_set_value_range(self, var, start, stop, endpoint = True ) :
        no = self.number_of_macros
        if isinstance(start, np.ndarray):
            arr = np.array([np.linspace(i,j, no, endpoint) for i,j in zip(start,stop)])
            arr = arr.T.squeeze()
        else:
            arr = np.linspace(start,stop, no, endpoint)

        values = (_ for _ in arr)

        macro_generator = self._generator_set_value(var, values)
        self.add_macro(macro_generator)


if __name__ == '__main__':

#    mg = PertubationMacroGenerator()
#    mg.add_set_value_designvar('test',1)
#    mg.add_set_value_designvar('test',2)
#
#    pprint(mg.generate_macros())
#
    import pytest
    pytest.main(str('generate_macros.py --doctest-modules'))

