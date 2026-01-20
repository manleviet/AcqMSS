"""
REDUCE Algorithm for redundancy elimination.

Removes redundant constraints from the acquired knowledge base.
Pattern follows WipeOutR_FM.find_redundancies() from the explanation package.
"""

import logging
from typing import List, Dict, Tuple, Any

from explanation.operations.algorithms.checker import ConsistencyChecker
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)
from explanation.operations.algorithms.utils import diff


def _to_hashable(item: Any) -> Any:
    """Convert item to hashable form for set operations."""
    if isinstance(item, list):
        return tuple(_to_hashable(x) for x in item)
    return item


def _unique_union(list1: List, list2: List) -> List:
    """Create union of two lists preserving order and uniqueness.

    Works with both hashable (int) and unhashable (list) elements.
    """
    # Check if elements are hashable
    if list1 and isinstance(list1[0], int):
        # Hashable elements - use set for efficiency
        return list(set(list1) | set(list2))

    # Unhashable elements - use conversion to tuple
    seen = set()
    result = []
    for item in list1 + list2:
        key = _to_hashable(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


class Reduce:
    """
    REDUCE algorithm for removing redundant constraints.

    Pattern follows WipeOutR_FM.find_redundancies().

    A constraint c is redundant if BG ∪ (KB - {c}) |= c
    Equivalently: BG ∪ (KB - {c}) ∪ {¬c} is inconsistent

    Algorithm REDUCE(B', NE, BG)
    1: KB ← B' ∪ NE
    2: for all c ∈ KB do
    3:     if inconsistent(BG ∪ (KB - {c}) ∪ {¬c}) then
    4:         KB ← KB - {c}
    5:     end if
    6: end for
    7: return KB

    Args:
        checker: ConsistencyChecker instance for SAT solving
        profiler_instance: Optional profiler for metrics tracking
    """

    def __init__(self, checker: ConsistencyChecker,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.checker = checker
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()

    @measure_time('reduce_runtime')
    @count_calls('reduce_calls')
    def reduce(self, set_b_prime: List, set_ne: List, set_bg: List,
               neg_map: Dict) -> Tuple[List, List]:
        """
        Remove redundant constraints from KB.

        Works with both incremental (int assumption IDs) and
        non-incremental (List[List[int]] clause lists) modes.

        Args:
            set_b_prime: MSS constraints from ACQMSS
            set_ne: Negated negative examples
            set_bg: Background knowledge
            neg_map: Mapping from constraint to its negated form
                     - Incremental: Dict[int, int]
                     - Non-incremental: Dict[Tuple, List[List[int]]]

        Returns:
            Tuple of (redundant constraints, non-redundant KB)
        """
        logging.debug('REDUCE [B\'=%s, NE=%s, BG=%s]', set_b_prime, set_ne, set_bg)

        # KB ← B' ∪ NE (handles both hashable and unhashable elements)
        kb = _unique_union(set_b_prime, set_ne)
        kb_delta = kb.copy()
        redundant = []

        for c in kb:
            # Skip if c already removed from KB
            if c not in kb_delta:
                continue

            # Build KB - {c}
            kb_without_c = diff(kb_delta, [c])

            # Get ¬c
            # For non-incremental: convert to hashable key
            c_key = _to_hashable(c) if isinstance(c, list) else c
            if c_key not in neg_map:
                logging.warning('No negated form for constraint %s, skipping', c)
                continue
            neg_c = neg_map[c_key]

            # Check inconsistent(BG ∪ (KB - {c}) ∪ {¬c})
            test_set = set_bg + kb_without_c + [neg_c]
            is_consistent = self.checker.is_consistent(test_set)

            logging.debug('Checking c=%s: consistent(BG ∪ KB-{c} ∪ {¬c}) = %s',
                          c, is_consistent)

            if not is_consistent:
                # c is redundant: BG ∪ (KB - {c}) |= c
                kb_delta.remove(c)
                redundant.append(c)
                logging.debug('Constraint %s is redundant', c)

        logging.debug('Redundant: %s', redundant)
        logging.debug('Non-redundant KB: %s', kb_delta)

        return redundant, kb_delta

    @measure_time('reduce_nonredundant_runtime')
    def find_non_redundant(self, set_b_prime: List, set_ne: List,
                           set_bg: List, neg_map: Dict) -> List:
        """
        Find non-redundant constraints in KB.

        This is a convenience method that returns only the non-redundant KB.

        Args:
            set_b_prime: MSS constraints from ACQMSS
            set_ne: Negated negative examples
            set_bg: Background knowledge
            neg_map: Mapping from constraint to its negated form

        Returns:
            List of non-redundant constraints
        """
        _, non_redundant = self.reduce(set_b_prime, set_ne, set_bg, neg_map)
        return non_redundant
