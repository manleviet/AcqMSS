"""Test case operation using HSDAG + QuickXPlainWithTestCases algorithm with test cases.

This module provides diagnosis operations using the HSDAG + QuickXPlainWithTestCases algorithm
which works with positive and negative test cases.
"""
from typing import Tuple

from explanation.models.task_preparation import PreparedTask, Task
from explanation.checker.protocols import ConsistencyChecker
from explanation.operations.algorithms.hsdag.hsdag import HSDAG
from explanation.operations.algorithms.hsdag.labeler.quickxplain_with_testcases_labeler import \
    QuickXPlainWithTestCasesParameters, QuickXPlainWithTestCasesLabeler
from profiling import AbstractProfiler
from explanation.operations.pysat_abstract_hsdag_explanation import PySATAbstractHSDAGExplanation


class PySATTestCaseQuickXPlain(PySATAbstractHSDAGExplanation):
    """Operation for test case diagnosis using HSDAG + QuickXPlainWithTestCases algorithm.

    This operation computes conflicts using the QuickXPlainWithTestCases algorithm which
    works with positive and negative test cases.
    """

    def __init__(self, profiler_instance: AbstractProfiler = None) -> None:
        """Initialize test case operation with default values."""
        super().__init__(profiler_instance)

    def _create_labeler(self, checker: ConsistencyChecker, task: Task) -> QuickXPlainWithTestCasesLabeler:
        """Create QuickXPlainWithTestCasesLabeler labeler for HSDAG.

        Args:
            checker: Consistency checker instance
            task: Task carrying set_c, set_b, set_tc, set_neg_tv

        Returns:
            QuickXPlainWithTestCasesLabeler instance
        """
        parameters = QuickXPlainWithTestCasesParameters(
            task.set_c, task.set_b, task.set_tc, task.set_neg_tv)
        return QuickXPlainWithTestCasesLabeler(checker, parameters)

    def prepare_hsdag(self, prepared: PreparedTask) -> Tuple[ConsistencyChecker, HSDAG]:
        """Prepare HSDAG with QuickXPlainWithTestCases labeler for test case computation.

        Args:
            prepared: PreparedTask to use

        Returns:
            Tuple of (consistency_checker, configured_hsdag)
        """
        task = prepared.task
        checker = self._create_checker(task)
        labeler = self._create_labeler(checker, task)

        return checker, self._create_hsdag(labeler)

    def set_result_messages(self, cs_mess: str, diag_mess: str) -> None:
        """Set result messages with diagnoses first.

        Args:
            cs_mess: Formatted conflicts message
            diag_mess: Formatted diagnoses message
        """
        self.result_messages = [diag_mess, cs_mess]
