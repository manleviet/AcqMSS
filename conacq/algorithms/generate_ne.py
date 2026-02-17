"""
Compatibility module: re-exports GenerateNE from acqmss.generate_ne.

This allows both:
- from conacq.algorithms import GenerateNE
- from conacq.algorithms.generate_ne import GenerateNE
"""

from .acqmss.generate_ne import GenerateNE, NEPerTestcase

__all__ = ['GenerateNE', 'NEPerTestcase']
