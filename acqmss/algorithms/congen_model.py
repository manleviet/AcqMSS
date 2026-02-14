"""
Model for ConGen algorithm.

Uses existing classes from explanation module:
- Assignment, TestCase, TestSuite from explanation.models.testsuite
- TaskInput, DescriptionProvider from explanation.models.task_preparation

ConGenModel uses composition to delegate task preparation to ConGenTaskPreparation.
Call prepare() before accessing task or description_provider.
"""

from typing import Dict, List, Optional

from explanation.models.testsuite import Assignment, TestCase, TestSuite
from explanation.models.task_preparation import TaskInput, DescriptionProvider

from .task_preparation import ConGenTask


class ConGenModel:
    """Model for ConGen algorithm.

    Uses composition to delegate task preparation to ConGenTaskPreparation.
    Call prepare() before accessing task or description_provider.

    Unlike DiagnosisModel, this doesn't require a feature model and works
    directly with bias constraints.
    """

    def __init__(self) -> None:
        self.constraint_map: Dict[str, List[List[int]]] = {}
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        self.variables: Dict[str, int] = {}
        self.task_input: TaskInput = TaskInput()
        self.next_tseitin_var: int = 1
        self.background_knowledge: List[int] = []

        # Populated after prepare()
        self._task: Optional[ConGenTask] = None
        self._description_provider: Optional[DescriptionProvider] = None

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

    def prepare(self, mode_name: str = "congen") -> ConGenTask:
        """Prepare ConGen task using ConGenTaskPreparation strategy.

        Args:
            mode_name: Mode name for logging (e.g., "incremental-congen")

        Returns:
            ConGenTask ready for GenerateNE and ConGen.
        """
        from .task_preparation import ConGenTaskPreparation

        preparation = ConGenTaskPreparation(mode_name)
        output = preparation.prepare(self)

        assert isinstance(output.task, ConGenTask)
        self._task = output.task
        self._description_provider = output.description_provider
        return self._task

    @classmethod
    def from_bias_and_examples(
            cls,
            bias_constraints: Dict[str, List[List[int]]],
            positive_examples: List[Dict[str, bool]],
            negative_examples: List[Dict[str, bool]],
            feature_ids: Dict[str, int],
            background_knowledge: Optional[List[int]] = None
    ) -> 'ConGenModel':
        """Create model from bias constraints and examples.

        Args:
            bias_constraints: {constraint_name: [clauses]} from bias
            positive_examples: List of valid configurations {feature: bool}
            negative_examples: List of invalid configurations {feature: bool}
            feature_ids: {feature_name: variable_id}
            background_knowledge: BG literals (e.g., [root_feature_id])

        Returns:
            ConGenModel ready for prepare()
        """
        # Find max variable ID for Tseitin allocation
        max_var = max(feature_ids.values()) if feature_ids else 0
        for clauses in bias_constraints.values():
            for clause in clauses:
                for lit in clause:
                    max_var = max(max_var, abs(lit))

        # Convert examples to test suites
        positive_tc = cls._examples_to_testsuite(positive_examples)
        negative_tc = cls._examples_to_testsuite(negative_examples)

        model = cls()
        model.constraint_map = bias_constraints
        model.variables = feature_ids
        model.task_input = TaskInput(
            positive_test_cases=positive_tc,
            negative_test_cases=negative_tc
        )
        model.next_tseitin_var = max_var + 1
        model.background_knowledge = background_knowledge or []
        return model

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
