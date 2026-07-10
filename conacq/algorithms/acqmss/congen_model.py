"""
Model for ConGen algorithm.

Pure data container for bias constraints and solver config.
Oracle injected at prepare() time — model has no FM dependency.

Uses existing classes from explanation module:
- Assignment, TestCase, TestSuite from explanation.models.testsuite
- TaskInput, DescriptionProvider from explanation.models.task_preparation

ConGenModel uses composition to delegate task preparation to ConGenTaskPreparation.
Call prepare(oracle) before accessing task or description_provider.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from conacq.kb_model import KBModel
from explanation.models.task_preparation import TaskInput, DescriptionProvider, TestCaseTask, cf
from explanation.models.testsuite import Assignment, TestCase, TestSuite
from .task_preparation import ConGenTask

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle
    from .congen import ConGenResult


class ConGenModel(KBModel):
    """Pure data container for ConGen algorithm.

    Holds bias constraints, variables, and solver config.
    Oracle injected at prepare() time — no FM dependency.

    Call prepare(oracle) before accessing task or description_provider.
    """

    def __init__(self) -> None:
        super().__init__()

        # CheckerModel protocol attributes
        self._use_incremental: bool = True

        # Background knowledge (e.g., root feature IDs) to include in set_b
        # self.background_knowledge: List[int] = []

        # Task input populated by builder or caller before prepare()
        self._task_input: TaskInput = TaskInput()

        # Populated after prepare()
        self._task: Optional[ConGenTask] = None
        self._description_provider: Optional[DescriptionProvider] = None
        self._root_constraint: Optional[List[List[int]]] = None

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
    def task(self) -> Optional[ConGenTask]:
        """Get prepared task, or None if prepare() has not been called."""
        return self._task

    @property
    def description_provider(self) -> DescriptionProvider:
        """Get description provider. Call prepare() first."""
        if self._description_provider is None:
            raise RuntimeError("Call prepare() first")
        return self._description_provider

    def _require_task(self) -> ConGenTask:
        """Return task or raise if not prepared."""
        if self._task is None:
            raise RuntimeError("Model not prepared. Call prepare() first.")
        return self._task

    # Convenience getters (delegate to result)
    def get_c(self) -> List:
        """Get the set of potentially faulty constraints."""
        return self._require_task().set_c

    def get_b(self) -> List:
        """Get the background knowledge."""
        return self._require_task().set_b

    def get_cf(self) -> List:
        """Get all constraints (C ∪ B) for redundancy detection.

        Returns:
            List of all constraint IDs (set_c + set_b).
        """
        return cf(self._require_task())

    def get_kb(self) -> List[List]:
        """Get the full knowledge base with assumptions."""
        return self._require_task().set_kb

    def get_negation_map(self) -> dict:
        """Get the mapping from original to negated assumption IDs.

        Returns:
            Dict mapping original assumption ID to negated assumption ID,
            or empty dict if no negated forms.
        """
        return self._require_task().negation_map

    def get_assumptions(self) -> List:
        """Get the list of assumption literals."""
        return self._require_task().assumptions

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

    def _resolve_ids(self, assumption_ids: List[int]) -> Tuple[List[List[int]], List[str]]:
        """Resolve assumption IDs to clauses and names via constraint_map.

        Args:
            assumption_ids: Assumption IDs to resolve.

        Returns:
            (clauses, names) — clauses from constraint_map, names from description_provider.
        """
        provider = self.description_provider
        clauses: List[List[int]] = []
        names: List[str] = []
        for aid in assumption_ids:
            name = provider.get_description(aid)
            names.append(name)
            if name in self.constraint_map:
                clauses.extend(self.constraint_map[name])
        return clauses, names

    def resolve_result(self, result: ConGenResult) -> Tuple[List[List[int]], List[List[int]], List[str], List[str]]:
        """Resolve a ConGenResult into clauses and names.

        Args:
            result: ConGenResult with assumption IDs.

        Returns:
            (bg_clauses, kb_clauses, kb_names, redundant_names)
        """
        bg_clauses = self._root_constraint or []
        kb_clauses, kb_names = self._resolve_ids(result.kb_assumption_ids)
        _, redundant_names = self._resolve_ids(result.redundant_ids)
        return bg_clauses, kb_clauses, kb_names, redundant_names

    def prepare(
            self,
            oracle: FeatureModelOracle,
            positive_examples: Optional[List[Dict[str, bool]]] = None,
            negative_examples: Optional[List[Dict[str, bool]]] = None
    ) -> ConGenTask:
        """Prepare ConGen task including GenerateNE.

        Oracle injected here — model stays FM-agnostic.
        Can be called multiple times (e.g., for CV folds).

        Args:
            oracle: Feature model oracle for NE generation and FM metadata
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

        # Run ConGenTaskPreparation (oracle provides BGData + GenerateNE)
        from .task_preparation import ConGenTaskPreparation
        preparation = ConGenTaskPreparation()
        output = preparation.prepare(self, oracle)

        assert isinstance(output.task, ConGenTask)
        self._task = output.task
        self._description_provider = output.description_provider
        self._root_constraint = oracle.get_root_clauses()

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
