import logging
logger = logging.getLogger('abt.anypytools')
logger.addHandler(logging.NullHandler())


from .abcutils import AnyPyProcess
from .generate_macros import (MacroGenerator, MonteCarloMacroGenerator,
                              LatinHyperCubeMacroGenerator)



__all__ = ['abcutils', 'datautils', 'generate_macros', 'h5py_wrapper', 'AnyPyProcess', 
           'MacroGenerator', 'MonteCarloMacroGenerator', 'LatinHyperCubeMacroGenerator'
           'print_versions', 'test']

__version__ = '0.7.2'


def print_versions():
    """Print all the versions of software that Blaze relies on."""
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


def test(verbose=False, exit=False):
    """
    Runs py.test unit tests
    
    Parameters
    ----------
    verbose : int, optional
        py.test verbose level. 0 is only print a very little, 1 is more
        and 2 is all information from py.test
    exit : bool, optional
        If True, the function will call sys.exit with an
        error code after the tests are finished.
    """
    import os
    import sys
    import pytest

    args = []

    if verbose:
        args.append('--verbose')


    # Add all 'tests' subdirectories to the options
    rootdir = os.path.dirname(__file__)
    for root, dirs, files in os.walk(rootdir):
        if 'tests' in dirs:
            testsdir = os.path.join(root, 'tests')
            args.append(testsdir)
            print('Test dir: %s' % testsdir[len(rootdir) + 1:])

    print_versions()
    sys.stdout.flush()

    error_code = pytest.main(args=args)
    if exit:
        return sys.exit(error_code)
    return error_code == 0