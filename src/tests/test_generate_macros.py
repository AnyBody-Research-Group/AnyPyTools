# -*- coding: utf-8 -*-
"""
Created on Sun Jul 06 19:09:58 2014

@author: Morten
"""
from __future__ import division, absolute_import, print_function, unicode_literals
from anypytools.utils.py3k import * # @UnusedWildImport
import pytest
import numpy as np

from anypytools.generate_macros import MacroGenerator, MonteCarloMacroGenerator, LatinHyperCubeMacroGenerator

@pytest.yield_fixture()
def macro_gen():
    mg = MacroGenerator()
    yield mg

    
class TestMacroGenerator:

    def test_add_macro(self, macro_gen):
        macro_gen.add_macro(['load "main.any"', 'operation Main.RunApplication'])
        macro = macro_gen.generate_macros()
        assert macro[0] == ['load "main.any"', 'operation Main.RunApplication']
    
    def test_set_value(self,macro_gen):
        macro_gen.add_set_value('val0', 23.1)
        macro_gen.add_set_value('val1', -0.123010929395)
        macro_gen.add_set_value('val2', "hallo world")
        macro_gen.add_set_value(['val3','val4'], [3.0,4])
        macro = macro_gen.generate_macros()
        assert macro[0][0] == 'classoperation val0 "Set Value" --value="23.1"'
        assert macro[0][1] == 'classoperation val1 "Set Value" --value="-0.123010929395"'
        assert macro[0][2] == 'classoperation val2 "Set Value" --value="hallo world"'
        assert macro[0][3] == 'classoperation val3 "Set Value" --value="3"'
        assert macro[0][4] == 'classoperation val4 "Set Value" --value="4"'

    def test_set_value_multiple(self):
        macro_gen = MacroGenerator(number_of_macros = 3)
        macro_gen.add_set_value('val0', [2,2.5,3])
        macros = macro_gen.generate_macros()
        assert macros[0] == ['classoperation val0 "Set Value" --value="2"'] 
        assert macros[1] == ['classoperation val0 "Set Value" --value="2.5"'] 
        assert macros[2] == ['classoperation val0 "Set Value" --value="3"'] 
