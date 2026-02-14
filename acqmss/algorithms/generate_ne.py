"""
GenerateNE Algorithm for generating negated negative examples.

Uses QuickXPlain to find minimal conflict sets from negative examples,
then negates them to create NE constraints. Returns new clauses and
assumptions in NEResult for the caller to merge into the task.

Reference: Paper Section "ConGen (Algorithm 1)"
- GENERATENE(E⁻) activates QUICKXPLAIN once per negative example e⁻ ∈ E⁻.
- NE is a set of constraints such that: if e⁻ᵢ ∈ E⁻ then ¬e⁻ᵢ ∈ NE
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict

from explanation.operations.algorithms.checker import ConsistencyChecker
from explanation.operations.algorithms.quickxplain import QuickXPlain
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


@dataclass
class NEResult:
    """Result of NE generation."""
    assumption_ids: List[int]
    neg_map: Dict[int, int]
    original_literals: List[List[int]]
    new_clauses: List[List[int]] = field(default_factory=list)
    new_assumptions: List[int] = field(default_factory=list)


class GenerateNE:
    """
    Generate negated negative examples using QuickXPlain.

    For each negative example e⁻, uses QuickXPlain to find the minimal
    conflict set, then creates a constraint that blocks that configuration.
    Returns new clauses and assumptions in NEResult for the caller to merge.

    NE = {¬(minimal_conflict(e⁻)) | e⁻ ∈ E⁻}
    """

    def __init__(self, checker: ConsistencyChecker,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.checker = checker
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        self.quickxplain = QuickXPlain(checker, self.profiler)

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
            set_bg: Background knowledge (assumption IDs)
            start_assumption_id: Starting ID for new assumptions

        Returns:
            NEResult with assumption IDs and neg_map
        """
        logging.debug('>>> GenerateNE [%d E⁻, BG=%s]', len(set_e_neg), set_bg)

        assumption_ids = []
        neg_map = {}
        original_literals = []
        new_clauses = []
        new_assumptions = []
        current_id = start_assumption_id

        for e_neg in set_e_neg:
            if not e_neg:
                continue

            # Use QuickXPlain to find minimal conflict
            # Pass literals directly as assumption IDs
            minimal_conflict = self.quickxplain.find_conflict(e_neg, set_bg)

            if len(minimal_conflict) == 0:
                minimal_conflict = e_neg
                logging.debug('E⁻=%s consistent with BG, using full example', e_neg)
            else:
                logging.debug('E⁻=%s -> minimal conflict=%s', e_neg, minimal_conflict)

            original_literals.append(minimal_conflict)

            # Create blocking clause: ¬(l1 ∧ l2 ∧ ...) = (¬l1 ∨ ¬l2 ∨ ...)
            blocking_clause = [-lit for lit in minimal_conflict]

            # Collect clause and assumption (caller will merge into task)
            assumption_id = current_id
            current_id += 1
            new_clauses.append([-assumption_id] + blocking_clause)
            new_assumptions.append(assumption_id)

            # Create negated form for REDUCE: ¬(¬l1 ∨ ¬l2 ∨ ...) = (l1 ∧ l2 ∧ ...)
            neg_assumption_id = current_id
            current_id += 1
            for lit in minimal_conflict:
                new_clauses.append([-neg_assumption_id, lit])
            new_assumptions.append(neg_assumption_id)

            assumption_ids.append(assumption_id)
            neg_map[assumption_id] = neg_assumption_id

            logging.debug('NE assumption=%d, neg=%d, clause=%s',
                          assumption_id, neg_assumption_id, blocking_clause)

        logging.debug('<<< GenerateNE: %d NE constraints', len(assumption_ids))

        return NEResult(
            assumption_ids=assumption_ids,
            neg_map=neg_map,
            original_literals=original_literals,
            new_clauses=new_clauses,
            new_assumptions=new_assumptions
        )

def merge_ne_into_task(task, ne_result: NEResult) -> None:
    """Merge GenerateNE results into a ConGenTask.

    Updates task in-place:
    - set_ne: NE assumption IDs
    - set_kb: appends new clauses
    - assumptions: appends new assumption IDs
    - neg_c_map: merges NE negation map
    - assumption_to_constraint: adds ne_X entries

    Args:
        task: ConGenTask to update
        ne_result: Result from GenerateNE.generate()
    """
    task.set_ne = ne_result.assumption_ids
    task.set_kb.extend(ne_result.new_clauses)
    task.assumptions.extend(ne_result.new_assumptions)
    task.neg_c_map.update(ne_result.neg_map)
    for ne_id in ne_result.assumption_ids:
        task.assumption_to_constraint[ne_id] = f"ne_{ne_id}"
