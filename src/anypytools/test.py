# -*- coding: utf-8 -*-
"""
Created on Sun Jan 22 17:20:32 2012

@author: melund
"""

import h5py_wrapper as h5py

h5f = h5py.File('C:\Users\melund\Documents\AnyBody\SC_wpgait_s6.anydata.h5')


grp = h5f['/Output/HumanModel/Scaling/GeometricalScaling/Left/LegTDRef/Patella/rDDot']
dset = h5f['/Output/HumanModel/Scaling/GeometricalScaling/Left/LegTDRef/Patella']

print grp.wrapped
print grp.file.wrapped
print grp.parent.wrapped
print dset.file.wrapped
print dset.wrapped
print dset.parent.wrapped




