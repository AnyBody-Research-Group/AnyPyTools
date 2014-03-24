# -*- coding: utf-8 -*-
"""
Created on Fri Oct 19 21:14:59 2012

@author: Morten
"""
from __future__ import division, absolute_import, print_function, unicode_literals
from utils.py3k import * # @UnusedWildImport


import numpy as np
from scipy.stats import distributions
from numpy.random import random
import types
import pyDOE

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



class MacroGenerator(object):

    def __init__(self, number_of_macros=1):
        self.macro_cmd_list = []
        self.number_of_macros = number_of_macros
       
    def add_macro(self,macro):
        if not isinstance(macro,list):
            macro = [macro]
        for macro_cmd in macro:
            self.macro_cmd_list.append(macro_cmd)
            
    def add_set_value(self,variables, values):
        if not isinstance(variables,list):
            variables = [variables]
        if not isinstance(values,list):
            values = [values]
        for var,val in zip(variables,values):
            self.add_macro(self._create_set_value_cmd(var,val))
    
    def _create_set_value_cmd(self,var,val):
        if isinstance(val, np.ndarray):
                val = _list2anyscript(val)
        return 'classoperation {0} "Set Value" --value="{1}"'.format(var,val)

    def _generator_set_value(self, var, values):
        for value in values:
            yield self._create_set_value_cmd(var, value)
    
    def add_dump(self, variables):
        if not isinstance(variables,list):
            variables = [variables]
        for var in variables:
            self.add_macro('classoperation {0} "Dump"'.format(var))
    
    def add_load(self, mainfile, define_kw = {}, path_kw={}):
        load_cmd = ['load "{}"'.format(mainfile)]
        
        for key,value in define_kw.iteritems():   
            if isinstance(value,basestring):
                load_cmd.append('-def %s=---"\\"%s\\""'% (key, value) )
            elif value is None:
                load_cmd.append('-def %s=---""'% (key) )
            else:
                load_cmd.append('-def %s="%d"'% (key, value) )
        
        for key,value in path_kw.iteritems():   
            load_cmd.append('-p %s=---"%s"'% (key, value.replace('\\','\\\\')) )
        
        self.add_macro(' '.join(load_cmd))
    
        
    def add_save_design(self, operation, filename):
        self.add_macro('classoperation {} "Save design" --file="{}"'.format(operation, filename))
        
    def add_load_design(self, operation, filename):
        self.add_macro('classoperation {} "Load design" --file="{}"'.format(operation, filename))

    def add_save_values(self, filename):
        self.add_macro('classoperation Main "Save Values" --file="{}"'.format(filename))

    def add_load_values(self, filename):
        self.add_macro('classoperation Main "Load Values" --file="{}"'.format(filename))

    def add_update_values(self):
        self.add_macro('classoperation Main "Update Values"')

    def add_run_operation(self, operation):
        self.add_macro(['operation {}'.format(operation),'run'])
        

    def build_macro(self,i):
        macro = []
        for macro_cmd in self.macro_cmd_list:
            if isinstance(macro_cmd, basestring):
                macro.append(macro_cmd)
            if isinstance(macro_cmd, types.GeneratorType):
                macro.append(macro_cmd.next())
        return macro
        
        
    def generate_macros(self, batch = 1):
        if batch is None:
            batch=self.number_of_macros
        macros = []
        for i_macro in range(self.number_of_macros):
            macros.append( self.build_macro(i_macro) )
            
            if i_macro % batch == batch-1:
                yield macros
                macros = []
        if len(macros):
            yield macros 
    
    
class MonteCarloMacroGenerator(MacroGenerator):
    
    def __init__(self, number_of_macros=1):
        super(self.__class__,self).__init__(number_of_macros)
                
    def add_set_value_random_uniform(self, var, means, scale ) :
        dist = distributions.uniform(means-scale/2.0,scale)
        self.add_set_value_random(var,dist)
        
    def add_set_value_random_norm(self, var, means, stdvs ) :
        dist = distributions.norm(means,stdvs)
        self.add_set_value_random(var,dist)

    def add_set_value_random(self, var, frozen_dist ) :
        if not isinstance(frozen_dist, distributions.rv_frozen):
            raise TypeError('frozen_dist must be frozen distribtuion from \
                            scipy.stats.distributions' )
        if isinstance(frozen_dist.mean(),np.ndarray):
            shape = frozen_dist.args[0].shape
        else:
            shape = None
        random_values = (frozen_dist.ppf(random(shape)) for _ in \
                                    range(self.number_of_macros) )
        macro_generator = self._generator_set_value(var, random_values)
        self.add_macro(macro_generator)


