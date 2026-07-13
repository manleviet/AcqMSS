"""
Oracle package for constraint acquisition.

Provides ground truth interfaces for classifying configurations:
- Oracle: Minimal ABC — only is_valid() / ask()
- FMOracle: Validates against a feature model (SAT-based)
- UserPromptOracle: Human-in-the-loop oracle
- CachedOracle: Wrapper caching oracle answers
- FMData: Immutable FM metadata snapshot
- GroundTruthData: Extracted ground truth for evaluation
"""

from .base import Oracle
from .bg_data import BGData
from .fm_data import FMData
from .protocols import (
    MembershipOracle,
    CompletableOracle,
    CatalogProvider,
    BGProvider,
    KBProvider,
    GeneratorOracle,
    PreparationOracle,
)
from .fm_oracle import FMOracle
from .user_prompt import UserPromptOracle
from .cached import CachedOracle
from .ground_truth import GroundTruthData
from .fm_oracle_model import FMOracleModel
from .constraint_description import extract_constraint_descriptions

__all__ = [
    'Oracle',
    'BGData',
    'FMData',
    # Narrow role protocols (contracts consumers depend on)
    'MembershipOracle',
    'CompletableOracle',
    'CatalogProvider',
    'BGProvider',
    'KBProvider',
    'GeneratorOracle',
    'PreparationOracle',
    'FMOracle',
    'UserPromptOracle',
    'CachedOracle',
    'GroundTruthData',
    'FMOracleModel',
    'extract_constraint_descriptions',
]
