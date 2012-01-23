# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 11:40:42 2012

@author: mel
"""
import os.path as op
import csv
import numpy as np
import os
import h5py_wrapper as h5py


def anydatah5_generator(folder=None, DEBUG = False):
#    # Change Anybody tree-path to hdf5 path 
#    if not isinstance(varlist, list):
#        varlist = [varlist]
#    for idx,val in enumerate(varlist):
#        val = val.split('Output',1)[1]
#        val = '/Output'+val.replace('.','/')
#        varlist[idx] = val    
    
    if folder is None:
        folder = os.getcwd()
    filelist = [_ for _ in os.listdir(folder) if _.lower().endswith('h5')]
    for filename in filelist:
        try:
            with h5py.File(op.join(folder,filename)) as h5file:
                yield (h5file, filename)
        except IOError:
            pass
    

def anyouputfile_generator(folder =None, DEBUG = False):
    if folder is None:
        folder = os.getcwd()
    filelist = os.listdir(folder)
    
    
    def is_scinum(str):
        try:
            np.float(str)
            return True
        except ValueError:
            return False
    
    for filename in filelist:
        with open(op.join(folder,filename),'r') as csvfile:
            try:
                dialect = csv.Sniffer().sniff(csvfile.read(2048))
            except:
                if DEBUG: print "problem with " +filename
                continue
            csvfile.seek(0)
            reader = csv.reader(csvfile, dialect)   
            #Check when the header section ends
            fpos1 = 0
            fpos0 = 0
            for row in reader:
                if is_scinum(row[0]):
                    break
                fpos1 = fpos0
                fpos0 = csvfile.tell()
            else:
                if DEBUG: print "No numeric data in " +filename
                break
            # Read last line of the header section if there is a header
            if fpos0 != 0:
                csvfile.seek(fpos1)
                header = [_.rsplit('.',2)[-1] for _ in reader.next()]
            else:
                header = None
            data = np.array([[float(col) for col in row] for row in reader])
            yield (data,header, op.splitext(filename)[0])

if __name__ == '__main__':
#    for data,header,filename in csv_trial_data('C:\Users\mel\SMIModelOutput', DEBUG= True):
#        print header
        
    outvars = ['/Output/Validation/EMG'] 
        
    for data, filename in h5_trial_data(outvars):
        print data.keys()