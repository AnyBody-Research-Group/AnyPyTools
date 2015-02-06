# -*- coding: utf-8 -*-
"""
Created on Sun Jul 06 19:09:58 2014

@author: Morten
"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *

import os
import shutil
import pytest
import numpy as np

from copy import deepcopy

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
    def test_logfile_persistance(self, init_simple_model, default_macro) :
        app = AnyPyProcess(disp = False, keep_logfiles=True, 
                           return_task_info=True)
        output = app.start_macro(default_macro)
        assert os.path.isfile(output[0]['task_logfile'])

    
    def test_macro_with_erros(self,init_simple_model, default_macro):
        app = AnyPyProcess(disp = False, return_task_info=True, 
                           ignore_errors = ['Unresolved object'])
        macro = [ ['load "model.main.any"'
                  ,'operation Main.ArmModelStudy.InverseDynamics'
                  ]
                , ['load "model.main.any"'
                  , 'operation Main.NonExistentOpeation'
                  ]
                , ['load "not_a_model.any"'
                  , 'operation Main.ArmModelStudy.InverseDynamics'
                  ]
                ]
             
        
        output = app.start_macro(macro)
    
        assert not 'ERROR' in output[0]
        assert not 'ERROR' in output[1]
        assert 'ERROR' in output[2]
    
    def test_start_macro(self,init_simple_model, default_macro):
        app = AnyPyProcess(disp = False)
        
        default_macro[0].extend(['classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"', 
                         'classoperation Main.ArmModel.GlobalRef.t "Dump"'])
        
        output = app.start_macro(default_macro)
        
        assert len(output) == 1
        assert 'Main.ArmModelStudy.Output.MaxMuscleActivity' in output[0]
        assert 'Main.ArmModel.GlobalRef.t' in output[0]
        assert 'ERROR' not in output[0]
        
    def test_start_macro_with_task_info(self,init_simple_model, default_macro):
        app = AnyPyProcess(disp = False, return_task_info=True)
        
        default_macro[0].extend(['classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"', 
                         'classoperation Main.ArmModel.GlobalRef.t "Dump"'])
        
        output = app.start_macro(default_macro,)
        
        assert len(output) == 1
        assert 'task_macro_hash' in output[0]
        assert 'task_id' in output[0]
        assert 'task_work_dir' in output[0]
        assert 'task_name' in output[0]
        assert 'task_processtime' in output[0]
        assert 'task_macro' in output[0]
        assert 'task_logfile' in output[0]
        
        
    def test_start_macro_subdirs(self, tmpdir, default_macro ):
        number_of_models = 5
        setup_models_in_subdirs(tmpdir, number_of_models)   
        
        app = AnyPyProcess(disp = False )
        with tmpdir.as_cwd():
            output = app.start_macro(default_macro,search_subdirs='main.any')
    
        assert len(output) == number_of_models
        for result in output:
            assert 'ERROR' not in result
        
    def test_start_macro_generator_input(self, init_simple_model, default_macro):
        n_macros = 5
        def generate_macros():
            """Generator that returns macros
            """
            for i in range(n_macros):
                yield default_macro[0]
        
        app = AnyPyProcess(disp = False)
        macros_gen = generate_macros()
        output = app.start_macro(macros_gen )
        
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
            
        
    def test_output_convert_data(self,init_simple_model):
        macro = [['load "model.main.any"',
                 'operation Main.ArmModelStudy.InverseDynamics',
                 'classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"', 
                 'classoperation Main.ArmModel.GlobalRef.t "Dump"'], 
                 ['load "model.main.any"',
                 'operation Main.ArmModelStudy.InverseDynamics',
                 'classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"', 
                 'classoperation Main.ArmModel.GlobalRef.t "Dump"'],
		     ['load "model.main.any"',
                 'operation Main.ArmModelStudy.InverseDynamics',
                 'classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"', 
                 'classoperation Main.ArmModel.GlobalRef.t "Dump"']]
        
        from anypytools.utils import blaze_converter
        from into import into
        from dynd import nd
        
        app = AnyPyProcess(return_task_info=True)

        output = app.start_macro(macro)
        out1 = into(nd.array, deepcopy(output))
        assert hasattr(out1, 'Main_ArmModelStudy_Output_MaxMuscleActivity')        
        assert hasattr(out1, 'Main_ArmModel_GlobalRef_t')
        
        out2 = into(nd.array, deepcopy(output), create_nested_structure = True)
        assert hasattr(out2, 'Main')        
        assert hasattr(out2.Main.ArmModel.GlobalRef, 't')        
        
        
        
        
    def test_restart_macro(self,init_simple_model):
        macro = [['load "model.main.any"',
                 'classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"', 
                 'classoperation Main.ArmModel.GlobalRef.t "Dump"'],
                 ['load "model.main.any"',
                 'classoperation Main.ArmModelStudy.Output.MaxMuscleActivity "Dump"', 
                 'classoperation Main.ArmModel.GlobalRef.t "Dump"']]
        
        app = AnyPyProcess(return_task_info=True)

        output = app.start_macro(macro)
        output = app.start_macro()

        
        output[0]['ERROR'] = ['SOME ERROR']
        
        output = app.start_macro(output)
        
        for result in output:
            assert 'ERROR' not in result

        
        
        
if __name__ == '__main__':
    pytest.main(str( 'test_abcutils.py'))    
