"""
Compatibility module: re-exports Reduce from acqmss.reduce.

This allows both:
- from conacq.algorithms import Reduce
- from conacq.algorithms.reduce import Reduce
"""

from .acqmss.reduce import Reduce

__all__ = ['Reduce']
