# -*- coding: utf-8 -*-
"""
Created on Mon Jan 09 12:19:16 2012

@author: melund
"""
from __future__ import division

import numpy as np
import os


def findpeaks(data, minheight, axis = None):
    # Find Indx of the signal higher than min hieght   
    Indx = np.nonzero(data > minheight)[0]
    if len(Indx) == 0:
        raise NameError('No peaks are large enough')
    # Find the signal trends to detect peaks 
    trend = np.sign(np.diff(data))
    # Find flat peaks )trend == 0) and remove them  
    idx = np.nonzero(trend==0)[0]
    if len(idx)>0:
        for i in reversed(xrange(idx)):
            if trend(np.min([idx[i]+1, len(trend)])) >=0:
                trend[idx[i]]= 1
            else:
                trend[idx[i]]=-1
    # Differentiate the trend and find location 'locs' of all peaks     
    trenddiff = np.diff(trend)
    idx = np.nonzero(np.diff(trend)==-2)[0]
    # Remove locs with peaks less than min height
    locs = np.intersect1d(idx,Indx)
    pks = data[locs]
    # create plot if an axis object is provided 
    if axis is not None :
#        ax.plot(data)
#        ax.plot(data)
        ax.plot(trenddiff)
    return (pks,locs)


def find_heelstrike_from_marker(marker, sacrummarker, axis = None):
    # find dimension of working 
    marker = np.array(marker)
    sacrummarker = np.array(sacrummarker)
    # find dimention with largest variability (direction of walking) 
    dim = np.std(marker,0).argmax()  
    # Calculate the movement of marker with respect to sacrum marker
    data =  -(marker[:,dim]-sacrummarker[:,dim])
    # Find peaks of data (Where marker start moving backward)
    peak_threshold = 0.9*(np.max(data)-np.min(data))
    pks,locs = findpeaks(data-np.min(data),peak_threshold,axis = axis)
    return locs


def find_toeoff_from_marker( marker, sacrummarker, axis = None):
    marker = np.array(marker)
    sacrummarker = np.array(sacrummarker)
    # find dimention with largest variability (direction of walking) 
    dim = np.std(marker,0).argmax()  
    # Calculate the movement of marker with respect to sacrum marker
    data = (marker[:,dim]-sacrummarker[:,dim])
    # Find peaks of data (Where marker start moving forward)
    peak_threshold = 0.9*(np.max(data)-np.min(data))
    pks,locs = findpeaks(data-np.min(data),peak_threshold,axis = axis)
    # Get first peak after 'aftertime...
    return locs
            
def find_toeoff(forcedata, threshold = 5, axis = None):
    forcedata = np.array(forcedata)
    indices = np.nonzero(forcedata < -threshold)[0]       
    if len(indices) > 0:
        return int(indices[-1])   
    else:
        return len(forcedata)
    
def find_heelstrike (forcedata, threshold = 5, axis = None):
    forcedata = np.array(forcedata)
    indices = np.nonzero(forcedata < -threshold)[0]       
    if len(indices) > 0:
        return int(indices[0])     
    else:
        return 0    
    
    
def find_events(f1,f2,f3,RHeel,LHeel,RToe,LToe, Sacrum, avratio = 1, axis = None):
    # Find all Heel toe off events from forceplate data
    hs_events = np.array([find_heelstrike(f1), find_heelstrike( f2 ), find_heelstrike( f3 )]) / avratio
    to_events = np.array([find_toeoff(f1), find_toeoff( f2 ), find_toeoff( f3 )]) / avratio
       
    # Find time indices when on forceplates
    t_gaitcycle = np.min(np.diff( np.sort(hs_events) ))
    hs_fp_start = np.round(min(hs_events)-0.2*t_gaitcycle )
    hs_fp_end = np.round(max(hs_events)+0.2*t_gaitcycle )
    to_fp_start = np.round(min(to_events)-0.2*t_gaitcycle )
    to_fp_end = np.round(max(to_events)+0.2*t_gaitcycle )
    
    win_FP_hs = np.arange(hs_fp_start,hs_fp_end)
    win_FP_to = np.arange(to_fp_start,to_fp_end)

    # Get all heel strike and toe off events from kinematic data
    hs_events_kin = np.concatenate( (find_heelstrike_from_marker(RHeel,Sacrum),
                              find_heelstrike_from_marker(LHeel,Sacrum)) )
    to_events_kin = np.concatenate( (find_toeoff_from_marker(RToe,Sacrum), 
                             find_toeoff_from_marker(LToe,Sacrum)) )
                             
    #Find heelstrike and toeoff not on force plate
    hs_on_fp =  np.in1d(hs_events_kin, win_FP_hs)
    hs_events_kin =  hs_events_kin[ hs_on_fp == False ]
    to_on_fp =  np.in1d(to_events_kin, win_FP_to)
    to_events_kin =  to_events_kin[ to_on_fp == False ]

    # Detect which foot is stepping on the first forceplate
    time_fp1 = ( min(hs_events)+min(to_events) ) /2
    
    vel_rheel = np.diff(np.array(RHeel),axis=0)
    vel_lheel = np.diff(np.array(LHeel),axis=0)
    
    to_events.sort()
    hs_events.sort()
    
    if np.sqrt(sum( vel_rheel[time_fp1,:]**2)) > np.sqrt(sum( vel_lheel[time_fp1,:]**2)):        
        hs_L = hs_events[[0,2]]
        hs_R = np.array( [hs_events[1], hs_events_kin[0]] )
        to_L = to_events[[0,2]]
        to_R = np.r_[to_events_kin[to_events_kin<to_events[0]], to_events[1] ]
        first_foot_on_FP = 'Left'
    else:
        hs_R = hs_events[[0,2]]
        hs_L = np.array( [hs_events[1], hs_events_kin[0]] )
        to_R = to_events[[0,2]]
        to_L = np.r_[to_events_kin[to_events_kin<to_events[0]], to_events[1] ]
        first_foot_on_FP = 'Right'

    hs = np.sort( np.r_[hs_L,hs_R] )
    to =np.sort(  np.r_[to_L,to_R] )
    
    events = np.round( np.sort(  np.concatenate((hs,to) ) ) )
    return (first_foot_on_FP, events)

