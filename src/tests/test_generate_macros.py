# -*- coding: utf-8 -*-
"""
Created on Sun Jul 06 19:09:58 2014

@author: Morten
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
# TEST_UNICODE_LITERALS

import pytest
import numpy as np
from scipy.stats.distributions import norm
from numpy.random import random, seed
from collections import OrderedDict

from anypytools.generate_macros import MacroGenerator, MonteCarloMacroGenerator, LatinHyperCubeMacroGenerator

@pytest.yield_fixture()
def fixture():
    mg = MacroGenerator()
    yield mg

    
class TestMacroGenerator:

    def test_add_macro(self):
        mg = MacroGenerator()
        mg.add_macro(['load "main.any"', 'operation Main.RunApplication'])
        macro = mg.generate_macros()
        assert len(macro) == 1
        assert macro[0] == ['load "main.any"', 'operation Main.RunApplication']
    
    def test_add_load(self):
        mg = MacroGenerator()
        mg.add_load('main.any')
        macros = mg.generate_macros()
        assert macros[0][0] == 'load "main.any"'
        
        mg = MacroGenerator()
        defines = {'AnyString': '"Test\\string"'}
        mg.add_load('main.any', define_kw = defines)
        macros = mg.generate_macros()
        assert macros[0][0] ==  'load "main.any" -def AnyString=---"\\"Test\\\\string\\""' 
        
        mg = MacroGenerator()
        defines = {'AnyScript': 'Main.MyStudy'}
        mg.add_load('main.any', define_kw = defines)
        macros = mg.generate_macros()
        assert macros[0][0] ==  'load "main.any" -def AnyScript="Main.MyStudy"' 
        
        
        mg = MacroGenerator()
        paths = {'testpath': 'c:\\path\\to\\something' }
        mg.add_load('main.any', path_kw=paths)
        macros = mg.generate_macros()
        assert macros[0][0] == 'load "main.any" -p testpath=---"c:\\\\path\\\\to\\\\something"' 
    
    
    def test_set_value(self):
        mg = MacroGenerator()
        mg.add_set_value('val0', 23.1)
        mg.add_set_value('val1', -0.123010929395)
        mg.add_set_value('val2', "hallo world")
        mg.add_set_value(['val3','val4'], [3.0,4])
        mg.add_set_value('val5', np.array([1,2,3,4]) )
        mg.add_set_value('val6', np.array([[1,0],[0,1]]) )
        mg.add_set_value('val7', np.array(3.2142))
        mg.add_set_value('val8', np.array("hallo world"))
        
        macro = mg.generate_macros()
        assert macro[0][0] == 'classoperation val0 "Set Value" --value="23.1"'
        assert macro[0][1] == 'classoperation val1 "Set Value" --value="-0.123010929395"'
        assert macro[0][2] == 'classoperation val2 "Set Value" --value="hallo world"'
        assert macro[0][3] == 'classoperation val3 "Set Value" --value="3"'
        assert macro[0][4] == 'classoperation val4 "Set Value" --value="4"'
        assert macro[0][5] == 'classoperation val5 "Set Value" --value="{1,2,3,4}"'
        assert macro[0][6] == 'classoperation val6 "Set Value" --value="{{1,0},{0,1}}"'
        assert macro[0][7] == 'classoperation val7 "Set Value" --value="3.2142"'
        assert macro[0][8] == 'classoperation val8 "Set Value" --value="hallo world"'

    def test_set_value_list_intput(self):
        mg = MacroGenerator(number_of_macros=3)
        mg.add_set_value('val0', [1,2,3])
        
        macro = mg.generate_macros()
        assert macro[0][0] == 'classoperation val0 "Set Value" --value="1"'
        assert macro[1][0] == 'classoperation val0 "Set Value" --value="2"'
        assert macro[2][0] == 'classoperation val0 "Set Value" --value="3"'
        
        
        
    def test_set_value_multiple(self):
        mg = MacroGenerator(number_of_macros = 3)
        mg.add_set_value('val0', [2,2.5,3])
        macros = mg.generate_macros()
        assert macros[0] == ['classoperation val0 "Set Value" --value="2"'] 
        assert macros[1] == ['classoperation val0 "Set Value" --value="2.5"'] 
        assert macros[2] == ['classoperation val0 "Set Value" --value="3"'] 

    def test_set_value_range(self):
        n_macros = 4
        mg = MacroGenerator(number_of_macros = n_macros)
        mg.add_set_value_range('testvar', 0, 3)
        macros = mg.generate_macros()
        assert macros[0] == ['classoperation testvar "Set Value" --value="0"']
        assert macros[-1] == ['classoperation testvar "Set Value" --value="3"']
        
        mg = MacroGenerator(number_of_macros = n_macros)
        mg.add_set_value_range('testvar',
                               start = np.array([[1.0,0.0],
                                                 [0.0, 1.5]]),
                               stop = np.array([[10.0,-0.5],
                                                [10.5,100.5]]) )
        macros = mg.generate_macros()
        assert macros[0] == ['classoperation testvar "Set Value" --value="{{1,0},{0,1.5}}"']
        assert macros[-1] == ['classoperation testvar "Set Value" --value="{{10,-0.5},{10.5,100.5}}"']

        
        
class TestMonteCarloMacroGenerator:

    def test_add_macro(self):
        mg = MonteCarloMacroGenerator()
        mg.add_macro(['load "main.any"', 'operation Main.RunApplication'])
        macro = mg.generate_macros()
        assert macro[0] == ['load "main.any"', 'operation Main.RunApplication']
    
    def test_add_set_value_random_norm(self):
        seed(1)
        mg = MonteCarloMacroGenerator(number_of_macros=4)
        mg.add_load('c:/MyModel/model.main.any')
        mg.add_set_value_random_norm('Main.Study.myvar', means = 2, stdvs = 0.1)
        mg.add_run_operation('Main.Study.Kinematics')
        macros = mg.generate_macros()
        
        assert len(macros) == 4
        assert macros[0][0] == 'load "c:/MyModel/model.main.any"'
        assert macros[0][1] ==  'classoperation Main.Study.myvar "Set Value" --value="2"'
        assert macros[0][2] == 'operation Main.Study.Kinematics'
        assert macros[0][3] ==  'run'
        
        assert macros[1][0] == 'load "c:/MyModel/model.main.any"'
        assert macros[1][1] == 'classoperation Main.Study.myvar "Set Value" --value="1.97904821591"'
        assert macros[1][2] == 'operation Main.Study.Kinematics'
        assert macros[1][3] == 'run'

                
        
        
        
        
        
        
class TestLHSMacroGenerator:

    def test_add_macro(self):
        mg = LatinHyperCubeMacroGenerator()
        mg.add_macro(['load "main.any"', 'operation Main.RunApplication'])
        macro = mg.generate_macros()
        assert macro[0] == ['load "main.any"', 'operation Main.RunApplication']
    
    def test_set_value(self):
        mg = LatinHyperCubeMacroGenerator()
        mg.add_set_value('val0', 23.1)
        mg.add_set_value('val1', -0.123010929395)
        mg.add_set_value('val2', "hallo world")
        mg.add_set_value(['val3','val4'], [3.0,4])
        mg.add_set_value('val5', np.array([1,2,3,4]) )
        mg.add_set_value('val6', np.array([[1,0],[0,1]]) )
        macros = mg.generate_macros()
        
        assert len(macros) == 1

        assert macros[0][0] == 'classoperation val0 "Set Value" --value="23.1"'
        assert macros[0][1] == 'classoperation val1 "Set Value" --value="-0.123010929395"'
        assert macros[0][2] == 'classoperation val2 "Set Value" --value="hallo world"'
        assert macros[0][3] == 'classoperation val3 "Set Value" --value="3"'
        assert macros[0][4] == 'classoperation val4 "Set Value" --value="4"'
        assert macros[0][5] == 'classoperation val5 "Set Value" --value="{1,2,3,4}"'
        assert macros[0][6] == 'classoperation val6 "Set Value" --value="{{1,0},{0,1}}"'
        
    def test_set_value_LHS(self):
        seed(1)
        normdist = norm( [1,3,4], [0.1,0.5,1] )
        mg = LatinHyperCubeMacroGenerator(number_of_macros=4)
        mg.add_set_value_LHS('Main.myvar1',normdist)
        mg.add_set_value_LHS('Main.myvar2', normdist)
        macros =  mg.generate_macros() 
        
        assert len(macros) == 4

        assert macros[0][0] == 'classoperation Main.myvar1 "Set Value" --value="{1,3,4}"'
        assert macros[0][1] == 'classoperation Main.myvar2 "Set Value" --value="{1,3,4}"'
        assert macros[1][0] == 'classoperation Main.myvar1 "Set Value" --value="{1.07895227633,3.41996355574,-0.0241255334168}"'
        assert macros[1][1] == 'classoperation Main.myvar2 "Set Value" --value="{1.24119096808,2.1047636289,2.00615775617}"'




if __name__ == '__main__':
    import pytest
    pytest.main(str( 'test_generate_macros.py ../anypytools/generate_macros.py --doctest-modules'))    
