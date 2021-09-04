# -*- coding: utf-8 -*-
"""
Created on Sat Sep 24 12:29:53 2011.

@author: melund
"""

import os
import io
import re
import sys

from setuptools import setup, find_packages

long_description = (
    "AnyPyTools is a toolkit for working with the AnyBody Modeling System "
    "from Python. Its main purpose is to launch AnyBody simulations and collect "
    "results. It has a scheduler to launch multiple instances of AMS utilising "
    "computers with multiple cores. AnyPyTools makes it possible to run parameter "
    "and Monte Carlo studies more efficiently than from within the AnyBody Modeling "
    "System.\n\n"
    "Please visit https://anybody-research-group.github.io/anypytools-docs for more information."
)


def read(*names, **kwargs):
    """Read content of file."""
    with io.open(
        os.path.join(os.path.dirname(__file__), *names),
        encoding=kwargs.get("encoding", "utf8"),
    ) as fp:
        return fp.read()


def find_version(*file_paths):
    """Parse the __version__ string from a file."""
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


require_list = ["numpy", "scipy", "tqdm"]



setup(
    name="AnyPyTools",
    version=find_version("anypytools", "__init__.py"),
    install_requires=require_list,
    python_requires=">=3.8",
    packages=find_packages(exclude=["docs", "tests*"]),
    package_data={"anypytools": ["test_models/Demo.Arm2D.any"]},
    # the following makes a plugin available to pytest
    entry_points={"pytest11": ["anypytools = anypytools.pytest_plugin"]},
    author="Morten Lund",
    author_email="melund@gmail.com",
    description="Python tools and utilities for working with the AnyBody Modeling System",
    long_description=long_description,
    license="MIT",
    keywords=("AnyBody Modeling System", "AnyScript"),
    url="https://github.com/AnyBody-Research-Group/AnyPyTools",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Framework :: Pytest",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
    ],
)
