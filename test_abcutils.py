# -*- coding: utf-8 -*-
"""
Created on Mon Sep 26 16:26:03 2011

@author: melund
"""

from anypytools import abcutils
from numpy import array, random
import os.path as op
testmodel = op.join( op.dirname(abcutils.__file__), 'test_models', 'Demo.Arm2D.any'   )


#==============================================================================
# RUN Sensitivity study
#==============================================================================
ap = abcutils.AnyProcess(testmodel, num_processes = 6)
out =  ap.start(inputs =  {'Main.ArmModel.Segs.LowerArm.Brachialis.sRel':
                            array([-0.1,0,0]) +  0.02* random.randn(50,1) },
               macrocmds= ['operation ArmModelStudy.InverseDynamics',\
                           'run'],
               outputs = [ 'Main.ArmModelStudy.Output.Model.Muscles.Brachialis.Activity']
              )
  
       
       
       
#==============================================================================
# PLOT data
#==============================================================================
import matplotlib.pyplot as plt 
for data in out.values()[0]:
    plt.plot(data)
#plt.axis([0,100 , 0, 1])
plt.show()