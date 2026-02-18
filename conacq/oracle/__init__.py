"""
Oracle package for constraint acquisition.

Provides ground truth interfaces for classifying configurations:
- Oracle: Minimal ABC — only is_valid() / ask()
- FeatureModelOracle: Validates against a feature model (SAT-based)
- UserPromptOracle: Human-in-the-loop oracle
- CachedOracle: Wrapper caching oracle answers
- FMData: Immutable FM metadata snapshot
- GroundTruthData: Extracted ground truth for evaluation
"""

from .base import Oracle
from .bg_data import BGData
from .fm_data import FMData
from .fm_oracle import FeatureModelOracle
from .user_prompt import UserPromptOracle
from .cached import CachedOracle
from .ground_truth import GroundTruthData, OracleData
from .fm_oracle_model import FMOracleModel, OneShotModel
from .constraint_description import extract_constraint_descriptions

__all__ = [
    'Oracle',
    'BGData',
    'FMData',
    'FeatureModelOracle',
    'UserPromptOracle',
    'CachedOracle',
    'GroundTruthData',
    'OracleData',  # backward compat alias
    'FMOracleModel',
    'OneShotModel',
    'extract_constraint_descriptions',
]
