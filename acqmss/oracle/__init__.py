"""
Oracle package for constraint acquisition.

Provides ground truth interfaces for classifying configurations:
- Oracle: Unified abstract base class for all oracles
- FeatureModelOracle: Validates against a feature model (SAT-based)
- UserPromptOracle: Human-in-the-loop oracle
- CachedOracle: Wrapper caching oracle answers
- OracleData: Extracted oracle data for evaluation
"""

from .base import Oracle
from .fm_oracle import FeatureModelOracle
from .user_prompt import UserPromptOracle
from .cached import CachedOracle
from .extractor import OracleData
from .fm_oracle_model import FMOracleModel, OneShotModel
from .constraint_description import extract_constraint_descriptions

__all__ = [
    'Oracle',
    'FeatureModelOracle',
    'UserPromptOracle',
    'CachedOracle',
    'OracleData',
    'FMOracleModel',
    'OneShotModel',
    'extract_constraint_descriptions',
]
