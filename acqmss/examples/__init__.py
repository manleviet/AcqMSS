"""
Test case generation package for constraint acquisition.

Provides:
- Generators: Various sampling methods (RS, FF, 2-COV)
- Data structures: Example, ExampleSet
"""

from .data_structures import Example, ExampleSet, ExampleType
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
