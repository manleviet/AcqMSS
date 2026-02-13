"""
Oracle package for constraint acquisition.

Provides ground truth interfaces for classifying configurations:
- Oracle: Abstract base class for configuration validation
- FeatureModelOracle: Validates against a feature model (SAT-based)
- InteractiveOracle: Abstract interface for membership queries
- AutomatedOracle: Automated oracle using FeatureModelOracle
- UserPromptOracle: Human-in-the-loop oracle
- CachedOracle: Wrapper caching oracle answers
- ExampleProvider: Provides examples for example-based learning
"""

from .oracle import Oracle, FeatureModelOracle
from .interactive import (
    InteractiveOracle,
    AutomatedOracle,
    UserPromptOracle,
    CachedOracle,
    ExampleProvider,
)

__all__ = [
    'Oracle',
    'FeatureModelOracle',
    'InteractiveOracle',
    'AutomatedOracle',
    'UserPromptOracle',
    'CachedOracle',
    'ExampleProvider',
]
