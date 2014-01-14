# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 11:40:42 2012

@author: mel
"""
from h5py import Group as BaseGroup, Dataset as BaseDataset, File as BaseFile
from h5py import *

def _follow_reftarget(elem):
    completename = elem.attrs['CompleteName'].replace('.','/')
    reftarget = elem.attrs['RefTarget'].replace('.','/')
    prefix = completename[:-len(elem.name)]
    h5target = reftarget[len(prefix):]
    elem = elem.file[h5target]
    return elem


def _check_input_path(path):
    if not "/" in path:
        # path does not have traditional h5 format.
        if path.startswith('Main.') and 'Output' in path:
            path = '/Output' + path.split('Output')[-1]
        path = path.replace('.', '/')
    return path
    

class File(BaseFile):
    def __init__(self,arg):
         super(File, self).__init__(arg)
         self.wrapped = True
     
    def __getitem__(self,path):
        path = _check_input_path(path)
        try:
            elem = super(File, self).file[path]
            if isinstance(elem, BaseGroup) and not len(elem.keys()):
                if 'RefTarget' in elem.attrs:
                    elem = _follow_reftarget(elem)
        except KeyError:
            elem = super(type(self),self)
            levels = path.strip('/').split('/')
            for level in levels:
                if elem.__contains__(level):
                    elem = elem.__getitem__(level)
                else:
                    try:
                        elem = _follow_reftarget(elem)
                        elem = elem.__getitem__(level)
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

        
    def __contains__(self, name):
        """ Test if a member name exists """
        if super(File, self).__contains__(name):
            return True
        else:
            try:
                self.__getitem__(name)
                return True
            except KeyError:
                pass
        return False

          
class Group(BaseGroup):
    def __init__(self,arg):
        super(Group, self).__init__(arg)
        self.wrapped = True
 
    def __getitem__(self,path):
        path = _check_input_path(path)
        try:
            elem = super(Group, self).__getitem__(path)
            if isinstance(elem, BaseGroup) and not len(elem.keys()):
                if 'RefTarget' in elem.attrs:
                    elem = _follow_reftarget(elem)            
        except KeyError:
            elem = super(type(self),self)
            levels = path.strip('/').split('/')
            for level in levels:
                if elem.__contains__(level):
                    elem = elem.__getitem__(level)
                else:
                    try:
                        elem = _follow_reftarget(elem)
                        elem = elem.__getitem__(level)
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

    def __contains__(self, name):
        """ Test if a member name exists """
        if super(Group, self).__contains__(name):
            return True
        else:
            try:
                self.__getitem__(name)
                return True
            except KeyError:
                pass
        return False

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