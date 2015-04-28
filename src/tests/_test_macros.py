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

from anypytools.macroutils import (Macros, MacroCommand, Load, SetValue, 
                                    Dump, SaveDesign, LoadDesign, SaveValues, 
                                    LoadValues, UpdateValues, OperationRun)

#@pytest.yield_fixture()
#def fixture():
#    mg = MacroGenerator()
#    yield mg

    
def test_load():
    cmd = Load('main.any', defs =  {'AnyString': '"Test\\string"'} )
    assert cmd.get_macro(0) == 'load "main.any" -def AnyString=---"\\"Test\\\\string\\""'

    cmd = Load('main.any', defs =  {'AnyScript': 'Main.MyStudy'} )
    assert cmd.get_macro(0) == 'load "main.any" -def AnyScript="Main.MyStudy"' 

    cmd = Load('main.any', paths = {'testpath': 'c:\\path\\to\\something' })
    assert cmd.get_macro(0) == 'load "main.any" -p testpath=---"c:\\\\path\\\\to\\\\something"' 
    
def test_setvalue():
    c = SetValue('val', 23.1)
    assert c.get_macro(0)  == 'classoperation val "Set Value" --value="23.1"'

    c = SetValue('val', -0.123010929395)
    assert c.get_macro(0)  == 'classoperation val "Set Value" --value="-0.123010929395"'

    c = SetValue('val', "hallo world")
    assert c.get_macro(0)  == 'classoperation val "Set Value" --value="hallo world"'

    c = SetValue('val', [3.0,4,5.1])
    assert c.get_macro(0)  == 'classoperation val "Set Value" --value="3"'
    assert c.get_macro(1)  == 'classoperation val "Set Value" --value="4"'
    assert c.get_macro(2)  == 'classoperation val "Set Value" --value="5.1"'
    assert c.get_macro(3)  == 'classoperation val "Set Value" --value="3"'


    c = SetValue('val', np.array([1,2,3,4]))
    assert c.get_macro(0)  == 'classoperation val "Set Value" --value="{1,2,3,4}"'
    
    c = SetValue('val', np.array([[1,0],[0,1]]) )
    assert c.get_macro(0)  == 'classoperation val "Set Value" --value="{{1,0},{0,1}}"'
    

def test_dump():
    c = Dump('Main.Study.myvar1')
    assert c.get_macro(0) == 'classoperation Main.Study.myvar1 "Dump"'


def test_savedesign():
    c = SaveDesign('Main.MyStudy.Kinematics', 'c:/design.txt')
    assert c.get_macro(0) == 'classoperation Main.MyStudy.Kinematics "Save design" --file="c:/design.txt"'

def test_loaddesign():
    c = LoadDesign('Main.MyStudy.Kinematics', 'c:/design.txt')
    assert c.get_macro(0) == 'classoperation Main.MyStudy.Kinematics "Load design" --file="c:/design.txt"'

def test_savevalues():
    c = SaveValues('c:/design.anyset')
    assert c.get_macro(0) == 'classoperation Main "Save Values" --file="c:/design.anyset"'

def test_loadvalues():
    c = LoadValues('c:/design.anyset')
    assert c.get_macro(0) == 'classoperation Main "Load Values" --file="c:/design.anyset"'

def test_updatevalues():
    c = UpdateValues()
    assert c.get_macro(0) == 'classoperation Main "Update Values"'

def test_operationrun():
    c = OperationRun('Main.MyStudy.Kinematics')
    assert c.get_macro(0) == 'operation Main.MyStudy.Kinematics\nrun'


def test_macrocommand():
    c = MacroCommand('My macro cmd')
    assert c.get_macro(0) == 'My macro cmd'
    
    c = MacroCommand(['c1', 'c2'])
    assert c.get_macro(0) == 'c1\nc2'
    
    
    
    

def test_macros():
    mcr = Macros(number_of_macros = 10)
    mcr.append(Load('main.any'))
    
    macros = mcr.build()
    
    assert macros[0][0] == 'load "main.any"'
    assert macros[1][0] == 'load "main.any"'
    assert len(macros) == 10

def test_macro2():
    mcr = Macros([
                    Load('main.any'),
                    OperationRun('Main.MyStudy.Kinematics')
                    ])
    
    assert str(mcr) == 'kd'

if __name__ == '__main__':
    import pytest
    pytest.main(str( 'test_macros.py ../anypytools/generate_macros.py --doctest-modules'))    
