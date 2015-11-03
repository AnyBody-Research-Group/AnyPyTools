import logging
logger = logging.getLogger('abt.anypytools')
logger.addHandler(logging.NullHandler())


from .abcutils import AnyPyProcess
from .generate_macros import (MacroGenerator, MonteCarloMacroGenerator,
                              LatinHyperCubeMacroGenerator)

from .macroutils import AnyMacro
from . import macro_commands

__all__ = ['datautils', 'h5py_wrapper', 'AnyPyProcess',
           'MacroGenerator', 'MonteCarloMacroGenerator', 'LatinHyperCubeMacroGenerator'
           'AnyMacro', 'macro_commands', 'print_versions']

__version__ = '0.8.1'


def print_versions():
    """ Print all the versions of software that AnyPyTools relies on."""
    import sys, platform
    import numpy as np
    print("-=" * 38)
    print("AnyPyTools version: %s" % __version__)
    print("NumPy version: %s" % np.__version__)
    print("Python version: %s" % sys.version)
    (sysname, nodename, release, version, machine, processor) = \
        platform.uname()
    print("Platform: %s-%s-%s (%s)" % (sysname, release, machine, version))
    if sysname == "Linux":
        print("Linux dist: %s" % " ".join(platform.linux_distribution()[:-1]))
    if not processor:
        processor = "not recognized"
    print("Processor: %s" % processor)
    print("Byte-ordering: %s" % sys.byteorder)
    print("-=" * 38)


