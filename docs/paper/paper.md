---
title: 'AnyPyTools: A Python package for reproducible research with the AnyBody Modeling System'
tags:
  - Python
  - Musculoskeletal Modeling
  - Batch processing
  - Parameter studies
  - Reproducible workflows
  - AnyBody Modeling System
authors:
  - name: Morten Enemark Lund
    orcid: 0000-0001-9920-4051
    affiliation: "1, 2"
  - name: John Rasmussen
    orcid: 0000-0003-3257-5653
    affiliation: 2
  - name: Michael Skipper Andersen
    orcid: 0000-0001-8275-9472
    affiliation: 2
affiliations:
 - name: AnyBody Technology A/S, Denmark
   index: 1
 - name: Department of Materials and Production, Aalborg University, Denmark
   index: 2
date: 09 October 2018
bibliography: paper.bib
---

# Summary

The AnyPyTools package provides a Python interface to automate multibody
musculoskeletal model simulations in the AnyBody Modeling System. The main
advantage of AnyPyTools is that it enables reproducible research for the
AnyBody Modeling System, and bridges the gap to the whole ecosystem of open
source scientific Python packages.

As musculoskeletal simulations become increasingly important in decision making
processes in a range of applications, so does the requirement for model
verification and validation (V&V) [@Lund2012-ty]. Successful V&V will often
require running large numbers of simulations (batch processing) or investigating
parameters systematically (sensitivity or parameter studies). The stand-alone
AnyBody Modeling System is not very suited for this kind of meta-analysis. The
modeling system is essentially an IDE/compiler for scripting single multibody
musculoskeletal models in the AnyScript modeling language. 

The AnyPyTools Python package enables batch processing, parallelization of model
simulations, model sensitivity studies, and parameter studies, using either
Monte-Carlo (random sampling) or Latin hypercube sampling. It makes reproducible
research much easier and replaces the tedious process of manually automating the
musculoskeletal simulations and aggregating the results.

The AnyPyTools library was developed at Aalborg University to
help in the effort to validate musculoskeletal models created within the AnyBody
Modeling System [@Lund2015-ix, @Lund2012-ty]. In this work AnyPyTools was
used to orchestrate large number of model simulations and distribute the load over
multiple processors, as well as collect the results directly in Python and
investigate the sensitivity of the model predictions. The library has
evolved over time to also include a pytest plugin for running unit tests on
AnyScript files (`test_*.any`) similar to how unit-tests are used for Python.

The AnyPyTools library is available on both PyPI and conda. It has been
downloaded more than 20.000 times from the conda-forge channel and has been used in a large
number of scientific publications over the last 5 years [@De_Pieri2018-py, @Stensgaard_Stoltze2018-hi,
@Richards2018-oj, @Theodorakos2018-jv, Rasmussen2018-nq, @DellIsola2017-ac, @Eltoukhy2017-ut,
@Skals2017-if, @Oliveira2017-by, @Skipper_Andersen2017-cw, @Skals2017-sg,
@Vanheule2017-sh, @Theodorakos2016-jx, @Lund2015-ix, @Oliveira2014-vd,
@Oliveira2013-xi, @Oliveira2013-ec]


The source code for AnyPyTools is available on [GitHub](https://github.com/AnyBody-Research-Group/AnyPyTools) and releases are archived
to Zenodo with the linked DOI: [@Lund2018-jm]


# Acknowledgements

We acknowledge contributions from AnyBody Technology A/S who have used the package extensively
for their verification and validation work. Also, thanks to to the numerous academic users of the
AnyBody Modeling System from all over the world, who have contributed feedback and feature requests.  

# References
