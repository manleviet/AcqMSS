"""Diagnosis model."""

from typing import List, Dict, Optional

from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.pysat_metamodel.models import PySATModel

from .task_preparation import (
    TaskPreparationFactory,
    DiagnosisTask,
    IncrementalDiagnosisTask,
    DebuggingTask,
    DescriptionProvider,
    DiagnosisFormatter,
)
from .testsuite import TestSuite


class DiagnosisModel(PySATModel):
    """PySATModel extension for diagnosis tasks.

    This class uses composition to delegate task preparation to strategies:
    - IncrementalTaskPreparation: Uses assumptions for efficient repeated checks
    - NonIncrementalTaskPreparation: Uses clauses for each check

    Supported task types:
    1. Configuration diagnosis (is_CF_in_C = False):
        C = configuration, B = feature model (PySATModel) + root
    2. Configuration and feature model diagnosis (is_CF_in_C = True):
        C = configuration + feature model (PySATModel), B = root only
    2. Feature model diagnosis (test_case is None):
        C = FM constraints, B = root only
    3. Error diagnosis (debugging):
        C = FM constraints, B = root + test case
        where test_case is the following:
        + Dead feature: test_case = {fi = true}
        + False optional feature: test_case = {f_parent = true} & {f_child = false}
    4. Debugging task - Diagnosis with positive and negative test cases:
        C = FM constraints (excluding root)
        B = root constraint
        TC = positive test cases
        TV = negative test cases (optional)

    # 2. Redundancy Detection Task (need negative constraints)
    #     C = CF (i.e., = PySATModel - {f0 = true})
    #     B = {}
    """

    @staticmethod
    def get_extension() -> str:
        return 'pysat_diagnosis'

    def __init__(self) -> None:
        super().__init__()
        # map clauses to relationships/constraint
        self.constraint_map: Dict[str, List[List]] = {}
        self.is_incremental: bool = True  # default to use incremental solver
        self.is_CF_in_C: bool = False  # whether diagnosis for CF

        # Populated after prepare_diagnosis_task()
        self._task: Optional[DiagnosisTask] = None
        self._description_provider: Optional[DescriptionProvider] = None

    def add_clause_to_map(self, description: str, clauses: List[List]) -> None:
        """Add clauses with description to constraint map."""
        self.constraint_map[description] = clauses

    @property
    def task(self) -> DiagnosisTask:
        """Get the preparation result.
        Call prepare_diagnosis_task()/prepare_debugging_task()/prepare_redundancy_detection_task() first."""
        if self._task is None:
            raise RuntimeError("Call prepare_diagnosis_task()/"
                               "prepare_debugging_task()/prepare_redundancy_detection_task() first")
        return self._task

    @property
    def description_provider(self) -> DescriptionProvider:
        """Get the description provider.
        Call prepare_diagnosis_task()/prepare_debugging_task() first."""
        if self._description_provider is None:
            raise RuntimeError("Call prepare_diagnosis_task()/"
                               "prepare_debugging_task()/prepare_redundancy_detection_task() first")
        return self._description_provider

    # Convenience getters (delegate to result)
    def get_c(self) -> List:
        """Get the set of potentially faulty constraints."""
        return self.task.set_c

    def get_b(self) -> List:
        """Get the background knowledge."""
        return self.task.set_b

    def get_kb(self) -> List[List]:
        """Get the full knowledge base with assumptions."""
        return self.task.set_kb

    def get_assumptions(self) -> List:
        """Get the list of assumption literals (incremental mode only)."""
        if isinstance(self._task, IncrementalDiagnosisTask):
            return self._task.assumptions
        if isinstance(self._task, DebuggingTask):
            return self._task.assumptions
        return []

    def get_tc(self) -> List:
        """Get the positive test cases (debugging task only).

        Returns:
            List of positive test case assumptions, or empty list if not debugging task.
        """
        if isinstance(self._task, DebuggingTask):
            return self._task.set_tc
        return []

    def get_tv(self) -> List:
        """Get the negative test cases (debugging task only).

        Returns:
            List of negative test case assumptions, or empty list if not debugging task.
        """
        if isinstance(self._task, DebuggingTask):
            return self._task.set_tv
        return []

    def format_diagnoses(self, diagnoses: List[List]) -> str:
        """Format diagnoses for display.

        Args:
            diagnoses: List of diagnoses to format.

        Returns:
            Human-readable string representation.
        """
        return DiagnosisFormatter.format(diagnoses, self.description_provider)

    def prepare_diagnosis_task(self,
                               configuration: Configuration = None,
                               test_case: Configuration = None) -> DiagnosisTask:
        """Prepare model for diagnosis task.

        Supported task types:
        1. Configuration diagnosis (is_CF_in_C = False):
            C = configuration, B = feature model (PySATModel) + root
        2. Configuration and feature model diagnosis (is_CF_in_C = True):
            C = configuration + feature model (PySATModel), B = root only
        2. Feature model diagnosis (test_case is None):
            C = FM constraints, B = root only
        3. Error diagnosis (debugging):
            C = FM constraints, B = root + test case
            where test_case is the following:
            + Dead feature: test_case = {fi = true}
            + False optional feature: test_case = {f_parent = true} & {f_child = false}

        Args:
            configuration: Optional configuration to diagnose.
            test_case: Optional test case for error diagnosis.

        Returns:
            DiagnosisTask (IncrementalDiagnosisTask or NonIncrementalDiagnosisTask).
        """
        strategy = TaskPreparationFactory.create_diagnosis(self.is_incremental)
        output = strategy.prepare(
            variables=self.variables,
            constraint_map=self.constraint_map,
            configuration=configuration,
            test_case=test_case,
            is_CF_in_C=self.is_CF_in_C
        )

        self._task = output.task
        self._description_provider = output.description_provider
        return self._task

    def prepare_debugging_task(self,
                               positive_test_cases: TestSuite,
                               negative_test_cases: TestSuite = None) -> DebuggingTask:
        """Prepare model for debugging task with test cases.

        Uses KBDiag algorithm to find diagnoses based on positive/negative test cases.

        Debugging task:
            C = FM constraints (excluding root)
            B = root constraint
            TC = positive test cases
            TV = negative test cases (optional)

        Args:
            positive_test_cases: TestSuite of positive test cases that should pass.
            negative_test_cases: Optional TestSuite of negative test cases.

        Returns:
            DebuggingTask with set_c, set_b, set_tc, set_tv populated.
        """
        strategy = TaskPreparationFactory.create_debugging(self.is_incremental)
        output = strategy.prepare(
            variables=self.variables,
            constraint_map=self.constraint_map,
            positive_test_cases=positive_test_cases,
            negative_test_cases=negative_test_cases
        )

        self._task = output.task
        self._description_provider = output.description_provider
        return self._task

    def prepare_redundancy_detection_task(self) -> None:
        """Prepare for WipeOutR algorithm.

        C = CF (PySATModel - {f0 = true})
        B = {}

        Note: Not yet implemented.
        """
        pass
