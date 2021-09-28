# -*- coding: utf-8 -*-
"""AnyPyTools library."""
import os
import sys
import platform
import logging

if "FOR_DISABLE_CONSOLE_CTRL_HANDLER" not in os.environ:
    os.environ["FOR_DISABLE_CONSOLE_CTRL_HANDLER"] = "1"

from anypytools.abcutils import AnyPyProcess, execute_anybodycon
from anypytools.macroutils import AnyMacro
from anypytools import macro_commands
from anypytools.tools import (
    ABOVE_NORMAL_PRIORITY_CLASS,
    BELOW_NORMAL_PRIORITY_CLASS,
    IDLE_PRIORITY_CLASS,
    NORMAL_PRIORITY_CLASS,
)


logger = logging.getLogger("abt.anypytools")
logger.addHandler(logging.NullHandler())


__all__ = [
    "datautils",
    "h5py_wrapper",
    "AnyPyProcess",
    "AnyMacro",
    "macro_commands",
    "print_versions",
    "execute_anybodycon",
    "ABOVE_NORMAL_PRIORITY_CLASS",
    "BELOW_NORMAL_PRIORITY_CLASS",
    "IDLE_PRIORITY_CLASS",
    "NORMAL_PRIORITY_CLASS",
]

__version__ = "1.7.5"


def print_versions():
    """Print all the versions of software that AnyPyTools relies on."""
    import numpy as np
    import scipy as sp

    print("-=" * 38)
    print("AnyPyTools version: %s" % __version__)
    print("NumPy version: %s" % np.__version__)
    print("SciPy version: %s" % sp.__version__)
    print("Python version: %s" % sys.version)
    (sysname, _, release, version, machine, processor) = platform.uname()
    print("Platform: %s-%s-%s (%s)" % (sysname, release, machine, version))
    if not processor:
        processor = "not recognized"
    print("Processor: %s" % processor)
    print("Byte-ordering: %s" % sys.byteorder)
    print("-=" * 38)
