"""
GenerateNE Algorithm for generating negated negative examples.

Uses QuickXPlain to find minimal conflict sets from negative examples,
then negates them to create NE constraints.

Reference: Paper Section "ConGen (Algorithm 1)"
- GENERATENE(E-) activates QUICKXPLAIN once per negative example e- in E-.
- NE is a set of constraints such that: if e-_i in E- then not(e-_i) in NE

Purity contract:
    generate() does NOT mutate the caller's result_set_kb.  It keeps a local
    accumulator so successive testcases still see prior NE clauses, then
    returns the NE clauses list.  The caller (ConGenTaskPreparation) extends
    its own KB copy from the returned NE clauses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Tuple

from explanation.operations.algorithms.checker import NonIncrementalPySATChecker
from explanation.operations.algorithms.quickxplain import QuickXPlain

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle
    from explanation.models.testsuite import TestCase, TestSuite


@dataclass
class NEPerTestcase:
    """Result of NE generation for a single testcase."""
    ne_id: int          # assumption ID for this NE
    ne_clause: List[int]  # blocking clause WITH assumption literal (ready to add to KB)
    desc: str           # description string


class GenerateNE:
    """Generate negated negative examples using QuickXPlain.

    For each negative example e-, finds the minimal conflict set
    and creates a blocking clause.

    Pure: generate() does not mutate the caller's result_set_kb.
    A local accumulator is used so that successive testcases within
    the same generate() call see prior NE clauses (preserving
    cross-testcase visibility that existed previously).
    """

    def __init__(self, oracle: 'FeatureModelOracle') -> None:
        self.oracle = oracle

    def generate(
            self,
            testsuite: 'TestSuite',
            variables: Dict[str, int],
            result_set_kb: List[List[int]],
            result_assumptions: List[int],
            start_id: int
    ) -> Tuple[List[NEPerTestcase], int]:
        """Generate NE from negative examples using QuickXPlain.

        Per testcase: merges oracle KB with result KB + accumulated NE clauses,
        creates assignment clauses, runs QuickXPlain for minimal conflict,
        creates blocking clause.

        PURE: does not append to result_set_kb.  Returns NE clauses;
        the caller must extend its own KB.

        Args:
            testsuite: Negative test cases
            variables: Feature name -> SAT variable mapping
            result_set_kb: Task KB snapshot (read-only — not mutated)
            result_assumptions: Task assumptions (read-only snapshot)
            start_id: Starting assumption ID

        Returns:
            (per_testcase_results, next_id_assumption)
            Each NEPerTestcase.ne_clause is the blocking clause that must
            be appended to the task KB by the caller.
        """
        if not testsuite.testcases:
            return [], start_id

        set_bg = self.oracle.get_c()
        results: List[NEPerTestcase] = []
        id_assumption = start_id

        # Local accumulator: starts as a copy of the caller's KB;
        # NE clauses from previous testcases are appended here so
        # subsequent testcases see them — without touching the caller's list.
        local_kb = list(result_set_kb)

        for testcase in testsuite.testcases:
            ne, id_assumption = self._process_testcase(
                testcase, variables, local_kb, result_assumptions,
                set_bg, id_assumption)
            results.append(ne)
            # Accumulate NE clause locally so the next testcase in this loop
            # sees it (cross-testcase visibility preserved).
            local_kb.append(ne.ne_clause)

        logging.debug('<<< GenerateNE: %d NE constraints', len(results))
        return results, id_assumption

    def _process_testcase(
            self,
            testcase: 'TestCase',
            variables: Dict[str, int],
            local_kb: List[List[int]],
            result_assumptions: List[int],
            set_bg: List[int],
            id_assumption: int
    ) -> Tuple[NEPerTestcase, int]:
        """Process single testcase: merge KBs, QuickXPlain, create NE clause."""
        # Merge oracle KB with current local KB (creates new list for this call)
        set_kb = self.oracle.get_kb() + local_kb
        assumptions = self.oracle.get_assumptions() + list(result_assumptions)

        # Create per-assignment clauses
        set_tv, assumption_to_var, assumption_to_desc = [], {}, {}
        for assignment in testcase.assignments:
            if assignment.feature not in variables:
                raise KeyError(f'Feature {assignment.feature} is not in the model.')

            desc = f'{assignment.feature} = {"true" if assignment.value else "false"}'
            var = variables[assignment.feature] if assignment.value else -variables[assignment.feature]

            set_tv.append(id_assumption)
            assumptions.append(id_assumption)
            set_kb.append([var, -1 * id_assumption])
            assumption_to_var[id_assumption] = var
            assumption_to_desc[id_assumption] = desc
            id_assumption += 1

        # QuickXPlain for minimal conflict
        checker = NonIncrementalPySATChecker(set_kb, assumptions)
        quickxplain = QuickXPlain(checker)
        minimal_conflict = quickxplain.find_conflict(set_tv, set_bg)
        if len(minimal_conflict) > 0:
            set_tv = minimal_conflict

        # Filter literals from minimal conflict
        literals, desc_parts = [], []
        for lit in set_tv:
            if lit in assumption_to_var:
                literals.append(assumption_to_var[lit])
                desc_parts.append(assumption_to_desc[lit])

        # Create NE clause: not(e) = (not(l1) or not(l2) or ... or not(ne_id))
        ne_id = id_assumption
        ne_clause = [-lit for lit in literals]
        ne_clause.append(-ne_id)
        # NOTE: do NOT append to local_kb here — caller (_process_testcase's
        # parent loop in generate()) handles accumulation after receiving result.

        id_assumption += 1
        return NEPerTestcase(
            ne_id=ne_id, ne_clause=ne_clause,
            desc=f"NOT({' & '.join(desc_parts)})"
        ), id_assumption
