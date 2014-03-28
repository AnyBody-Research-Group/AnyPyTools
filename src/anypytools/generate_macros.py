# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 21:14:59 2012

@author: Morten
"""
from __future__ import division, absolute_import, print_function, unicode_literals
try:
    from .utils.py3k import * # @UnusedWildImport
except ValueError:
    from utils.py3k import * # @UnusedWildImport

from pprint import pprint
import numpy as np
from scipy.stats import distributions
from numpy.random import random, seed
import types

def _list2anyscript(arr):
    def createsubarr(arr):
        outstr = ""
        if isinstance(arr, np.ndarray):
            if len(arr) == 1:
                return str(arr[0])
            outstr += '{'
            for row in arr:
                outstr += createsubarr(row)
            outstr = outstr[0:-1] + '},'
            return outstr
        else:
            return outstr + str(arr)+','      
    if isinstance(arr, np.ndarray) :
        return createsubarr(arr)[0:-1]
    else:
        return str(arr)

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
    [[u'load "c:/MyModel/model.main.any"',
      u'classoperation Main.Study.myvar "Set Value" --value="12.3"',
      u'operation Main.Study.Kinematics',
      u'run']]

    If more than one macro is generated the class can construct a python 
    generator object which builds the macro (lazily) as they are requested. 
             
             
    Parameters
    ----------
    number_of_macros:
        The number of macros to generate. M
        
    Returns
    -------
    A MacroGenerator object: 
        A MacroGenerator object for constructing the macro.       
    """    
    def __init__(self, number_of_macros=1):
        assert(number_of_macros > 0)
        self._macro_cmd_list = []
        self.number_of_macros = number_of_macros
       
       
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
            >>> mg.add_set_value('Main.Study.myvar1', 23.0)
            >>> mg.add_set_value('Main.Study.myvar2', np.array([2,3,4]))
            >>> mg.add_run_operation('Main.Study.Kinematics')
            >>> pprint( mg.generate_macros() )
            [[u'load "c:/MyModel/model.main.any"',
              u'classoperation Main.Study.myvar1 "Set Value" --value="23.0"',
              u'classoperation Main.Study.myvar2 "Set Value" --value="{2,3,4}"',
              u'operation Main.Study.Kinematics',
              u'run']]
            
            Set variable across different macros
            
            >>> mg = MacroGenerator(number_of_macros = 3)
            >>> mg.add_load('c:/MyModel/model.main.any')
            >>> mg.add_set_value('Main.Study.myvar1',[1,2,3])
            >>> pprint( mg.generate_macros() )
            [[u'load "c:/MyModel/model.main.any"',
              u'classoperation Main.Study.myvar1 "Set Value" --value="1"'],
             [u'load "c:/MyModel/model.main.any"',
              u'classoperation Main.Study.myvar1 "Set Value" --value="2"'],
             [u'load "c:/MyModel/model.main.any"',
              u'classoperation Main.Study.myvar1 "Set Value" --value="3"']]
            
            The method can also add several macro commands if both variable and 
            value are list of the same length
            
            >>> mg = MacroGenerator()
            >>> mg.add_set_value(['Main.Study.myvar1','Main.Study.myvar1'],[4.0, 23.0])
            >>> pprint( mg.generate_macros())
            [[u'classoperation Main.Study.myvar1 "Set Value" --value="4.0"',
              u'classoperation Main.Study.myvar1 "Set Value" --value="23.0"']]
            
        """        
        
        if isinstance(variable,list) and isinstance(value,list):
            if len(variable) != len(value):
                raise ValueError('Lists must be the same length')
            for k,v in zip(variable,value):
                self.add_macro(self._create_set_value_cmd(k,v))
        
        elif isinstance(variable, basestring) and isinstance(value,list):
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
            [[u'classoperation Main.Study.myvar1 "Set Value" --value="10.0"'],
             [u'classoperation Main.Study.myvar1 "Set Value" --value="20.0"'],
             [u'classoperation Main.Study.myvar1 "Set Value" --value="30.0"'],
             [u'classoperation Main.Study.myvar1 "Set Value" --value="40.0"'],
             [u'classoperation Main.Study.myvar1 "Set Value" --value="50.0"'],
             [u'classoperation Main.Study.myvar1 "Set Value" --value="60.0"'],
             [u'classoperation Main.Study.myvar1 "Set Value" --value="70.0"'],
             [u'classoperation Main.Study.myvar1 "Set Value" --value="80.0"'],
             [u'classoperation Main.Study.myvar1 "Set Value" --value="90.0"'],
             [u'classoperation Main.Study.myvar1 "Set Value" --value="100.0"']]

        """                
        no = self.number_of_macros
        if isinstance(start, np.ndarray):
            assert start.shape == stop.shape, 'Start and stop must be similar'
            arr = np.array([np.linspace(i,j, no, endpoint) for i,j in zip(start,stop)])
            values = arr.T.squeeze()
        else:
            values = np.linspace(start,stop, no, endpoint)
        
        macro_generator = self._generator_set_value(var, values)
        self.add_macro(macro_generator)
    
    
    def _create_set_value_cmd(self,var,val):
        """Creates a set value macro string"""
        if isinstance(val,list):
            val = np.array(val)
        if isinstance(val, np.ndarray):
                val = _list2anyscript(val)
        return 'classoperation {0} "Set Value" --value="{1}"'.format(var,val)

    def _generator_set_value(self, var, values):
        """ Creates a generator for the set value macro command """
        for value in values:
            yield self._create_set_value_cmd(var, value)
    
    def add_dump(self, variables):
        """ Create Dump macro command.
        
        Parameters:
        ----------
        variables: string or list of strings
            The anyscript values to create a 'Dump' macro command for
            
        Examples:
        ---------
        
        >>> mg = MacroGenerator()
        >>> mg.add_dump('Main.Study.myvar1')
        >>> print( mg.generate_macros())
        [[u'classoperation Main.Study.myvar1 "Dump"']]
        """
        if not isinstance(variables,list):
            variables = [variables]
        for var in variables:
            self.add_macro('classoperation {0} "Dump"'.format(var))
    
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
            
        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> paths = {'DATA':'c:/MyModel/Data'}
        >>> defines = {'EXCLUDE_ARMS':None, 'N_STEP':20}
        >>> mg.add_load('c:/MyModel/model.main.any', defines, paths)
        >>> print( mg.generate_macros())
        [[u'load "c:/MyModel/model.main.any" -def EXCLUDE_ARMS="" -def N_STEP="20" -p DATA=---"c:/MyModel/Data"']]
        """
        load_cmd = ['load "{}"'.format(mainfile)]
        
        for key,value in define_kw.iteritems():   
            if isinstance(value,basestring):
                load_cmd.append('-def %s=---"\\"%s\\""'% (key, value) )
            elif value is None:
                load_cmd.append('-def %s=""'% (key) )
            else:
                load_cmd.append('-def %s="%d"'% (key, value) )
        
        for key,value in path_kw.iteritems():   
            load_cmd.append('-p %s=---"%s"'% (key, value.replace('\\','\\\\')) )
        
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
        >>> print( mg.generate_macros())
        [[u'classoperation Main.MyStudy.Kinematics "Save design" --file="c:/design.txt"']]
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
        >>> print( mg.generate_macros())
        [[u'classoperation Main.MyStudy.Kinematics "Load design" --file="c:/design.txt"']]
        """
        self.add_macro('classoperation {} "Load design" --file="{}"'.format(operation, filename))

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
        >>> print( mg.generate_macros())
        [[u'classoperation Main "Save Values" --file="c:/values.anyset"']]
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
        >>> print( mg.generate_macros())
        [[u'classoperation Main "Load Values" --file="c:/values.anyset"']]
        """        
        self.add_macro('classoperation Main "Load Values" --file="{}"'.format(filename))

    def add_update_values(self):
        """ Create a Update Values macro command.
                    
        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> mg.add_update_values()
        >>> print( mg.generate_macros())
        [[u'classoperation Main "Update Values"']]
        """        
        self.add_macro('classoperation Main "Update Values"')

    def add_run_operation(self, operation):
        """ Create a macro command to select and run an operation 
                    
        Examples:
        ---------
        >>> mg = MacroGenerator()
        >>> mg.add_run_operation('Main.MyStudy.Kinematics')
        >>> print( mg.generate_macros())
        [[u'operation Main.MyStudy.Kinematics', u'run']]
        """        
        self.add_macro(['operation {}'.format(operation),'run'])
        

    def _build_macro(self,i):
        """ Assemble the macro commands for the i'th  macro"""
        macro = []
        for macro_cmd in self._macro_cmd_list:
            if isinstance(macro_cmd, basestring):
                macro.append(macro_cmd)
            if isinstance(macro_cmd, types.GeneratorType):
                macro.append(macro_cmd.next())
        return macro
        
        
    def generate_macros(self, batch_size = None):
        """ Generate the macros. Either as list (batch = None) or in batches 
        as generator object (memory efficient when generating many macros)
                    
        Examples:
        ---------
        >>> mg = MacroGenerator(number_of_macros = 4)
        >>> mg.add_load("c:/Model.main.any")
        >>> mg.add_run_operation('Main.study.Kinematics')
        >>> macros =  mg.generate_macros()
        >>> type(macros)
        <type 'list'>
        >>> pprint(macros)
        [[u'load "c:/Model.main.any"', u'operation Main.study.Kinematics', u'run'],
         [u'load "c:/Model.main.any"', u'operation Main.study.Kinematics', u'run'],
         [u'load "c:/Model.main.any"', u'operation Main.study.Kinematics', u'run'],
         [u'load "c:/Model.main.any"', u'operation Main.study.Kinematics', u'run']]
        
        
        Generate macros in batches:
        >>> mg = MacroGenerator(number_of_macros = 6)
        >>> mg.add_load('c:/Model.main.any')
        >>> macro_gen =  mg.generate_macros(batch_size = 2) 
        >>> type(macro_gen)
        <type 'generator'>
        >>> for i, macros in enumerate( macro_gen ):
        ...     print( 'Batch {}'.format(i) )
        ...     pprint(macros)
        Batch 0
        [[u'load "c:/Model.main.any"'], [u'load "c:/Model.main.any"']]
        Batch 1
        [[u'load "c:/Model.main.any"'], [u'load "c:/Model.main.any"']]
        Batch 2
        [[u'load "c:/Model.main.any"'], [u'load "c:/Model.main.any"']]
        """        
        if batch_size is None:
           return list(self._macro_generator(0))
        else:
            return self._macro_generator(batch_size)
    
    
    def _macro_generator(self, batch = 0):
        """ Return a macro generator object"""
        assert(batch >= 0)
        
        macro_batch = []
        for i_macro in range(self.number_of_macros):
            if batch == 0:
                yield self._build_macro(i_macro)
            else: 
                macro_batch.append( self._build_macro(i_macro) )
                if i_macro % batch == batch-1:
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
    vary parameters across the generated macros 
    
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
    [[u'load "c:/MyModel/model.main.any"',
      u'classoperation Main.Study.myvar "Set Value" --value="1.97904821591"',
      u'operation Main.Study.Kinematics',
      u'run'],
     [u'load "c:/MyModel/model.main.any"',
      u'classoperation Main.Study.myvar "Set Value" --value="2.05838057443"',
      u'operation Main.Study.Kinematics',
      u'run'],
     [u'load "c:/MyModel/model.main.any"',
      u'classoperation Main.Study.myvar "Set Value" --value="1.63150523305"',
      u'operation Main.Study.Kinematics',
      u'run'],
     [u'load "c:/MyModel/model.main.any"',
      u'classoperation Main.Study.myvar "Set Value" --value="1.94822964848"',
      u'operation Main.Study.Kinematics',
      u'run']]
    
    Generate macros using a custom distribtuion from scipy.stats.distribtuion. 
    In this example we use a logistic distribution
    
    >>> seed(1)
    >>> from scipy.stats.distributions import logistic
    >>> log_dist = logistic( loc= [2,4,10],scale = [0.1,0.5,1] )
    >>> mg = MonteCarloMacroGenerator(number_of_macros=4)
    >>> mg.add_set_value_random('Main.MyVar', log_dist)
    >>> pprint( mg.generate_macros())
    [[u'classoperation Main.MyVar "Set Value" --value="{1.96649895478,4.47303588492,0.924084750004}"'],
     [u'classoperation Main.MyVar "Set Value" --value="{1.91637851212,3.11986245798,7.71459079162}"'],
     [u'classoperation Main.MyVar "Set Value" --value="{1.8525504037,3.68069479813,9.58104766459}"'],
     [u'classoperation Main.MyVar "Set Value" --value="{2.01555799978,3.83695956934,10.7778636562}"']]

    """    

    def __init__(self, number_of_macros=1):
        super(self.__class__,self).__init__(number_of_macros)
                
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
        >>> for line in mg.generate_macros(): print(line)
        [u'classoperation Main.Study.myvar "Set Value" --value="1.99170220047"']
        [u'classoperation Main.Study.myvar "Set Value" --value="2.02203244934"']
        [u'classoperation Main.Study.myvar "Set Value" --value="1.95001143748"']
        [u'classoperation Main.Study.myvar "Set Value" --value="1.98023325726"']
        [u'classoperation Main.Study.myvar "Set Value" --value="1.96467558908"']
            
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
        >>> for line in mg.generate_macros(): print(line)
        [u'classoperation Main.Var "Set Value" --value="{0.979048215908,2.29190287213,-3.36989533908}"']
        [u'classoperation Main.Var "Set Value" --value="{0.948229648476,1.47477555917,1.34701845466}"']
        [u'classoperation Main.Var "Set Value" --value="{0.910823783045,1.80133318708,3.47655384811}"']
        [u'classoperation Main.Var "Set Value" --value="{1.00974531575,1.8980227331,4.96468967866}"']
        [u'classoperation Main.Var "Set Value" --value="{0.917417699026,2.5828136969,0.158689525592}"']
            
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
        >>> for line in mg.generate_macros(): print(line)
        [u'classoperation Main.MyVar "Set Value" --value="{0.966498954775,3.47303588492,-5.07591525}"']
        [u'classoperation Main.MyVar "Set Value" --value="{0.916378512121,2.11986245798,1.71459079162}"']
        [u'classoperation Main.MyVar "Set Value" --value="{0.852550403705,2.68069479813,3.58104766459}"']
        [u'classoperation Main.MyVar "Set Value" --value="{1.01555799978,2.83695956934,4.7778636562}"']
            
        """        
        if not isinstance(frozen_dist, distributions.rv_frozen):
            raise TypeError('frozen_dist must be frozen distribtuion from \
                            scipy.stats.distributions' )
        if isinstance(frozen_dist.mean(),np.ndarray):
            shape = frozen_dist.mean().shape
        else:
            shape = None
        random_values = (frozen_dist.ppf(random(shape)) for _ in \
                                    range(self.number_of_macros) )
        macro_generator = self._generator_set_value(variable, random_values)
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
         
    Returns
    -------
    A LatinHyperCubeMacroGenerator object: 

    """    

    def __init__(self, number_of_macros=1): 
        super(self.__class__,self).__init__(number_of_macros)
        self.LHS_factors = 0
        self.lhd = np.zeros((2,100))
        
                
    def add_set_value_LHS_uniform(self, variable, means, scale ) :
        """ Add a 'Set Value' macro command where the values are uniformly
        chosen using Latin Hyper Cube Sampling.
        
        Parameters
        ----------
        variable: string
            An AnyScript variable or a list of AnyScript variables. 
        means: int,float, numpy.ndarray
            The mean value of the sampled space
        scale: The range of the variable from means-scale/2 to means+scale/2]
        
                                         
        Examples:
        ---------                 
            Set variable across different macros
            
        >>> seed(1)
        >>> mg = LatinHyperCubeMacroGenerator(number_of_macros=8)
        >>> mg.add_set_value_LHS_uniform('Main.myvar1',1,2)
        >>> mg.add_set_value_LHS_uniform('Main.myvar2',10,10)
        >>> pprint( mg.generate_macros() )
        [[u'classoperation Main.myvar1 "Set Value" --value="1.0991918685"',
          u'classoperation Main.myvar2 "Set Value" --value="7.6154232434"'],
         [u'classoperation Main.myvar1 "Set Value" --value="0.79656505284"',
          u'classoperation Main.myvar2 "Set Value" --value="10.673520917"'],
         [u'classoperation Main.myvar1 "Set Value" --value="1.354798628"',
          u'classoperation Main.myvar2 "Set Value" --value="9.181950908"'],
         [u'classoperation Main.myvar1 "Set Value" --value="0.53668897270"',
          u'classoperation Main.myvar2 "Set Value" --value="5.900405616"'],
         [u'classoperation Main.myvar1 "Set Value" --value="0.10425550117"',
          u'classoperation Main.myvar2 "Set Value" --value="13.597646795"'],
         [u'classoperation Main.myvar1 "Set Value" --value="1.5511130624"',
          u'classoperation Main.myvar2 "Set Value" --value="14.588084387"'],
         [u'classoperation Main.myvar1 "Set Value" --value="0.25002859370"',
          u'classoperation Main.myvar2 "Set Value" --value="12.106524375"'],
         [u'classoperation Main.myvar1 "Set Value" --value="1.756846898"',
          u'classoperation Main.myvar2 "Set Value" --value="6.6279157157"']]
            
        """        
        if isinstance(means,list):
            means = np.array(means)
        if isinstance(scale,list):
            scale = np.array(scale)
        dist = distributions.uniform(means-scale/2.0,scale)
        self.add_set_value_LHS(variable,dist)


    def add_set_value_LHS(self, var, frozen_dist ) :
        """ Add a 'Set Value' macro command where the values are
        chosen using Latin Hyper Cube Sampling and transformed using custom 
        distribution
        
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
        [[u'classoperation Main.myvar1 "Set Value" --value="{1.07895227633,3.41996355574,-0.0241255334168}"',
          u'classoperation Main.myvar2 "Set Value" --value="{1.24119096808,2.1047636289,2.00615775617}"'],
         [u'classoperation Main.myvar1 "Set Value" --value="{1.01284739969,3.29072197649,5.64666114098}"',
          u'classoperation Main.myvar2 "Set Value" --value="{0.970685113414,2.81380147984,4.35758342284}"'],
         [u'classoperation Main.myvar1 "Set Value" --value="{0.87423296579,2.54247201378,4.01716347152}"',
          u'classoperation Main.myvar2 "Set Value" --value="{1.04333421171,3.13228054445,5.42610272557}"'],
         [u'classoperation Main.myvar1 "Set Value" --value="{0.94656943816,2.78883239641,3.61249682803}"',
          u'classoperation Main.myvar2 "Set Value" --value="{0.856457591334,3.47384439353,3.80144358466}"']]
            
        """        

        if not isinstance(frozen_dist, distributions.rv_frozen):
            raise TypeError('frozen_dist must be frozen distribtuion from \
                            scipy.stats.distributions' )
        
        if isinstance(frozen_dist.mean(),np.ndarray):
            shape = frozen_dist.mean().shape
            n_elem = np.prod(shape)
            lhs_slice = np.s_[self.LHS_factors:self.LHS_factors+n_elem]
            values = (frozen_dist.ppf(self.lhd[i , lhs_slice ].reshape(shape) )\
                        for i in  range(self.number_of_macros) )
        else:
            shape = None
            n_elem = 1
            lhs_slice = np.s_[self.LHS_factors:self.LHS_factors+n_elem]
            values = (frozen_dist.ppf(self.lhd[i , lhs_slice ] )\
                        for i in range(self.number_of_macros) )
        
        macro_generator = self._generator_set_value(var, values)
        self.add_macro(macro_generator)

        self.LHS_factors += n_elem

    def generate_macros(self, batch_size = None):
        try:
            import pyDOE
        except ImportError:
            raise ImportError('The pyDOE package must be install to use this class')

        self.lhd = pyDOE.lhs(self.LHS_factors, samples=self.number_of_macros)
        return super(LatinHyperCubeMacroGenerator,self).generate_macros(batch_size)
        
        
        
class PertubationMacroGenerator(MacroGenerator):
    """ TODO: Make a class that can generate macros for pertubation studies
    
    
    """
    def __init__(self, number_of_macros=1):
        super(self.__class__,self).__init__(number_of_macros)        
                
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
    
    import doctest
    doctest.testmod()


