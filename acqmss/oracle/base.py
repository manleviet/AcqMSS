"""
Unified oracle ABC for constraint acquisition.

Defines the base interface for all oracle implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set


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

    @abstractmethod
    def complete_configuration(self, partial: Dict[str, bool]) -> Optional[Dict[str, bool]]:
        """Complete a partial configuration to a full valid one.

        Args:
            partial: Partial assignment {feature_name: True/False} for subset of features

        Returns:
            Full valid configuration dict, or None if no valid completion exists
        """
        pass

    @abstractmethod
    def get_cnf_clauses(self) -> List[List[int]]:
        """Get the raw ground truth CNF clauses.

        Returns:
            List of clauses, each clause a list of integer literals
        """
        pass

    def ask(self, query: Dict[str, bool]) -> bool:
        """Alias for is_valid() (interactive compatibility)."""
        return self.is_valid(query)

    def get_feature_count(self) -> int:
        """Get number of features."""
        return len(self.get_features())
