"""
AcqMSS - Constraint Acquisition with Maximum Satisfiable Subsets.

This package provides tools for constraint acquisition from feature models:
- testcases: Test case generation and oracle for feature models
- algorithms: CONGEN algorithm implementation
- bias: Bias generation for constraint acquisition
"""

from . import testcases
from . import algorithms

__all__ = ['testcases', 'algorithms']
