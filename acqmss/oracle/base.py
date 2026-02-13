"""
Unified oracle ABC for constraint acquisition.

Defines the base interface for all oracle implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Set


class Oracle(ABC):
    """Unified oracle interface for membership queries.

    Validates configurations against ground truth (FM, DB, API, etc).
    All oracle implementations must inherit from this class.
    """

    @abstractmethod
    def is_valid(self, assignments: Dict[str, bool]) -> bool:
        """Check if configuration is valid.

        Args:
            assignments: Feature assignments {feature_name: True/False}

        Returns:
            True if configuration satisfies the ground truth
        """
        pass

    @abstractmethod
    def get_features(self) -> Set[str]:
        """Get all feature names."""
        pass

    @abstractmethod
    def get_feature_ids(self) -> Dict[str, int]:
        """Get mapping from feature names to SAT variable IDs."""
        pass

    def ask(self, query: Dict[str, bool]) -> bool:
        """Alias for is_valid() (interactive compatibility)."""
        return self.is_valid(query)

    def get_feature_count(self) -> int:
        """Get number of features."""
        return len(self.get_features())
