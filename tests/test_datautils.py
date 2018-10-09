# -*- coding: utf-8 -*-
"""
Created on Wed Sep  3 11:03:41 2014

@author: Morten
"""
from anypytools.datautils import read_anyoutputfile


def test_open_anyoutputfile(request):
    testfile = str(request.fspath.new(basename="any_output_file.txt"))
    data, header, constants = read_anyoutputfile(testfile)

    assert constants["Main.Studies.ElbowExtension.Outputfile.SepSign"] == ","
    assert (
        constants["Main.Studies.ElbowExtension.Outputfile." "NumberFormat.FormatStr"]
        == "%22.15e"
    )

    assert "Main.Studies.ElbowExtension.IterationStep" in header

    assert data.shape == (27, 12)
