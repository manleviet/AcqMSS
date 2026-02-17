"""
Compatibility module: re-exports ConGenModelBuilder from acqmss.congen_model_builder.

This allows both:
- from conacq.algorithms import ConGenModelBuilder
- from conacq.algorithms.congen_model_builder import ConGenModelBuilder
"""

from .acqmss.congen_model_builder import ConGenModelBuilder

__all__ = ['ConGenModelBuilder']
