# -*- coding: utf-8 -*-
"""
Created on Sat Sep 24 12:29:53 2011

@author: melund
"""

from distutils.core import setup

setup(
    name='AnyPyTools',
    version='0.1',
    install_requires=['numpy'],
    py_modules=['anypytools.abcutils'],
    scripts=['scripts/pp2any.py'],
    packages=['anypytools'],
#    package_dir={'mypkg': 'src/mypkg'},
    package_data={'anypytools': ['test_models/Demo.Arm2D.any']},
    author='Morten Lund',
    author_email='melund@gmail.com',
    description='A library of python utilities for AnyBody Modelling System ',
#    long_description=open('README.rst').read(),
    license='MIT',
    keywords=('AnyBody Modelling system '
              'AnyScript'),
    url='http://github.com/lmjohns3/py-c3d',
    classifiers=[
        'Development Status :: 1 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Windows',
        'Topic :: Scientific/Engineering',
        ],
    )
