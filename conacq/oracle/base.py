"""
Unified oracle ABC for constraint acquisition.

Defines the minimal interface for all oracle implementations:
only membership queries (is_valid / ask).
"""

from abc import ABC, abstractmethod
from typing import Dict


class Oracle(ABC):
    """Minimal oracle interface for membership queries.

    Validates configurations against ground truth (FM, DB, API, etc).
    All oracle implementations must inherit from this class.

    Only requires is_valid() — FM metadata and SAT capabilities
    live on concrete implementations (e.g. FMOracle).
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

    def ask(self, query: Dict[str, bool]) -> bool:
        """Alias for is_valid() (interactive compatibility)."""
        return self.is_valid(query)

    def get_variables(self):
        pass

    def complete_configuration(self, partial: Dict[str, bool]):
        pass
