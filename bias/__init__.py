"""
Bias module for constraint acquisition.

This module provides tools for generating constraint biases from feature models,
including data structures, clause generators, and I/O utilities.
"""

from .data_structures import (
    Feature,
    Constraint,
    Bias,
    OperatorType,
    RelationshipType,
    SimplifiedHierarchicalCandidate,
    SimplifiedCrossTreeConfig,
    SimplifiedBiasConfig,
)
from .clause_generator import ConstraintClauseGenerator
from .config_loader import SimplifiedConfigLoader
from .bias_generator import SimplifiedBiasGenerator
from .bias_io import BiasIO

__all__ = [
    # Data structures
    'Feature',
    'Constraint',
    'Bias',
    'OperatorType',
    'RelationshipType',
    'SimplifiedHierarchicalCandidate',
    'SimplifiedCrossTreeConfig',
    'SimplifiedBiasConfig',
    # Generators and utilities
    'ConstraintClauseGenerator',
    'SimplifiedConfigLoader',
    'SimplifiedBiasGenerator',
    'BiasIO',
]
