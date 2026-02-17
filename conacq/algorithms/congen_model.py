"""
Compatibility module: re-exports ConGenModel from acqmss.congen_model.

This allows both:
- from conacq.algorithms import ConGenModel
- from conacq.algorithms.congen_model import ConGenModel
"""

from .acqmss.congen_model import ConGenModel

__all__ = ['ConGenModel']
