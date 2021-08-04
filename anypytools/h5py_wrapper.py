# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 11:40:42 2012.

@author: mel
"""
import logging

import h5py

logger = logging.getLogger("abt.anypytools")


def _follow_reftarget(elem):
    completename = elem.attrs["CompleteName"]
    completename = completename.replace(b".", b"/")
    reftarget = elem.attrs["RefTarget"].replace(b".", b"/")
    prefix = completename[: -len(elem.name)]
    h5target = reftarget[len(prefix) :]
    elem = elem.file[h5target]
    return elem


def _check_input_path(path):
    """Convert dot notation to stardard h5py path."""
    if "/" not in path:
        # path does not have traditional h5 format.
        if path.startswith("Main.") and "Output" in path:
            path = "/Output" + path.split("Output")[-1]
        path = path.replace(".", "/")
    return path


class File(h5py.File):  # noqa

    __doc__ = h5py.File.__doc__

    def __init__(self, *args, **kwargs):  # noqa
        super(File, self).__init__(*args, **kwargs)
        self.wrapped = True

    def __getitem__(self, path):  # noqa
        """."""
        path = _check_input_path(path)
        try:
            elem = super(File, self).file[path]
            if isinstance(elem, h5py.Group) and not len(elem.keys()):
                if "RefTarget" in elem.attrs:
                    elem = _follow_reftarget(elem)
        except KeyError:
            elem = super(type(self), self)
            levels = path.strip("/").split("/")
            for level in levels:
                if elem.__contains__(level):
                    elem = elem.__getitem__(level)
                else:
                    try:
                        elem = _follow_reftarget(elem)
                        elem = elem.__getitem__(level)
                    except Exception:
                        raise KeyError("Entry not found: " + path)
        if isinstance(elem, h5py.Group):
            return Group(elem.id)
        elif isinstance(elem, h5py.Dataset):
            return Dataset(elem.id)
        elif isinstance(elem, h5py.File):
            return File(elem.id)

    @property
    def file(self):  # noqa
        id = super(File, self).file.id
        return File(id)

    @property
    def parent(self):  # noqa
        id = super(File, self).parent.id
        return Group(id)

    def __contains__(self, name):  # noqa
        """Test if a member name exists"""
        if super(File, self).__contains__(name):
            return True
        else:
            try:
                self.__getitem__(name)
                return True
            except KeyError:
                pass
        return False


class Group(h5py.Group):  # noqa

    __doc__ = h5py.Group.__doc__

    def __init__(self, arg):  # noqa
        super(Group, self).__init__(arg)
        self.wrapped = True

    def __getitem__(self, path):  # noqa
        path = _check_input_path(path)
        try:
            elem = super(Group, self).__getitem__(path)
            if isinstance(elem, h5py.Group) and not len(elem.keys()):
                if "RefTarget" in elem.attrs:
                    elem = _follow_reftarget(elem)
        except KeyError:
            elem = super(type(self), self)
            levels = path.strip("/").split("/")
            for level in levels:
                if elem.__contains__(level):
                    elem = elem.__getitem__(level)
                else:
                    try:
                        elem = _follow_reftarget(elem)
                        elem = elem.__getitem__(level)
                    except Exception:
                        raise KeyError("Entry not found: " + path)
        if isinstance(elem, h5py.Group):
            return Group(elem.id)
        elif isinstance(elem, h5py.Dataset):
            return Dataset(elem.id)
        elif isinstance(elem, h5py.File):
            return File(elem.id)

    @property
    def file(self):  # noqa
        id = super(Group, self).file.id
        return File(id)

    @property
    def parent(self):  # noqa
        id = super(Group, self).parent.id
        return Group(id)

    def __contains__(self, name):  # noqa
        """Test if a member name exists"""
        if super(Group, self).__contains__(name):
            return True
        else:
            try:
                self.__getitem__(name)
                return True
            except KeyError:
                pass
        return False


class Dataset(h5py.Dataset):  # noqa
    __doc__ = h5py.Dataset.__doc__

    def __init__(self, arg):  # noqa
        super(Dataset, self).__init__(arg)
        self.wrapped = True

    @property
    def file(self):  # noqa
        id = super(Dataset, self).file.id
        return File(id)

    @property
    def parent(self):  # noqa
        id = super(Dataset, self).parent.id
        return Group(id)
