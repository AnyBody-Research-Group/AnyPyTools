---
title: 'AnyPyTools: A Python package for reproducable research with the AnyBody Modeling System.
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


The ``anypytools`` package provides as Python interface to automate
musculoskeletal model simulations in the AnyBody Modeling System to run parallel
batch processing, model sensitivity studies, and parameter studies using either
monte-carlo (random sampling) or Latin hybercube sampling. This replaces the
tedious automating musculoskeltal simulations in the AnyBody Modeling System. 

The ``anypytools`` library was developed at Aalborg University to
help in the effort to validate musculoskeletal models created within the AnyBody
Modeling System [@Lund2015-ix, @Lund2012-ty]. In this work ``anypytools`` was
used to orchestrate large number of model simulations and distribute the load over
multiple processors, as well as collect the results directly in Python and
investigate the sensitivity of the model predictions [@zenodo]. The library have
evolved over time to also 

The main advantage of ``anypytools`` is that it enables reproducible research
for the AnyBody Modeling System, and bridges the gap between the AnyBody Modeling
System and the wealth of open source Python tools which has emerged.

The ``AnyPyTools`` has been used in a large number for scientific publications 

The source code for ``AnyPyTools`` has been
archived to Zenodo with the linked DOI: [@zenodo]



``Gala`` is an Astropy-affiliated Python package for galactic dynamics. Python
enables wrapping low-level languages (e.g., C) for speed without losing
flexibility or ease-of-use in the user-interface. The API for ``Gala`` was
designed to provide a class-based and user-friendly interface to fast (C or
Cython-optimized) implementations of common operations such as gravitational
potential and force evaluation, orbit integration, dynamical transformations,
and chaos indicators for nonlinear dynamics. ``Gala`` also relies heavily on and
interfaces well with the implementations of physical units and astronomical
coordinate systems in the ``Astropy`` package [@astropy] (``astropy.units`` and
``astropy.coordinates``).

``Gala`` was designed to be used by both astronomical researchers and by
students in courses on gravitational dynamics or astronomy. It has already been
used in a number of scientific publications [@Pearson:2017] and has also been
used in graduate courses on Galactic dynamics to, e.g., provide interactive
visualizations of textbook material [@Binney:2008]. The combination of speed,
design, and support for Astropy functionality in ``Gala`` will enable exciting
scientific explorations of forthcoming data releases from the *Gaia* mission
[@gaia] by students and experts alike. The source code for ``Gala`` has been
archived to Zenodo with the linked DOI: [@zenodo]

# Mathematics

Single dollars ($) are required for inline mathematics e.g. $f(x) = e^{\pi/x}$

Double dollars make self-standing equations:

$$\Theta(x) = \left\{\begin{array}{l}
0\textrm{ if } x < 0\cr
1\textrm{ else}
\end{array}\right.$$


# Citations

Citations to entries in paper.bib should be in
[rMarkdown](http://rmarkdown.rstudio.com/authoring_bibliographies_and_citations.html)
format.

# Figures

Figures can be included like this: ![Example figure.](figure.png)

# Acknowledgements

We acknowledge contributions from Brigitta Sipocz, Syrtis Major, and Semyeong
Oh, and support from Kathryn Johnston during the genesis of this project.

# References
