# -*- coding: utf-8 -*-
"""
Created on Sat Sep 24 12:29:53 2011

@author: melund
"""

#from distutils.core import setup
from setuptools import setup

setup(
    name='AnyPyTools',
    version='0.6.1',
    install_requires=[],
    py_modules=['anypytools.abcutils', 'anypytools.h5py_wrapper',
                'anypytools.datautils', 'anypytools.genereate_macros', 
                'anypytools.utils.py3k', 'anypytools.utils.pytest_plugin',
                'anypytools.utils.support_functions',
                'anypytools.utils.blaze_converter'],
    scripts=['src/scripts/pp2any.py'],
    packages=['anypytools'],
    package_dir={'': 'src'},
    package_data={'anypytools': ['test_models/Demo.Arm2D.any']},
    # the following makes a plugin available to pytest
    entry_points = {
        'pytest11': [
            'anypytools = anypytools.utils.pytest_plugin',
        ]
    },
    author='Morten Lund',
    author_email='melund@gmail.com',
    description='A library of python utilities for the AnyBody Modeling System',
    license='MIT',
    keywords=('AnyBody Modeling System ', 'AnyScript'),
    url='https://github.com/AnyBody-Research-Group/AnyPyTools',
    classifiers=[
        'Development Status :: 1 - Alpha',
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3.4",
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Windows',
        'Topic :: Scientific/Engineering'
        ]
    )