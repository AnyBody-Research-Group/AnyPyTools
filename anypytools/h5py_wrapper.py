# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 11:40:42 2012

@author: mel
"""
from h5py import Group as BaseGroup, Dataset as BaseDataset, File as BaseFile
from h5py import *

class File(BaseFile):
    def __init__(self,arg):
         super(File, self).__init__(arg)
         self.wrapped = True
     
    def __getitem__(self,path):
        try:
            elem = super(File, self).file[path]
        except KeyError:
            elem = self
            levels = path.strip('/').split('/')
            for level in levels:
                if level in elem:
                    elem = elem.__getitem__(level)
                else:
                    try:
                        completename = elem.attrs['CompleteName'].replace('.','/')
                        reftarget = elem.attrs['RefTarget'].replace('.','/')
                        prefix = completename[:-len(elem.name)]
                        h5target = reftarget[len(prefix):]
                        newpath = h5target + '/' + level
                        elem = super(File, self).file[newpath]
                    except:
                        raise KeyError('Entry not found: '+path    )
        if isinstance(elem, BaseGroup):
            return Group(elem.id)
        elif isinstance(elem, BaseDataset):
            return Dataset(elem.id)
        elif isinstance(elem,BaseFile):
            return File(elem.id)
          
    @property
    def file(self):   
        id = super(File,self).file.id
        return File(id)
 
    @property
    def parent(self):   
        id = super(File,self).parent.id
        return Group(id)
          
          
class Group(BaseGroup):
    def __init__(self,arg):
        super(Group, self).__init__(arg)
        self.wrapped = True
 
    def __getitem__(self,path):
        try:
            elem = super(Group, self).__getitem__(path)
        except KeyError:
            elem = self
            levels = path.strip('/').split('/')
            for level in levels:
                if level in elem:
                    elem = elem.__getitem__(level)
                else:
                    try:
                        completename = elem.attrs['CompleteName'].replace('.','/')
                        reftarget = elem.attrs['RefTarget'].replace('.','/')
                        prefix = completename[:-len(elem.name)]
                        h5target = reftarget[len(prefix):]
                        newpath = h5target + '/' + level
                        elem = super(Group, self).file[newpath]
                    except:
                        raise KeyError('Entry not found: '+path    )
        if isinstance(elem, BaseGroup):
            return Group(elem.id)
        elif isinstance(elem, BaseDataset):
            return Dataset(elem.id)
        elif isinstance(elem,BaseFile):
            return File(elem.id)
            
    @property
    def file(self):   
        id = super(Group,self).file.id
        return File(id)
    
    @property
    def parent(self):   
        id = super(Group,self).parent.id
        return Group(id)


class Dataset(BaseDataset):
    def __init__(self,arg):
        super(Dataset, self).__init__(arg)
        self.wrapped = True
    
    @property
    def file(self):   
        id = super(Dataset,self).file.id
        return File(id)
    
    @property
    def parent(self):   
        id = super(Dataset,self).parent.id
        return Group(id)

if __name__ == '__main__':
#    for data,header,filename in csv_trial_data('C:\Users\mel\SMIModelOutput', DEBUG= True):
#        print header
        
    outvars = ['/Output/Validation/EMG'] 
        
    for data, filename in h5_trial_data(outvars):
        print data.keys()