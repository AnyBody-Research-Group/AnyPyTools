---
title: 'AnyPyTools: A Python package for reproducible research with the AnyBody Modeling System.
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
 - name: Department of Mechanical Engineering, Aalborg University, Denmark
   index: 2
date: 09 October 2018
bibliography: paper.bib
---

# Summary

Introduction

The AnyPyTools package provides a Python interface to automate multibody
musculoskeletal model simulations in the AnyBody Modeling System. The main
advantage of AnyPyTools is that it enables reproducible research for the
AnyBody Modeling System, and bridges the gap to the whole ecosystem of open
source scientific Python packages.

As musculoskeletal simulations becomes increasingly important in decision making
processes in a range of applications, so does the requirement for model
verification and validation (V&V) [@Lund2012-ty]. Successful V&V will often
require running large number of simulations (batch processing) or investigating
parameters systematically (sensitivity or parameter studies). The stand-alone
AnyBody Modeling System is not very suited for these kind of meta analysis. The
modeling system is essentially a IDE/compiler for scripting single multibody
musculoskeletal models in the AnyScript modeling language. 

The AnyPyTools Python package enables batch processing, parallazation of model
simulations, model sensitivity studies, and parameter studies using either
monte-carlo (random sampling) or Latin hypercube sampling. It makes reproducible
research much easier and replaces the tedious process of manually automating the
musculoskeletal simulations and aggregating the results.

The AnyPyTools library was developed at Aalborg University to
help in the effort to validate musculoskeletal models created within the AnyBody
Modeling System [@Lund2015-ix, @Lund2012-ty]. In this work AnyPyTools was
used to orchestrate large number of model simulations and distribute the load over
multiple processors, as well as collect the results directly in Python and
investigate the sensitivity of the model predictions. The library have
evolved over time to also include a pytest plugin for running unit tests on
AnyScript files (`test_*.any`) similar to how unit-tests are used for python.

The AnyPyTools library has been used in a large number for scientific publications
over the last 5 years. 

The source code for AnyPyTools has been archived to Zenodo with the linked DOI: [@Lund2018-jm]


# Acknowledgements

We acknowledge contributions from AnyBody Technology A/S who have used the package extensively
for their verification and validation work. Also, thanks to to the numerous academic users of the
AnyBody Modeling System from all over the world who have contributed feedback and feature requests.  

# References
