# -*- coding: utf-8 -*-
"""
Created on Sun Jul 06 19:09:58 2014

@author: Morten
"""
from __future__ import division, absolute_import, print_function, unicode_literals
from anypytools.utils.py3k import * # @UnusedWildImport
import os
import shutil
import pytest
import numpy as np

from anypytools.abcutils import AnyPyProcess

demo_model_path = os.path.join(os.path.dirname(__file__), 'Demo.Arm2D.any')

def setup_simple_model(tmpdir):
    shutil.copyfile(demo_model_path, str( tmpdir.join('model.main.any') ) )
    
def setup_models_in_subdirs(tmpdir,number_of_models = 5):
    for i in range(number_of_models):
        subdir = tmpdir.mkdir('model'+str(i))
        setup_simple_model(subdir)

    
@pytest.yield_fixture()
def init_simple_model(tmpdir):
    setup_simple_model( tmpdir ) 
    with tmpdir.as_cwd():
        yield tmpdir
       

@pytest.yield_fixture()
def default_macro():   
    macro = [['load "model.main.any"',
              'operation Main.ArmModelStudy.InverseDynamics' ]]
    yield macro

    
class TestAnyPyProcess():
    def test_start_macro(self,init_simple_model, default_macro):
        app = AnyPyProcess()
        
        default_macro[0].extend(['classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"', 
                         'classoperation Main.ArmModel.GlobalRef.t "Dump"'])
        
        output = app.start_macro(default_macro)
        
        assert len(output) == 1
        assert 'Main.ArmModelStudy.Output.MaxMuscleActivity' in output[0]
        assert 'Main.ArmModel.GlobalRef.t' in output[0]
        assert 'ERROR' not in output[0]
        
    def test_start_macro_subdirs(self, tmpdir, default_macro ):
        number_of_models = 5
        setup_models_in_subdirs(tmpdir, number_of_models)   
        
        app = AnyPyProcess( )
        with tmpdir.as_cwd():
            output = app.start_macro(default_macro,search_subdirs='main.any')
    
        assert len(output) == number_of_models
        for result in output:
            assert 'ERROR' not in result
        
    def test_start_macro_generator_input(self, init_simple_model, default_macro):
        n_macros = 5
        def generate_macros():
            for i in range(n_macros):
                yield default_macro[0]
        
        app = AnyPyProcess()
        macros_gen = generate_macros()
        output = app.start_macro(macros_gen, number_of_macros= n_macros )
        
        assert len(output) == n_macros
        for result in output:
            assert 'ERROR' not in result
        
    def test_start_macro_multple_folders_and_macros(self, tmpdir, default_macro):
        number_of_models = 3
        number_of_macros = 3
        setup_models_in_subdirs(tmpdir, number_of_models)   
        folderlist = [str(_) for _ in tmpdir.listdir() ]
        macrolist = default_macro*number_of_macros

        
        with tmpdir.as_cwd():
            app = AnyPyProcess()
            output = app.start_macro(macrolist, folderlist)
        
        assert len(output) == len(folderlist)*len(macrolist)
        for result in output:
            assert 'ERROR' not in result
            
        
        
        
if __name__ == '__main__':
    test_list2anyscript() 