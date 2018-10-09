# -*- coding: utf-8 -*-
"""
Created on Mon Jan 16 11:40:42 2012.

@author: mel
"""
import os
import re
import logging
import warnings
import os.path as op
from ast import literal_eval

import numpy as np

logger = logging.getLogger("abt.anypytools")

__all__ = ["anydatah5_generator", "anyoutputfile_generator", "read_anyoutputfile"]


def anydatah5_generator(folder=None, match=r".*(\.h5)"):
    r"""Create a generator which opens anydata.h5 files.

    Parameters
    ----------
    folder : str, optional
        path of the directory to look for anydata.h5 files. Defaults is the
        current working directory
    match : str
        regular expression to match with filenames. Default is to include
        file ending with .h5 '.*(\.h5)'

    Yields
    -------
    h5py_file : array_like
        a h5_py file opened with anypytools.h5py_wrapper
    filename : str
        name of the file from which the data was read


    Examples
    --------
    >>> for (h5, filename) in anydatah5_generator():
            print(h5)

    """
    from . import h5py_wrapper

    if folder is None:
        folder = str(os.getcwd())

    def func(item):
        return re.match(item, match, flags=re.IGNORECASE)

    filelist = filter(func, os.listdir(folder))
    for filename in filelist:
        try:
            with h5py_wrapper.File(op.join(folder, filename)) as h5file:
                yield (h5file, filename)
        except IOError:
            pass


def anyoutputfile_generator(folder=None, match=".*\.(csv|txt)"):
    """Create a generator which opens AnyOutput files.

    Parameters
    ----------
    folder : str, optional
        path of the directory to look for AnyOutput files. Defaults is the
        current working directory
    match : str
        regular expression to match with filenames. Default is to include
        file ending with .csv or .txt '.*(.csv|.txt)'

    Yields
    -------
    data : array_like
        data collumns  in the anyoutput file
    header : list
        list of the collumn names
    constants : dict
        mapping with constants found in the file
    filename : str
        name of the file from which the data was read


    Examples
    --------
    >>> for (data, header, const, fn) in anyoutputfile_generator():
            print(fn)
            print(header)
            print(data.shape)

    """
    if folder is None:
        folder = str(os.getcwd())

    def func(item):
        return re.match(item, match, flags=re.IGNORECASE)

    filelist = filter(func, os.listdir(folder))

    for filename in filelist:
        filepath = op.join(folder, filename)
        data, header, const = open_anyoutputfile(filepath)
        if data is None:
            continue

        yield (data, header, const, os.path.basename(filepath))


def open_anyoutputfile(filepath):
    warnings.warn(
        "Deprecated: open_anyoutputfile is renamed to " "read_anyoutputfile",
        DeprecationWarning,
    )
    return read_anyoutputfile(filepath)


def _is_scinum(str):
    """Check if a string is a number acording to numpy."""
    try:
        np.float(str)
        return True
    except ValueError:
        return False


def read_anyoutputfile(filepath):
    """Read an AnyOutput file.

    Parameters
    ----------
    filepath : str


    Returns
    -------
    data : array_like
        data collumns  in the anyoutput file
    header : list
        list of the collumn names
    constants : dict
        mapping with constants found in the file


    """
    with open(filepath, "rU") as anyoutputfile:
        constants = {}
        reader = iter(anyoutputfile.readline, b"")
        # Check when the header section ends
        fpos1 = 0
        fpos0 = 0
        for row in reader:
            if _is_scinum(row.split(",")[0]):
                break
            # Save constant from AnyOutput file
            const, value = _parse_anyoutputfile_constants(row)
            if const is not None:
                constants[const] = value
            fpos1, fpos0 = fpos0, anyoutputfile.tell()
        else:
            warnings.warn("No numeric data in " + os.path.basename(filepath))
            return (None, None, constants)
        # Read last line of the header section if there is a header
        if fpos0 != 0:
            anyoutputfile.seek(fpos1)
            header = next(reader).strip("\n").split(",")
        else:
            header = None

        data = []
        for row in reader:
            try:
                data.append([float(val) for val in row.strip("\n").split(",")])
            except ValueError:
                break
        data = np.array(data)
    return (data, header, constants)


def _parse_anyoutputfile_constants(strvar):
    value = None
    varname = None
    if strvar.count("=") == 1 and strvar.startswith("Main"):
        (first, last) = strvar.split("=")
        varname = first.strip()
        last = last.strip()
        value = None
        last = last.strip("\n")
        if last.find("{") == -1:
            try:
                value = str(literal_eval("'''" + last + "'''"))
                value = str(literal_eval(last))
                value = float(literal_eval(last))
            except Exception:
                pass
        else:
            last = last.replace("{", "[").replace("}", "]")
            try:
                value = np.array(literal_eval("'''" + last + "'''"))
                value = np.array(literal_eval(last))
            except Exception:
                pass
    return (varname, value)
