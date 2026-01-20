"""
GenerateNE Algorithm for generating negated negative examples.

Uses QuickXPlain to find minimal conflict sets from negative examples,
then negates them to create NE constraints.

Reference: Paper Section "CONGEN (Algorithm 1)"
- GENERATENE(E⁻) activates QUICKXPLAIN once per negative example e⁻ ∈ E⁻.
- NE is a set of constraints such that: if e⁻ᵢ ∈ E⁻ then ¬e⁻ᵢ ∈ NE

Supports both incremental and non-incremental modes.
"""

import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional

from explanation.operations.algorithms.checker import (
    ConsistencyChecker,
    IncrementalPySATChecker,
    NonIncrementalPySATChecker
)
from explanation.operations.algorithms.quickxplain import QuickXPlain
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


@dataclass
class NEResult:
    """Result of NE generation."""
    # For incremental mode: assumption IDs
    assumption_ids: List[int]
    # For non-incremental mode: clause lists
    clause_lists: List[List[List[int]]]
    # Mapping from assumption ID to negated form (for REDUCE)
    neg_map: dict
    # Original literals for each NE (for reference)
    original_literals: List[List[int]]


class GenerateNE:
    """
    Generate negated negative examples using QuickXPlain.

    For each negative example e⁻, uses QuickXPlain to find the minimal
    conflict set, then creates a constraint that blocks that configuration.

    NE = {¬(minimal_conflict(e⁻)) | e⁻ ∈ E⁻}

    Supports both incremental and non-incremental modes:
    - Incremental: adds clauses to solver, returns assumption IDs
    - Non-incremental: returns clause lists without modifying solver

    Args:
        checker: ConsistencyChecker instance for SAT solving
        profiler_instance: Optional profiler for metrics tracking
    """

    def __init__(self, checker: ConsistencyChecker,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.checker = checker
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        self.quickxplain = QuickXPlain(checker, self.profiler)
        self._is_incremental = isinstance(checker, IncrementalPySATChecker)

    @measure_time('generate_ne_runtime')
    @count_calls('generate_ne_calls')
    def generate(self, set_e_neg: List[List[int]], set_bg: List[int],
                 start_assumption_id: int = 1000) -> NEResult:
        """
        Generate NE from negative examples using QuickXPlain.

        For each e⁻ (list of literals), uses QuickXPlain to find the minimal
        conflict set with respect to BG, then creates a blocking clause.

        Args:
            set_e_neg: List of negative examples, each is a list of literals
            set_bg: Background knowledge (assumption IDs for incremental,
                    or empty list for non-incremental)
            start_assumption_id: Starting ID for assumptions (incremental mode)

        Returns:
            NEResult with assumption IDs (incremental) or clause lists (non-incremental)
        """
        logging.debug('>>> GenerateNE [%d E⁻, BG=%s, mode=%s]',
                      len(set_e_neg), set_bg,
                      'incremental' if self._is_incremental else 'non-incremental')

        assumption_ids = []
        clause_lists = []
        neg_map = {}
        original_literals = []
        current_id = start_assumption_id

        for e_neg in set_e_neg:
            if not e_neg:
                continue

            # Use QuickXPlain to find minimal conflict
            # set_c = literals of e⁻ (each literal as a separate element)
            # set_b = BG (background knowledge)
            if self._is_incremental:
                # Incremental: pass literals directly (used as assumption IDs)
                qx_set_c = e_neg
                qx_set_b = set_bg
            else:
                # Non-incremental: wrap each literal as unit clause CNF
                # [l1, l2, ...] -> [[[l1]], [[l2]], ...]
                qx_set_c = [[[lit]] for lit in e_neg]
                qx_set_b = set_bg  # Already clause lists or empty

            minimal_conflict_raw = self.quickxplain.find_conflict(qx_set_c, qx_set_b)

            # Convert back to literals for blocking clause
            if self._is_incremental:
                minimal_conflict = minimal_conflict_raw
            else:
                # Extract literals from unit clause CNFs: [[[l1]], [[l2]]] -> [l1, l2]
                minimal_conflict = [c[0][0] for c in minimal_conflict_raw] if minimal_conflict_raw else []

            if len(minimal_conflict) == 0:
                # No conflict with BG alone - use the whole negative example
                # This means e⁻ conflicts with target theory, not just BG
                minimal_conflict = e_neg
                logging.debug('E⁻=%s consistent with BG, using full example', e_neg)
            else:
                logging.debug('E⁻=%s -> minimal conflict=%s', e_neg, minimal_conflict)

            original_literals.append(minimal_conflict)

            # Create blocking clause: ¬(l1 ∧ l2 ∧ ...) = (¬l1 ∨ ¬l2 ∨ ...)
            blocking_clause = [-lit for lit in minimal_conflict]

            if self._is_incremental:
                # Incremental mode: add clause to solver with assumption
                assumption_id = current_id
                current_id += 1

                # Add clause: (¬assumption ∨ blocking_clause)
                full_clause = [-assumption_id] + blocking_clause
                self.checker.solver.add_clause(full_clause)

                # Create negated form for REDUCE: ¬(¬l1 ∨ ¬l2 ∨ ...) = (l1 ∧ l2 ∧ ...)
                neg_assumption_id = current_id
                current_id += 1
                for lit in minimal_conflict:
                    self.checker.solver.add_clause([-neg_assumption_id, lit])

                assumption_ids.append(assumption_id)
                neg_map[assumption_id] = neg_assumption_id

                logging.debug('NE assumption=%d, neg=%d, clause=%s',
                              assumption_id, neg_assumption_id, blocking_clause)
            else:
                # Non-incremental mode: store clause list
                ne_clauses = [blocking_clause]
                clause_lists.append(ne_clauses)

                # Create negated form for REDUCE
                ne_key = tuple(tuple(c) for c in ne_clauses)
                ne_negated = [[lit] for lit in minimal_conflict]
                neg_map[ne_key] = ne_negated

                logging.debug('NE clauses=%s', ne_clauses)

        logging.debug('<<< GenerateNE: %d NE constraints', len(assumption_ids) or len(clause_lists))

        return NEResult(
            assumption_ids=assumption_ids,
            clause_lists=clause_lists,
            neg_map=neg_map,
            original_literals=original_literals
        )

    def generate_from_examples(self, e_neg_literals: List[List[int]],
                               set_bg: List[int] = None) -> List[int]:
        """
        Generate NE assumption IDs from negative example literals.

        Convenience method for incremental mode that calls generate().

        Args:
            e_neg_literals: List of negative examples, each is a list of literals
            set_bg: Background knowledge (default: empty)

        Returns:
            List of NE assumption IDs (incremental mode only)
        """
        if set_bg is None:
            set_bg = []
        result = self.generate(e_neg_literals, set_bg)
        return result.assumption_ids
