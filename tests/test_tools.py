# -*- coding: utf-8 -*-
"""
Created on Sun Jul 06 19:09:58 2014

@author: Morten
"""
import os
from pathlib import Path

import pytest
import numpy as np

from anypytools.tools import (
    array2anyscript,
    get_anybodycon_path,
    define2str,
    path2str,
    AnyPyProcessOutput,
    AnyPyProcessOutputList,
)


@pytest.yield_fixture(scope="module")
def fixture():
    yield True


def test_define2str():
    assert define2str("test", 2) == '-def test="2"'
    assert define2str("Test", "Main.MyStudy") == '-def Test="Main.MyStudy"'
    assert (
        define2str("test", '"This is a string"')
        == '-def test=---"\\"This is a string\\""'
    )


def test_path2str():
    assert path2str("test", "C:\hallo.txt") == '-p test=---"C:\\\\hallo.txt"'
    assert path2str("Test", "C:/hallo.txt") == '-p Test=---"C:/hallo.txt"'


def test_array2anyscript():

    mat33 = array2anyscript(np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]]))
    assert mat33 == "{{1,0,0},{0,1,0},{0,0,1}}"

    mat31 = array2anyscript(np.array([[1, 0, 0]]))
    assert mat31 == "{{1,0,0}}"

    mat13 = array2anyscript(np.array([[1], [0], [0]]))
    assert mat13 == "{{1},{0},{0}}"

    mat3 = array2anyscript(np.array([0.333333333, -1.9999999999, 0.0]))
    assert mat3 == "{0.333333333,-1.9999999999,0}"

    str2 = array2anyscript(np.array(["hallo", "world"]))
    assert str2 == '{"hallo","world"}'


def test_AnyPyProcessOutput():
    out = AnyPyProcessOutputList(
        [
            AnyPyProcessOutput({"AAAA": 1}),
            AnyPyProcessOutput({"AAAA": 2}),
            AnyPyProcessOutput({"AAAA": 3}),
            AnyPyProcessOutput({"AAAA": 4}),
            AnyPyProcessOutput({"AAAA": 5}),
            AnyPyProcessOutput({"AAAA": 6, "ERROR": 0}),
        ]
    )

    assert len(out) == 6
    assert isinstance(out[0], AnyPyProcessOutput)

    # Test slice get
    assert len(out[1:3]) == 2
    assert isinstance(out[0:2][0], AnyPyProcessOutput)

    # Test slice set
    out[:] = [e for e in out if "ERROR" not in e]
    assert len(out) == 5

    assert isinstance(out["A"], np.ndarray)
    assert out["A"].shape == (5,)


def test_AnyPyProcessOutput_to_dataframe():
    data = {
        "Output.Abscissa.t": np.linspace(0, 1, 6),
        "int": 8,
        "float": 0.38,
        "str": "Hello world",
        "one_dim_data": np.ones(6),
        "three_dim_data": np.ones((6, 3)),
        "StringArray": np.array("Hello world"),
        "speciel_length": np.arange(5),
    }
    anypydata = AnyPyProcessOutput(data)
    df = anypydata.to_dataframe()
    assert df.shape == (6, 14)
    df2 = anypydata.to_dataframe(index_var="speciel_length")
    assert df2.shape == (5, 35)
    df3 = anypydata.to_dataframe(index_var=None)
    assert df3.shape == (1, 39)


def test_AnyPyProcessOutputList_to_dataframe():
    time_len = 6
    no_simulations = 10
    data = {
        "Output.Abscissa.t": np.linspace(0, 1, time_len),
        "three_dim_data": np.ones((time_len, 3)),
    }
    appl = AnyPyProcessOutputList(
        [AnyPyProcessOutput(data) for i in range(no_simulations)]
    )
    df = appl.to_dataframe()
    assert df.shape == (no_simulations * time_len, 4)


def test_get_anybodycon_path():
    abc = get_anybodycon_path()

    assert os.path.exists(abc)


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    pytest.main([str("test_tools.py::test_AnyPyProcessOutputList_to_dataframe")])