class LatinHyperCubeMacroGenerator(MacroGenerator):
    
    def __init__(self, number_of_macros=1):
        super(self.__class__,self).__init__(number_of_macros)
        self.LHS_factors = 0
        self.lhd = np.zeros((2,100))
        
                
    def add_set_value_LHS_uniform(self, var, means, scale ) :
        dist = distributions.uniform(means-scale/2.0,scale)
        self.add_set_value_LHS(var,dist)
        if isinstance(means,np.ndarray):
            length = len(means)
        else:
            length = 1
        self.LHS_factors += length
        self.lhd = pyDOE.lhs(self.LHS_factors, samples=self.number_of_macros)


        


    def add_set_value_LHS(self, var, frozen_dist ) :
        if not isinstance(frozen_dist, distributions.rv_frozen):
            raise TypeError('frozen_dist must be frozen distribtuion from \
                            scipy.stats.distributions' )
        if isinstance(frozen_dist.mean(),np.ndarray):
            shape = frozen_dist.args[0].shape
        else:
            shape = None
        no = self.LHS_factors
        
        values = (frozen_dist.ppf(self.lhd[i , no:no+shape[0] ] ) for i in \
                                    range(self.number_of_macros) )
        macro_generator = self._generator_set_value(var, values)
        self.add_macro(macro_generator)



    
if __name__ == '__main__':
    #mb = MacroGenerator(number_of_macros= 4)
    mb = LatinHyperCubeMacroGenerator(number_of_macros= 10)
    paths = {'MODEL_TYPE':'D:/Users/Morten/Documents/GitHub/LowerExtremity-RBF-scaling/LinearScaledModel'}
    defines = {'EXCLUDE_ALL_MUSCLES':None}
    
    
    
#    mb.add_load('mymodel.main.any',defines,paths)
    mb.add_set_value_LHS_uniform('Main.study.myvar1',np.array([0.5, 2, 4]),np.array([1,1,1]))
    mb.add_set_value_LHS_uniform('Main.study.myvar2',np.array([0.1, 2, 8]),np.array([1,1,1]))
    mb.add_set_value_LHS_uniform('Main.study.myvar3',np.array([0.1, 2, 8]),np.array([1,1,1]))
    mb.add_set_value_LHS_uniform('Main.study.myvar4',np.array([0.1, 2, 8]),np.array([1,1,1]))
    mb.add_set_value_LHS_uniform('Main.study.myvar5',np.array([0.1, 2, 8]),np.array([1,1,1]))
    mb.add_set_value_LHS_uniform('Main.study.myvar6',np.array([0.1, 2, 8]),np.array([1,1,1]))
    mb.add_set_value_LHS_uniform('Main.study.myvar7',np.array([0.1, 2, 8]),np.array([1,1,1]))
    mb.add_set_value_LHS_uniform('Main.study.myvar8',np.array([0.1, 2, 8]),np.array([1,1,1]))

#    mb.add_save_design('Main.MyStudy','D:\\Users\\Morten\\Documents\\design.txt' )
    
#    mb.add_load_design('Main.MyStudy','D:\\Users\\Morten\Documents\\design.txt' )
#    mb.add_save_values('D:/Users/Morten/Documents/Values.anyset' )
#    mb.add_load_values('D:/Users/Morten/Documents/Values.anyset' )
#    mb.add_run_operation('Main.mystudy.Kinematics')
#    mb.add_set_value('Main.study.myvar1', 23)
#    mb.add_set_value('Main.study.myvar2', 23.0)
#    mb.add_set_value('Main.study.myvar3', "hallo")
#    mb.add_set_value('Main.study.myvar4', np.array([2,3,4]))
#    mb.add_set_value('Main.study.myvar5', np.array([2.3,40.0,-1.2]))
#    mb.add_dump('Main.study.MaxMuscleStrength')
#    mb.add_macro(['run', 'exit'])
    
    
    for macro_batch in mb.generate_macros(batch = 3):
        print("--------new batch --------- ")
        for macro in macro_batch:
            print("\n".join(macro))
            print(" ")
    