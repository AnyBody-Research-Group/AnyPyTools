# AnyPyTools

[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![test](https://github.com/AnyBody-Research-Group/AnyPyTools/actions/workflows/test.yml/badge.svg)](https://github.com/AnyBody-Research-Group/AnyPyTools/actions/workflows/test.yml)
[![](https://anaconda.org/conda-forge/anypytools/badges/downloads.svg)](https://anaconda.org/conda-forge/anypytools)
[![](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![JOSS paper](http://joss.theoj.org/papers/10.21105/joss.01108/status.svg)](https://doi.org/10.21105/joss.01108)

AnyPyTools is a toolkit for working with the [AnyBody Modeling System (AMS)]
from Python. It enables reproduceable research with the AnyBody Modeling System, and bridges the gap to whole ecosystem of open source scientific Python.

The AnyPyTools Python package enables batch processing, parallization of model
simulations, model sensitivity studies, and parameter studies, using either
Monte-Carlo (random sampling) or Latin hypercube sampling. It makes reproducible
research much easier and replaces the tedious process of manually automating the
musculoskeletal simulations and aggregating the results.

If you use the library for publications please **cite as:**

> Lund et al., (2019). AnyPyTools: A Python package for reproducible research with the AnyBody Modeling System. Journal of Open Source Software, 4(33), 1108, <https://doi.org/10.21105/joss.01108>

## Installation

- Download and install the [Anaconda Python distribution]
- After installation opens the Anaconda command prompt and type:

```bash
conda config --add channels conda-forge
conda install anypytools
```

The library is also available on [PyPi](https://pypi.python.org/pypi/AnyPyTools) for installing using `pip`.


## Usage

The simplest case:

```python
from anypytools import AnyPyProcess
app = AnyPyProcess()
macro = [
    'load "Model.main.any"',
    'operation Main.Study.InverseDynamics',
    'run',
]
app.start_macro(macro)
```

Please see the [Jupyter Notebook based tutorial], or check the the following for more information:

- [AnyPyTools's Documentation](https://anybody-research-group.github.io/anypytools-docs)


<img src="docs/_static/relax.png" alt="Don't panic" height="100px">


[anaconda python distribution]: https://store.continuum.io/cshop/anaconda/
[anybody modeling system (ams)]: http://www.anybodytech.com
[jupyter notebook based tutorial]: http://nbviewer.jupyter.org/github/AnyBody-Research-Group/AnyPyTools/blob/master/docs/Tutorial/00_AnyPyTools_tutorial.ipynb
