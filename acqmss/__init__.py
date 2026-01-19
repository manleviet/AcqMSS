"""
AcqMSS - Constraint Acquisition with Maximum Satisfiable Subsets.

This package provides tools for constraint acquisition from feature models:
- testcases: Test case generation and oracle for feature models
- (future) congen: CONGEN algorithm implementation
"""

from . import testcases

__all__ = ['testcases']
