"""
Task data structures for CONGEN algorithm.

Inherits from TestCaseTask hierarchy in explanation module.
Supports both incremental and non-incremental modes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any

from explanation.models.task_preparation import (
    TestCaseTask,
    IncrementalTestCaseTask,
    NonIncrementalTestCaseTask
)


def _to_hashable(item: Any) -> Any:
    """Convert item to hashable form."""
    if isinstance(item, list):
        return tuple(_to_hashable(x) for x in item)
    return item


@dataclass
class CONGENTask(TestCaseTask):
    """Base task for CONGEN algorithm.

    Inherits from TestCaseTask with mapping:
    - set_c: Bias constraints (B) - constraints to learn from
    - set_b: Background knowledge (BG) - always true constraints
    - set_tc: Positive examples (E+) - valid configurations
    - set_tv: Negative examples (E-) - invalid configurations
    - set_neg_tv: Negated negative examples (NE) - created by GenerateNE in CONGEN
    - neg_c_map: Negation map for REDUCE algorithm

    Additional CONGEN-specific fields:
    - e_neg_literals: Raw E⁻ literals for GenerateNE (List of [l1, l2, ...])
    - assumption_to_constraint: Maps assumption ID to constraint name
    - constraint_to_assumption: Maps constraint name to assumption ID
    - next_assumption_id: Next available assumption ID for GenerateNE
    """
    # E⁻ literals for GenerateNE (each negative example as list of literals)
    e_neg_literals: List[List[int]] = field(default_factory=list)
    # Constraint ID mappings for result formatting (incremental mode)
    assumption_to_constraint: Dict[int, str] = field(default_factory=dict)
    constraint_to_assumption: Dict[str, int] = field(default_factory=dict)
    # Next available assumption ID (for GenerateNE to use)
    next_assumption_id: int = 1000

    def get_constraint_name(self, element: Any) -> str:
        """Get constraint name from element.

        Works for both incremental (int) and non-incremental (list) modes.

        Args:
            element: Assumption ID (int) or clause list (List[List[int]])

        Returns:
            Constraint name or placeholder if not found
        """
        if isinstance(element, int):
            return self.assumption_to_constraint.get(element, f'unknown_{element}')
        else:
            return f'unknown_{_to_hashable(element)}'


@dataclass
class IncrementalCONGENTask(CONGENTask, IncrementalTestCaseTask):
    """CONGEN task for incremental mode.

    All sets are List[int] (assumption IDs).
    Uses IncrementalPySATChecker with assumption-based solving.
    """
    pass


@dataclass
class NonIncrementalCONGENTask(CONGENTask, NonIncrementalTestCaseTask):
    """CONGEN task for non-incremental mode.

    All sets are List[List[int]] (clauses).
    Uses NonIncrementalPySATChecker with fresh solver per check.

    Additional fields for non-incremental mode:
    - clauses_to_name: Maps clause tuple to constraint name
    - name_to_clauses: Maps constraint name to clauses
    """
    # Clause-based mappings for non-incremental mode
    clauses_to_name: Dict[Tuple, str] = field(default_factory=dict)
    name_to_clauses: Dict[str, List[List[int]]] = field(default_factory=dict)

    def get_constraint_name(self, element: Any) -> str:
        """Get constraint name from clause list.

        Args:
            element: Clause list (List[List[int]])

        Returns:
            Constraint name or placeholder if not found
        """
        if isinstance(element, int):
            return self.assumption_to_constraint.get(element, f'unknown_{element}')
        else:
            key = _to_hashable(element)
            return self.clauses_to_name.get(key, f'unknown_{key}')
