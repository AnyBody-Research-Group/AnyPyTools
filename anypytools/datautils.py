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
from scipy.interpolate import interp1d



def anydatah5_generator(folder=None, match = ''):    
    if folder is None:
        folder = os.getcwd()
    def func(item):
        return item.endswith('h5') and item.find(match)!= -1
    filelist = filter(func,  os.listdir(folder)) 
    for filename in filelist:
        try:
            with h5py.File(op.join(folder,filename)) as h5file:
                yield (h5file, filename)
        except IOError:
            pass
    

def anyouputfile_generator(folder =None, DEBUG = False):
    if folder is None:
        folder = os.getcwd()

    filelist = [_ for _ in os.listdir(folder) if _.endswith('.txt') or _.endswith('.csv')]
    
    
    def is_scinum(str):
        try:
            np.float(str)
            return True
        except ValueError:
            return False
    
    for filename in filelist:
        with open(op.join(folder,filename),'r') as csvfile:
#            try:
#                dialect = csv.Sniffer().sniff(csvfile.read(2048),delimiters=',')
#            except:
#                if DEBUG: print "problem with " +filename
#                continue
#            csvfile.seek(0)
            reader = csv.reader(csvfile, delimiter=',')   
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

def interp_percent(data, indices):
    data = np.array(data)
    data = data.squeeze()
    indices = np.array(indices)
    x = np.linspace(0,100,len(indices))
    xnew = np.arange(0,100)
    y = data[indices]   
    ipolfun = interp1d(x,y)
    return ipolfun(xnew)
    
def any_eval(string):
    string = string.split('//',1)[0]
    string  = string.split("=",1)[-1].split(";",1)[0].strip()
    
    string = string.replace('{','[')
    string = string.replace('}',']')
    return eval(string)
    
    

if __name__ == '__main__':
#    for data,header,filename in csv_trial_data('C:\Users\mel\SMIModelOutput', DEBUG= True):
#        print header
        
    outvars = ['/Output/Validation/EMG'] 
        
