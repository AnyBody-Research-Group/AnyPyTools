# -*- coding: utf-8 -*-
"""
Created on Sun Jul 06 19:09:58 2014

@author: Morten
"""
import pytest
import numpy as np
from scipy.stats.distributions import norm

from anypytools import AnyMacro
import anypytools.macro_commands as mc

# @pytest.yield_fixture()
# def fixture():
#    mg = MacroGenerator()
#    yield mg


def test_load():
    cmd = mc.Load("main.any", defs={"TEST_STR": '"Test\\string"'})
    assert cmd.get_macro(0) == 'load "main.any" -def TEST_STR=---"\\"Test\\\\string\\""'

    cmd = mc.Load("main.any", defs={"TEST_VAR": "Main.MyStudy"})
    assert cmd.get_macro(0) == 'load "main.any" -def TEST_VAR="Main.MyStudy"'

    cmd = mc.Load("main.any", paths={"TEST_PATH": "c:\\path\\to\\something"})
    assert (
        cmd.get_macro(0)
        == 'load "main.any" -p TEST_PATH=---"c:\\\\path\\\\to\\\\something"'
    )


def test_setvalue():
    c = mc.SetValue("val", 23.1)
    assert c.get_macro(0) == 'classoperation val "Set Value" --value="23.1"'

    c = mc.SetValue("val", -0.123010929395)
    assert c.get_macro(0) == 'classoperation val "Set Value" --value="-0.123010929395"'

    c = mc.SetValue("val", "hallo world")
    assert c.get_macro(0) == 'classoperation val "Set Value" --value="hallo world"'

    c = mc.SetValue("val", [3.0, 4, 5.1])
    assert c.get_macro(0) == 'classoperation val "Set Value" --value="3"'
    assert c.get_macro(1) == 'classoperation val "Set Value" --value="4"'
    assert c.get_macro(2) == 'classoperation val "Set Value" --value="5.1"'
    assert c.get_macro(3) == 'classoperation val "Set Value" --value="3"'

    c = mc.SetValue("val", np.array([1, 2, 3, 4]))
    assert c.get_macro(0) == 'classoperation val "Set Value" --value="{1,2,3,4}"'

    c = mc.SetValue("val", np.array([[1, 0], [0, 1]]))
    assert c.get_macro(0) == 'classoperation val "Set Value" --value="{{1,0},{0,1}}"'


def test_setvalue_random():
    np.random.seed(1)
    fdist = norm(2, [1, 1, 1])

    c = mc.SetValue_random("val", fdist)
    assert c.get_macro(0) == 'classoperation val "Set Value" --value="{2,2,2}"'

    mg = AnyMacro(c)
    macrolist = mg.create_macros_MonteCarlo(2)
    assert macrolist[0][0] == 'classoperation val "Set Value" --value="{2,2,2}"'
    assert (
        macrolist[1][0]
        == 'classoperation val "Set Value" --value="{1.79048215908,2.58380574427,-1.68494766954}"'
    )


def test_dump():
    c = mc.Dump("Main.Study.myvar1")
    assert c.get_macro(0) == 'classoperation Main.Study.myvar1 "Dump"'


def test_savedesign():
    c = mc.SaveDesign("Main.MyStudy.Kinematics", "c:/design.txt")
    assert (
        c.get_macro(0)
        == 'classoperation Main.MyStudy.Kinematics "Save design" --file="c:/design.txt"'
    )


def test_loaddesign():
    c = mc.LoadDesign("Main.MyStudy.Kinematics", "c:/design.txt")
    assert (
        c.get_macro(0)
        == 'classoperation Main.MyStudy.Kinematics "Load design" --file="c:/design.txt"'
    )


def test_savevalues():
    c = mc.SaveValues("c:/design.anyset")
    assert (
        c.get_macro(0) == 'classoperation Main "Save Values" --file="c:/design.anyset"'
    )


def test_savedata():
    c = mc.SaveData("Main.MyStudy", "output.anydata.h5")
    assert (
        c.get_macro(0)
        == 'classoperation Main.MyStudy.Output "Save data" --type="Deep" --file="output.anydata.h5"'
    )


def test_loadvalues():
    c = mc.LoadValues("c:/design.anyset")
    assert (
        c.get_macro(0) == 'classoperation Main "Load Values" --file="c:/design.anyset"'
    )


def test_updatevalues():
    c = mc.UpdateValues()
    assert c.get_macro(0) == 'classoperation Main "Update Values"'


def test_operationrun():
    c = mc.OperationRun("Main.MyStudy.Kinematics")
    assert c.get_macro(0) == "operation Main.MyStudy.Kinematics\nrun"


def test_macrocommand():
    c = mc.MacroCommand("My macro cmd")
    assert c.get_macro(0) == "My macro cmd"

    c = mc.MacroCommand(["c1", "c2"])
    assert c.get_macro(0) == "c1\nc2"


def test_macros():
    mcr = AnyMacro(number_of_macros=10)
    mcr.append(mc.Load("main.any"))

    macros = mcr.create_macros()

    assert macros[0][0] == 'load "main.any"'
    assert macros[1][0] == 'load "main.any"'
    assert len(macros) == 10


# def test_macro2():
# mcr = AnyMacro([
# mc.Load('main.any'),
# mc.OperationRun('Main.MyStudy.Kinematics')
# ])

# assert str(mcr) == 'kd'

if __name__ == "__main__":
    import pytest

    pytest.main(
        str("test_macros.py ../anypytools/generate_macros.py --doctest-modules")
    )
