# -*- coding: utf-8 -*-
"""

"""
from anypytools import h5py_wrapper


def test_file():

    with h5py_wrapper.File('test.anydata.h5') as f:
        t1 = f['/Output/MomentArm'] # Standard h5py notation
        t2 = f['Output.MomentArm']  # dot notation
        t3 = f['Main.MyStudy.Output.Model.Knee.Pos'] # dot notation with full path


def test_group():
    with h5py_wrapper.File('test.anydata.h5') as f:
        h5group = f['/Output']
        t1 = h5group['MomentArm'] # Standard h5py notation
        t2 = h5group['Model/Knee/Pos']
        t3 = h5group['Model.Knee.Pos']