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
    
    
def find_events(f1,f2,f3,RHeel,LHeel,RToe,LToe, Sacrum, avratio = 1, use_first_fp = True, axis = None):
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
        to_L = to_events[[0,2]]
        hs_R = np.array( [hs_events[1], hs_events_kin[0]] )
        to_R = np.r_[to_events_kin[to_events_kin<to_events[0]], to_events[1] ]
        first_foot_on_FP = 'Left'
    else:
        hs_R = hs_events[[0,2]]
        hs_L = np.array( [hs_events[1], hs_events_kin[0]] )
        to_R = to_events[[0,2]]
        to_L = np.r_[to_events_kin[to_events_kin<to_events[0]], to_events[1] ]
        first_foot_on_FP = 'Right'

    return (first_foot_on_FP, hs_R, hs_L, to_R, to_L)

def foot_contact_times(context, f1,f2,f3,RHeel,LHeel,RToe,LToe, Sacrum, folder, avratio, axis = None):
    (foot, hs_R, hs_L, to_R, to_L) = find_events(f1,f2,f3,RHeel,LHeel,RToe,LToe, Sacrum, avratio, axis = None)
    
    hs = np.sort( np.r_[hs_L,hs_R] )
    to =np.sort(  np.r_[to_L,to_R] )
    
    events = np.round( np.sort(  np.concatenate((hs,to) ) ) )
    
    return (int(events[0]),int(events[1]), int(events[2]), int(events[3]),
        int(events[4]), int(events[5]), int(events[6]), int(events[7]))
    

def events_from_h5file(h5file, use_first_fp = True):
    try:
        f1 = h5file['/Output/EnvironmentModel/ForcePlate1/FzTotal']
        f2 = h5file['/Output/EnvironmentModel/ForcePlate2/FzTotal']
        f3 = h5file['/Output/EnvironmentModel/ForcePlate3/FzTotal']
    except KeyError:
        f1 = h5file['/Output/ModelOptimizationModel/EnvironmentModel/ForcePlate1/FzTotal']
        f2 = h5file['/Output/ModelOptimizationModel/EnvironmentModel/ForcePlate2/FzTotal']
        f3 = h5file['/Output/ModelOptimizationModel/EnvironmentModel/ForcePlate3/FzTotal']

    # Get Foot positions
    try:
        RHeel = h5file['/Output/OptKinModel/Right/Seg/Foot/RHeel/r']
        LHeel = h5file['/Output/OptKinModel/Left/Seg/Foot/LHeel/r']
        RToe = h5file['/Output/OptKinModel/Right/Seg/Foot/RToe/r']
        LToe = h5file['/Output/OptKinModel/Left/Seg/Foot/LToe/r']
        Sacrum = h5file['/Output/OptKinModel/Trunk/Seg/Pelvis/r']
    except KeyError:
        try:
            RHeel = h5file['/Output/LegModel/Right/Seg/Foot/RHeel/r']
            LHeel = h5file['/Output/LegModel/Left/Seg/Foot/LHeel/r']
            RToe = h5file['/Output/LegModel/Right/Seg/Foot/RToe/r']
            LToe = h5file['/Output/LegModel/Left/Seg/Foot/LToe/r']
            Sacrum = h5file['/Output/LegModel/Trunk/Seg/Pelvis/r']
        except KeyError:
            try:
                RHeel = h5file['/Output/BodyModel/Right/Leg/Seg/Foot/HeelNode/r']
                LHeel = h5file['/Output/BodyModel/Left/Leg/Seg/Foot/HeelNode/r']
                RToe = h5file['/Output/BodyModel/Right/Leg/Seg/Foot/BigToeNode/r']
                LToe = h5file['/Output/BodyModel/Left/Leg/Seg/Foot/BigToeNode/r']
                Sacrum = h5file['/Output/BodyModel/Trunk/SegmentsLumbar/PelvisSeg/r']
            except KeyError:
                RHeel = h5file['/Output/HumanModel/BodyModel/Right/Leg/Seg/Foot/HeelNode/r']
                LHeel = h5file['/Output/HumanModel/BodyModel/Left/Leg/Seg/Foot/HeelNode/r']
                RToe = h5file['/Output/HumanModel/BodyModel/Right/Leg/Seg/Foot/BigToeNode/r']
                LToe = h5file['/Output/HumanModel/BodyModel/Left/Leg/Seg/Foot/BigToeNode/r']
                Sacrum = h5file['/Output/HumanModel/BodyModel/Trunk/SegmentsLumbar/PelvisSeg/r']

        
        
    (foot, RightHeelStrike, LeftHeelStrike,
     RightToeOff, LeftToeOff) =  find_events(f1,f2,f3,RHeel,LHeel,RToe,LToe, Sacrum)

    return RightHeelStrike.astype(int), RightToeOff.astype(int),\
            LeftHeelStrike.astype(int), LeftToeOff.astype(int)
    
                 
                 
        
    def __setitem__(self, item, value):
        raise NotImplementedError
        
    def __delitem__(self, item):
        raise NotImplementedError

    def keys(self):
        return self.h5file.keys()

def events_in_percent_gait(heelstrike1, heelstrike2, col_toeoff, col_heelstrike, toeoff):
    """Returns the colateral toeoff, colateral heelstrike, and toeoff in 
       percent of gait cycle given by heelstrike1 and heelstrike2. """
       
    cto = np.array(col_toeoff)
    chs = np.array(col_heelstrike)
    to = np.array(toeoff)
    hs1 = heelstrike1
    hs2 = heelstrike2

    cto = cto[cto > hs1]
    cto = cto[cto < hs2][0:1]
    chs = chs[chs > hs1]
    chs = chs[chs < hs2][0:1]
    to = to[to > hs1]
    to = to[to < hs2][0:1]
    cto_percent = 100*(cto-hs1)/float(hs2-hs1)
    chs_percent = 100*(chs-hs1)/float(hs2-hs1)
    to_percent = 100*(to-hs1)/float(hs2-hs1)
    
    if len(cto_percent) ==0:
        return None
    
    return (cto_percent, chs_percent, to_percent)

    


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
    
    