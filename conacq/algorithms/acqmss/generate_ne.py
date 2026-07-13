"""
GenerateNE Algorithm for generating negated negative examples.

Uses QuickXPlain to find minimal conflict sets from negative examples,
then negates them to create NE constraints.

Reference: Paper Section "ConGen (Algorithm 1)"
- GENERATENE(E-) activates QUICKXPLAIN once per negative example e- in E-.
- NE is a set of constraints such that: if e-_i in E- then not(e-_i) in NE
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Tuple

from explanation.api import build_checker, SolverBackend, DiagnosisTask
from explanation.api import QuickXPlain

if TYPE_CHECKING:
    from conacq.oracle import KBProvider
    from explanation.api import TestCase, TestSuite


@dataclass
class NEPerTestcase:
    """Result of NE generation for a single testcase."""
    ne_id: int  # assumption ID for this NE
    ne_clause: List[int]  # blocking clause with assumption literal
    desc: str  # description string


class GenerateNE:
    """Generate negated negative examples using QuickXPlain.

    For each negative example e-, finds the minimal conflict set
    and creates a blocking clause. NE clauses are appended to the
    result KB so subsequent testcases see previous NEs.
    """

    def __init__(self, oracle: KBProvider) -> None:
        self.oracle = oracle

    def generate(
            self,
            testsuite: TestSuite,
            variables: Dict[str, int],
            result_set_kb: List[List[int]],
            result_assumptions: List[int],
            start_id: int
    ) -> Tuple[List[NEPerTestcase], int]:
        """Generate NE from negative examples using QuickXPlain.

        Per testcase: merges oracle KB with result KB, creates assignment
        clauses, runs QuickXPlain for minimal conflict, creates blocking clause.

        Args:
            testsuite: Negative test cases
            variables: Feature name -> SAT variable mapping
            result_set_kb: Task KB (mutated: NE clauses appended)
            result_assumptions: Task assumptions (read-only snapshot per iteration)
            start_id: Starting assumption ID

        Returns:
            (per_testcase_results, next_id_assumption)
        """
        if not testsuite.testcases:
            return [], start_id

        set_bg = self.oracle.get_c()
        results: List[NEPerTestcase] = []
        id_assumption = start_id

        for testcase in testsuite.testcases:
            ne, id_assumption = self._process_testcase(
                testcase, variables, result_set_kb, result_assumptions,
                set_bg, id_assumption)
            results.append(ne)

        logging.debug('<<< GenerateNE: %d NE constraints', len(results))
        return results, id_assumption

    def _process_testcase(
            self,
            testcase: TestCase,
            variables: Dict[str, int],
            result_set_kb: List[List[int]],
            result_assumptions: List[int],
            set_bg: List[int],
            id_assumption: int
    ) -> Tuple[NEPerTestcase, int]:
        """Process single testcase: merge KBs, QuickXPlain, create NE clause."""
        # Merge oracle KB with current result KB (creates new list)
        set_kb = self.oracle.get_kb() + result_set_kb
        assumptions = self.oracle.get_assumptions() + result_assumptions

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

        # QuickXPlain for minimal conflict. The per-testcase subproblem is itself
        # a Task (set_c = test-value assumptions, set_b = background), so the
        # checker is built through the port like everywhere else.
        task = DiagnosisTask(set_c=set_tv, set_b=set_bg,
                             set_kb=set_kb, assumptions=assumptions)
        # One checker per testcase — release its solver before the next iteration.
        with build_checker(task, SolverBackend.PYSAT_NON_INCREMENTAL) as checker:
            quickxplain = QuickXPlain(checker)
            minimal_conflict = quickxplain.find_conflict(task.set_c, task.set_b)
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
        result_set_kb.append(ne_clause)  # mutate for subsequent testcases

        id_assumption += 1
        return NEPerTestcase(
            ne_id=ne_id, ne_clause=ne_clause,
            desc=f"NOT({' & '.join(desc_parts)})"
        ), id_assumption
