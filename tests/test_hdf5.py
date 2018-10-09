# -*- coding: utf-8 -*-
"""
Created on Thu Dec 10 13:38:15 2015

@author: kpr
"""
import os
import shutil
import pytest
from anypytools import AnyPyProcess

demo_model_path = os.path.join(os.path.dirname(__file__), "Demo.Arm2D.any")


def setup_simple_model(tmpdir):
    shutil.copyfile(demo_model_path, str(tmpdir.join("model.main.any")))


@pytest.yield_fixture()
def init_simple_model(tmpdir):
    setup_simple_model(tmpdir)
    with tmpdir.as_cwd():
        yield tmpdir


@pytest.fixture()
def default_macro():
    macro = [
        [
            'load "model.main.any"',
            "operation Main.ArmModelStudy.InverseDynamics",
            "run",
            'classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"',
            'classoperation Main.ArmModel.GlobalRef.t "Dump"',
        ]
    ] * 5
    return macro


def test_hdf5save(tmpdir, default_macro):
    setup_simple_model(tmpdir)
    tmpdir.chdir()
    app = AnyPyProcess(keep_logfiles=True)
    app.start_macro(default_macro)

    app.save_to_hdf5("test.hdf5", "LungeTLEM1")

    assert os.path.exists("test.hdf5")


if __name__ == "__main__":
    macro = [
        [
            'load "Demo.Arm2D.any"',
            "operation Main.ArmModelStudy.InverseDynamics",
            "run",
            'classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"',
            'classoperation Main.ArmModel.GlobalRef.t "Dump"',
        ]
    ] * 5
    app = AnyPyProcess(keep_logfiles=True)
    app.start_macro(macro)

    app.save_to_hdf5("test2.hdf5", "Lunge11dec")
