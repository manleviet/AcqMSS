"""
Compatibility module: re-exports ConGen from acqmss.congen.

This allows both:
- from conacq.algorithms import ConGen
- from conacq.algorithms.congen import ConGen
"""

from .acqmss.congen import ConGen, ConGenResult, resolve_congen_names

__all__ = ['ConGen', 'ConGenResult', 'resolve_congen_names']
