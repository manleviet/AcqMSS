"""
Model for ConGen algorithm.

Uses existing classes from explanation module:
- Assignment, TestCase, TestSuite from explanation.models.testsuite
- TaskInput, DescriptionProvider from explanation.models.task_preparation

ConGenModel uses composition to delegate task preparation to ConGenTaskPreparation.
Call prepare() before accessing task or description_provider.
"""

from typing import Dict, List, Optional

from explanation.models.task_preparation import TaskInput, DescriptionProvider, TestCaseTask
from explanation.models.testsuite import Assignment, TestCase, TestSuite
from .task_preparation import ConGenTask
from ..oracle import FeatureModelOracle


class ConGenModel:
    """Model for ConGen algorithm.

    Uses composition to delegate task preparation to ConGenTaskPreparation.
    Call prepare() before accessing task or description_provider.

    Unlike DiagnosisModel, this doesn't require a feature model and works
    directly with bias constraints.
    """

    def __init__(self) -> None:
        self._fm_path: Optional[str] = None
        self._oracle: Optional[FeatureModelOracle] = None

        # map clauses to bias relationships/constraint
        self.constraint_map: Dict[str, List[List[int]]] = {}
        # map negated clauses to bias relationships/constraint (for redundancy detection)
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        # map feature names to IDs (for debugging and description generation)
        self.variables: Dict[str, int] = {}
        # number of fm constraints
        self.num_fm_constraints: int = 0
        # Used as starting ID for assumption literals to avoid conflicts.
        self.next_tseitin_var: int = 1000

        # CheckerModel protocol attributes
        self._use_incremental: bool = True

        # Task input populated by builder or caller before prepare()
        self._task_input: TaskInput = TaskInput()

        # Background knowledge (e.g., root feature IDs) to include in set_b
        self.root_feature: Optional[str] = None
        # self.background_knowledge: List[int] = []

        # Populated after prepare()
        self._task: Optional[ConGenTask] = None
        self._description_provider: Optional[DescriptionProvider] = None

    @property
    def oracle(self):
        return self._oracle

    @property
    def use_incremental(self) -> bool:
        """Whether to use incremental solver."""
        return self._use_incremental

    @property
    def task_input(self) -> TaskInput:
        """Get task input."""
        return self._task_input

    @task_input.setter
    def task_input(self, value: TaskInput) -> None:
        """Set task input."""
        self._task_input = value

    @property
    def task(self) -> ConGenTask:
        """Get prepared task. Call prepare() first."""
        if self._task is None:
            raise RuntimeError("Call prepare() first")
        return self._task

    @property
    def description_provider(self) -> DescriptionProvider:
        """Get description provider. Call prepare() first."""
        if self._description_provider is None:
            raise RuntimeError("Call prepare() first")
        return self._description_provider

    # Convenience getters (delegate to result)
    def get_c(self) -> List:
        """Get the set of potentially faulty constraints."""
        return self.task.set_c

    def get_b(self) -> List:
        """Get the background knowledge."""
        return self.task.set_b

    def get_cf(self) -> List:
        """Get all constraints (C ∪ B) for redundancy detection.

        Returns:
            List of all constraint IDs (set_c + set_b).
        """
        return self.task.get_cf()

    def get_kb(self) -> List[List]:
        """Get the full knowledge base with assumptions."""
        return self.task.set_kb

    def get_neg_c_map(self) -> dict:
        """Get the mapping from constraint to negated constraint IDs.

        Returns:
            Dict mapping original constraint ID to negated constraint ID,
            or empty dict if no negated forms.
        """
        return self.task.neg_c_map

    def get_assumptions(self) -> List:
        """Get the list of assumption literals."""
        return self.task.assumptions

    def get_tc(self) -> List:
        """Get the positive test cases (debugging task only).

        Returns:
            List of positive test case assumptions, or empty list if not debugging task.
        """
        if isinstance(self.task, TestCaseTask):
            return self.task.set_tc
        return []

    def get_tv(self) -> List:
        """Get the negative test cases (debugging task only).

        Returns:
            List of negative test case assumptions, or empty list if not debugging task.
        """
        if isinstance(self.task, TestCaseTask):
            return self.task.set_tv
        return []

    def get_neg_tv(self) -> List:
        """Get the negated negative test cases (debugging task only).

        Used by KBDiag for B = B ∪ neg_Tν.

        Returns:
            List of negated negative test case assumptions, or empty list if not debugging task.
        """
        if isinstance(self.task, TestCaseTask):
            return self.task.set_neg_tv
        return []

    def get_neg_tc(self) -> List:
        """Get the negated positive test cases (debugging task only).

        Used for WipeOutR algorithm.

        Returns:
            List of negated positive test case assumptions, or empty list if not debugging task.
        """
        if isinstance(self.task, TestCaseTask):
            return self.task.set_neg_tc
        return []

    def get_neg_tc_map(self) -> dict:
        """Get the mapping from test case to negated test case IDs.

        Returns:
            Dict mapping original test case ID to negated test case ID,
            or empty dict if not debugging task.
        """
        if isinstance(self.task, TestCaseTask):
            return self.task.neg_tc_map
        return {}

    def prepare(
            self,
            positive_examples: Optional[List[Dict[str, bool]]] = None,
            negative_examples: Optional[List[Dict[str, bool]]] = None
    ) -> ConGenTask:
        """Prepare ConGen task including GenerateNE.

        If examples provided, updates task_input before preparing.
        Runs GenerateNE internally (callers no longer need to).
        Can be called multiple times (e.g., for CV folds) — each call
        overwrites the previous task state.

        Args:
            positive_examples: Optional new E+ (for fold reuse)
            negative_examples: Optional new E- (for fold reuse)

        Returns:
            ConGenTask with set_neg_tv already populated.
        """
        # Update task_input if new examples provided
        if positive_examples is not None or negative_examples is not None:
            pos_tc = self._examples_to_testsuite(positive_examples or [])
            neg_tc = self._examples_to_testsuite(negative_examples or [])
            self.task_input = TaskInput(
                positive_test_cases=pos_tc,
                negative_test_cases=neg_tc,
                for_redundancy=True
            )

        # Step 1: Run ConGenTaskPreparation
        from .task_preparation import ConGenTaskPreparation
        preparation = ConGenTaskPreparation()
        output = preparation.prepare(self)

        assert isinstance(output.task, ConGenTask)
        self._task = output.task
        self._description_provider = output.description_provider

        return self._task

    @staticmethod
    def _examples_to_testsuite(examples: List[Dict[str, bool]]) -> TestSuite:
        """Convert list of example dicts to TestSuite."""
        testcases = []
        for example in examples:
            assignments = [
                Assignment(feature=name, value=value)
                for name, value in example.items()
            ]
            testcases.append(TestCase(assignments=assignments))
        return TestSuite(testcases=testcases)