def foot_contact_times(context, f1,f2,f3,RHeel,LHeel,RToe,LToe, Sacrum, folder, avratio, axis = None):
    (foot,events) = find_events(f1,f2,f3,RHeel,LHeel,RToe,LToe, Sacrum, avratio, axis = None)
    return (int(events[0]),int(events[1]), int(events[2]), int(events[3]),
            int(events[4]), int(events[5]), int(events[6]), int(events[7]))


def events_from_h5file(h5file):
    f1 = h5file['/Output/EnvironmentModel/ForcePlate1/FzTotal']
    f2 = h5file['/Output/EnvironmentModel/ForcePlate2/FzTotal']
    f3 = h5file['/Output/EnvironmentModel/ForcePlate3/FzTotal']
    RHeel = h5file['/Output/HumanModel/BodyModel/Right/Leg/Seg/Foot/HeelNode/r']
    LHeel = h5file['/Output/HumanModel/BodyModel/Left/Leg/Seg/Foot/HeelNode/r']
    RToe = h5file['/Output/HumanModel/BodyModel/Right/Leg/Seg/Foot/BigToeNode/r']
    LToe = h5file['/Output/HumanModel/BodyModel/Left/Leg/Seg/Foot/BigToeNode/r']
    Sacrum = h5file['/Output/HumanModel/BodyModel/Trunk/SegmentsLumbar/PelvisSeg/r']
    (first_foot_on_FP, events) =  find_events(f1,f2,f3,RHeel,LHeel,RToe,LToe, Sacrum)
    events = events.astype(int)
    if first_foot_on_FP == 'Right':
        RightHeelStrike = events[[0, 4]]
        LeftToeOff = events[[1, 5]]
        LeftHeelStrike = events[[2, 6]]
        RightToeOff = events[[3, 7]]
    else:
        LeftHeelStrike = events[[0, 4]]
        RightToeOff = events[[1, 5]]
        RightHeelStrike = events[[2, 6]]
        LeftToeOff = events[[3, 7]]
    return RightHeelStrike, RightToeOff, LeftHeelStrike, LeftToeOff
    
                 
                 
        
    def __setitem__(self, item, value):
        raise NotImplementedError
        
    def __delitem__(self, item):
        raise NotImplementedError

    def keys(self):
        return self.h5file.keys()


if __name__ == "__main__":
    import testdata
    import matplotlib.pyplot as plt
    import numpy as np
    f1 = testdata.f1
    f2 = testdata.f2
    f3 = testdata.f3
    RHeel = testdata.RHeel
    LHeel = testdata.LHeel
    RToe = testdata.RToe
    LToe = testdata.LToe
    Sacral = testdata.Sacral
    
    
    fig = plt.figure()
    ax = fig.add_subplot(111)

    ret1  = foot_contact_times("",f1,f2,f3,RHeel,LHeel,RToe,LToe,Sacral, os.getcwd(), 10, axis = ax)
    side, ret1  = find_events(f1,f2,f3,RHeel,LHeel,RToe,LToe,Sacral, 10, axis = ax)
    print side
    print ret1
    ax.plot(np.array(ret1),np.zeros((len(ret1),)), 'r^' )
    ax.plot(np.array(RHeel)[:,0] )
    ax.plot(np.array(LHeel)[:,0] )
#    print 'Heelstrike: ' + str(find_heelstrike("",testdata.FzForce))
#    print 'Toeoff: ' + str(find_toeoff("",testdata.FzForce))
#    print 'ToeoffKIN: ' + str(find_heelstrike_from_marker("",testdata.HeelMarker,testdata.SacrumMarker,axis = ax, aftertime = 200))
    time = np.linspace(0,len(RHeel), len(f1))
    ax.plot(time,np.array(f1)*0.002)
    ax.plot(time,np.array(f2)*0.002)
    ax.plot(time,np.array(f3)*0.002)
    plt.show()
    
    