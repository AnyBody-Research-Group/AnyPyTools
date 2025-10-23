# -*- coding: utf-8 -*-
"""
Created on Sun Jul 06 19:09:58 2014

@author: Morten
"""
import os
from pathlib import Path

import numpy as np
import pytest

from anypytools.tools import (AnyPyProcessOutput, AnyPyProcessOutputList,
                              _parse_data, array2anyscript, define2str,
                              get_anybodycon_path, parse_anybodycon_output,
                              path2str)


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
    assert path2str("test", r"C:\hallo.txt") == '-p test=---"C:\\\\hallo.txt"'
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


def test_AnyPyProcessOutput_to_dataframe_interp():
    """Test that we can interpolate the data using 'Output.percent_var'
    from 0 to 100
    """
    time_var = np.linspace(0, 4, 200)
    data = {
        "Output.Abscissa.t": time_var,
        "Output.percent_var": np.linspace(-10, 140, len(time_var)),
        "Output.SomeData": np.sin(time_var),
        "contant": 0.38,
        "contant_str": "Hello world",
    }
    anypydata = AnyPyProcessOutput(data)
    interpolation_values = np.linspace(0, 99, 100)
    df = anypydata.to_dataframe(
        interp_var="Output.percent_var",
        interp_val=interpolation_values,
    )
    assert df.shape == (100, 5)
    assert all(df["Output.percent_var"] == interpolation_values)


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


@pytest.mark.parametrize(
    "str_val, expected, expected_dtype",
    [
        (
            """{{{0.9959166, nan, -nan}, {-0.08322453, 0.952727, -0.292207}, {0.0349831, 0.2958367, 0.9545977}},{{0.996183, -0.0689204, 0.05356734}, {0.07839193, 0.9763008, -0.2017211}, {-0.03839513, 0.2051504, 0.9779771}}}""",
            np.array([[[0.9959166, float("nan"), float("nan") ], [-0.08322453, 0.952727, -0.292207], [0.0349831, 0.2958367, 0.9545977]],[[0.996183, -0.0689204, 0.05356734], [0.07839193, 0.9763008, -0.2017211], [-0.03839513, 0.2051504, 0.9779771]]]),
            np.float64,
        ),
        (
            """{{inf, 4.0}, {3.0, -inf}}""",
            np.array([[float("inf"), 4.0],[3.0, float("-inf")]]),
            np.float64,
        ),
        (
            """{1.0, inf, 3.0}""",
            np.array([1.0, float("inf"), 3.0]),
            np.float64,
        ),
    ]
)
def test_parse_anybodydata_arrays(str_val, expected, expected_dtype):
    data_np = _parse_data(str_val)
    assert data_np.dtype == expected_dtype
    assert np.isclose(data_np, expected, equal_nan=True).all()


@pytest.mark.parametrize(
    "str_val, expected, expected_type",
    [
        ("1.0", 1.0, float),
        ('"some_str"', "some_str", str),
        ("'some_single_quoted_str'", "some_single_quoted_str", str),
        ("1", 1, int),
    ]
  )
def test_parse_anybodydata_scalars(str_val, expected, expected_type):
    out = _parse_data(str_val)
    assert isinstance(out, expected_type)
    assert out == expected


def test_parse_anybodydata_renamed():
    testfile = Path(__file__).parent / "data" / "anybodycon_output.txt"
    raw = testfile.read_text()
    
    data = parse_anybodycon_output(raw)
    assert "Main.SomeOldName" not in data
    assert "Renamed with spaces" in data

    # Ensure folder are no longer added to the output
    assert "Main.SubFolder" not in data
    # Ensure values in folders showup when exporting the folder
    assert "Main.SubFolder.SubOutput" in data

    # Ensure that Export("Main.SubFolder", "RenamedSubFolder") works too
    assert "ReNamedSubFolder.SubOutput" in data


def test_parse_anybodycon_output():
    testfile = Path(__file__).parent / "data" / "anybodycon_output.txt"
    raw = testfile.read_text()

    data = parse_anybodycon_output(raw)

    assert isinstance(data, dict)
    assert "Main.MyOutput" in data
    assert "Main.MyOutput2" in data
    assert "Main.SomeMatrix" in data
    assert "pi" not in data
    assert "Global.pi" in data

    assert isinstance(data["Main.MyOutput"], float)
    assert np.isclose(data["Main.MyOutput"], 42.0)

    assert isinstance(data["Main.MyOutput2"], np.ndarray)
    assert data["Main.MyOutput2"].shape == (3,)

    assert isinstance(data["Global.pi"], float)
    assert data["Global.pi"] == 3.1415926535897931

    assert isinstance(data["Main.SomeMatrix"], np.ndarray)
    assert data["Main.SomeMatrix"].shape == (3, 3)

    # Test parsing data added with ExtendOutput macro
    assert "hello" in data
    assert data["hello"] == "world"
    assert "number" in data
    assert data["number"] == 123
    assert "array" in data
    assert np.array_equal(data["array"], np.array([1, 2, 3]))


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    pytest.main([str("test_tools.py::test_AnyPyProcessOutputList_to_dataframe")])
