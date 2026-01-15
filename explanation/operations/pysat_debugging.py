"""Debugging operation using KBDiag algorithm with test cases.

This module provides diagnosis operations using the KBDiag algorithm
which works with positive and negative test cases.
"""
from typing import Tuple, Optional

from explanation.models.pysat_diagnosis_model import DiagnosisModel
from explanation.models.testsuite import TestSuite
from explanation.operations.algorithms.checker import ConsistencyChecker
from explanation.operations.algorithms.hsdag.hsdag import HSDAG
from explanation.operations.algorithms.hsdag.labeler.kbdiag_labeler import KBDiagLabeler, KBDiagParameters
from explanation.operations.algorithms.profiler import AbstractProfiler
from explanation.operations.pysat_abstract_explanation import PySATAbstractExplanation


class PySATDebugging(PySATAbstractExplanation):
    """Operation for debugging using KBDiag algorithm with test cases.

    This operation computes diagnoses using the KBDiag algorithm which
    works with positive and negative test cases.

    Attributes:
        positive_test_cases: TestSuite of positive test cases
        negative_test_cases: Optional TestSuite of negative test cases
        m: Parameter for KBDiag algorithm (default: 1)
    """

    def __init__(self, profiler_instance: AbstractProfiler = None) -> None:
        """Initialize debugging operation with default values."""
        super().__init__(profiler_instance)
        self.positive_test_cases: Optional[TestSuite] = None
        self.negative_test_cases: Optional[TestSuite] = None
        self._m: int = 1

    def set_positive_test_cases(self, test_cases: TestSuite) -> None:
        """Set positive test cases.

        Args:
            test_cases: TestSuite of positive test cases
        """
        self.positive_test_cases = test_cases

    def set_negative_test_cases(self, test_cases: TestSuite) -> None:
        """Set negative test cases.

        Args:
            test_cases: TestSuite of negative test cases
        """
        self.negative_test_cases = test_cases

    @property
    def m(self) -> int:
        """Get the parameter m."""
        return self._m

    @m.setter
    def m(self, value: int) -> None:
        """Set m parameter for KBDiag algorithm.

        Args:
            value: parameter value (must be positive or default: 1)

        Raises:
            ValueError: If value is not positive
        """
        if value < 1:
            raise ValueError(f"the parameter m must be positive and greater than 1, got {value}")
        self._m = value

    def _prepare_model_for_diagnosis(self, model: DiagnosisModel) -> None:
        """Prepare model for debugging task with test cases.

        Overrides parent method to use prepare_debugging_task() instead.

        Args:
            model: Diagnosis model to prepare
        """
        if self.positive_test_cases is None:
            raise ValueError("positive_test_cases must be set before execution")

        model.prepare_debugging_task(
            positive_test_cases=self.positive_test_cases,
            negative_test_cases=self.negative_test_cases
        )

    def _create_labeler(self, checker: ConsistencyChecker, model: DiagnosisModel) -> KBDiagLabeler:
        """Create KBDiag labeler for HSDAG.

        Args:
            checker: Consistency checker instance
            model: Diagnosis model

        Returns:
            KBDiagLabeler instance
        """
        set_c = model.get_c()
        set_b = model.get_b()
        set_tc = model.get_tc()
        set_tv = model.get_tv()

        parameters = KBDiagParameters(set_c, set_b, set_tv, set_tc)
        return KBDiagLabeler(checker, self.m, parameters)

    def prepare_hsdag(self, model: DiagnosisModel) -> Tuple[ConsistencyChecker, HSDAG]:
        """Prepare HSDAG with KBDiag labeler for debugging computation.

        This method uses the helper methods to:
        1. Prepare the diagnosis model
        2. Create a consistency checker
        3. Create a KBDiag labeler
        4. Configure HSDAG with operation parameters

        Args:
            model: Diagnosis model to use

        Returns:
            Tuple of (consistency_checker, configured_hsdag)
        """
        # Prepare model for debugging task
        self._prepare_model_for_diagnosis(model)

        checker = self._create_checker(model)
        labeler = self._create_labeler(checker, model)

        return checker, self._create_hsdag(labeler)

    def set_result_messages(self, cs_mess: str, diag_mess: str) -> None:
        """Set result messages with diagnoses first.

        Args:
            cs_mess: Formatted conflicts message
            diag_mess: Formatted diagnoses message
        """
        self.result_messages = [diag_mess, cs_mess]
