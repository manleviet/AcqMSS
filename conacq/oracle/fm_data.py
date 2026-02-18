"""
Feature model metadata dataclass.

Immutable container for FM metadata extracted from FeatureModelOracle.
Created once, passed around explicitly to decouple callers from Oracle.
"""

from dataclasses import dataclass
from typing import Dict, Set


@dataclass(frozen=True)
class FMData:
    """Immutable FM metadata extracted from FeatureModelOracle.

    Attributes:
        features: Set of all feature names
        feature_ids: Mapping from feature names to SAT variable IDs
        root_feature: Name of the root feature
        num_constraints: Number of FM constraints in ground truth
        next_available_id: Starting Tseitin variable ID from FM model
    """
    features: Set[str]
    feature_ids: Dict[str, int]
    root_feature: str
    num_constraints: int
    next_available_id: int

    @property
    def feature_count(self) -> int:
        """Get number of features."""
        return len(self.features)
