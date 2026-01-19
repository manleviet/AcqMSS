"""
Test case generation package for constraint acquisition.

Provides:
- Oracle: Feature model ground truth for classifying configurations
- Generators: Various sampling methods (RS, FF, 2-COV)
- Data structures: Example, ExampleSet
"""

from .data_structures import Example, ExampleSet, ExampleType
from .oracle import Oracle, FeatureModelOracle
from .generators import (
    ExampleGenerator,
    RandomSamplingGenerator,
    BalancedRandomSamplingGenerator,
    ControlledRandomSamplingGenerator,
    FeatureFrequencyGenerator,
    NWiseCoverageGenerator,
    TwoCoverageGenerator,
)
from .io_utils import ExampleIO

__all__ = [
    # Data structures
    'Example',
    'ExampleSet',
    'ExampleType',
    # Oracle
    'Oracle',
    'FeatureModelOracle',
    # Generators
    'ExampleGenerator',
    'RandomSamplingGenerator',
    'BalancedRandomSamplingGenerator',
    'ControlledRandomSamplingGenerator',
    'FeatureFrequencyGenerator',
    'NWiseCoverageGenerator',
    'TwoCoverageGenerator',
    # I/O
    'ExampleIO',
]
