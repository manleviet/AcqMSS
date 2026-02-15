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

from acqmss.oracle import FeatureModelOracle
from explanation.models import TestSuite
from explanation.operations.algorithms.checker import ConsistencyChecker
from explanation.operations.algorithms.profiler import (
    measure_time, count_calls
)
from explanation.operations.algorithms.quickxplain import QuickXPlain


@dataclass
class NEResult:
    """Result of NE generation."""
    # assumption_ids: List[int]
    # neg_map: Dict[int, int]
    # original_literals: List[List[int]]
    new_clauses: List[List[int]] = field(default_factory=list)
    set_neg_tv: List[int] = field(default_factory=list)
    next_tseitin_var: int = 1000


class GenerateNE:
    """
    Generate negated negative examples using QuickXPlain.

    For each negative example e⁻, uses QuickXPlain to find the minimal
    conflict set, then creates a constraint that blocks that configuration.
    Returns new clauses and assumptions in NEResult for the caller to merge.

    NE = {¬(minimal_conflict(e⁻)) | e⁻ ∈ E⁻}
    """

    def __init__(self, checker: ConsistencyChecker, oracle: FeatureModelOracle) -> None:
        self.checker = checker
        self.quickxplain = QuickXPlain(checker)
        self.oracle = oracle

    @measure_time('generate_ne_runtime')
    @count_calls('generate_ne_calls')
    def generate(self, testsuite: TestSuite, set_bg: List[int],
                 start_assumption_id: int = 1000) -> NEResult:
        """
        Generate NE from negative examples using QuickXPlain.

        For each e⁻ (list of literals), uses QuickXPlain to find the minimal
        conflict set with respect to BG, then creates a blocking clause.

        Args:
            set_tv: List of negative examples, each is a list of literals
            set_bg: Background knowledge (assumption IDs)
            start_assumption_id: Starting ID for new assumptions

        Returns:
            NEResult with assumption IDs and neg_map
        """
        logging.debug('>>> GenerateNE [%d E⁻, BG=%s]', len(testsuite.testcases), set_bg)

        new_clauses = []
        set_neg_tv = []
        current_id = start_assumption_id

        # Iterates examples; creates blocking clauses and negated forms
        for testcase in testsuite.testcases:
            active_assumptions = []
            for feat, value in items:
                assumption = self._pos_assignment_to_assumption[feat] if value else self._neg_assignment_to_assumption[
                    feat]
                active_assumptions.append(assumption)

            step = 2
            set_c = [self._task.assumptions[i] for i in range(0, self.start_id_assignments, step)]
            set_c += active_assumptions

            # Use QuickXPlain to find minimal conflict
            # Wrap single assumption ID in list for find_conflict API
            tv_list = tv if isinstance(tv, list) else [tv]


            minimal_conflict = self.quickxplain.find_conflict(tv_list, set_bg)

            if len(minimal_conflict) == 0:
                new_tv = tv_list
                logging.debug('E⁻=%s consistent with BG, using full example', tv)
            else:
                new_tv = minimal_conflict
                logging.debug('E⁻=%s -> minimal conflict=%s', tv, minimal_conflict)

            # Create blocking clause: ¬(l1 ∧ l2 ∧ ...) = (¬l1 ∨ ¬l2 ∨ ...)
            blocking_clause = [-lit for lit in new_tv]

            # Collect clause and assumption (caller will merge into task)
            assumption_id = current_id
            current_id += 1
            new_clauses.append([-assumption_id] + blocking_clause)
            set_neg_tv.append(assumption_id)

            logging.debug('NE assumption=%d, clause=%s',
                          assumption_id, blocking_clause)

        logging.debug('<<< GenerateNE: %d NE constraints', len(set_neg_tv))

        return NEResult(
            new_clauses=new_clauses,
            set_neg_tv=set_neg_tv,
            next_tseitin_var=current_id
        )

def merge_ne_into_task(task, ne_result: NEResult) -> None:
    """Merge GenerateNE results into a ConGenTask.

    Updates task in-place:
    - set_neg_tv: NE assumption IDs
    - set_kb: appends new clauses
    - assumptions: appends new assumption IDs
    - neg_c_map: merges NE negation map
    - assumption_to_constraint: adds ne_X entries

    Args:
        task: ConGenTask to update
        ne_result: Result from GenerateNE.generate()
    """
    task.set_neg_tv = ne_result.set_neg_tv
    task.set_kb.extend(ne_result.new_clauses)
    task.assumptions.extend(ne_result.set_neg_tv)
    # task.neg_c_map.update(ne_result.neg_map)
    # for ne_id in ne_result.assumption_ids:
    #     task.assumption_to_constraint[ne_id] = f"ne_{ne_id}"
