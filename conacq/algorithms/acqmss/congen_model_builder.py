"""Builder for creating configured ConGenModel instances.

Handles bias loading, solver config, and optional auto-prepare.
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from .congen_model import ConGenModel

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle
    from .task_preparation import ConGenTask


class ConGenModelBuilder:
    """Fluent builder for ConGenModel.

    Examples:
        # Pattern 1: Auto-prepare from file
        oracle = FeatureModelOracle('data/fms/model.uvl')
        builder = (ConGenModelBuilder
                   .from_bias('data/bias/model.json')
                   .with_oracle(oracle)
                   .with_examples('data/examples/model.json'))
        model = builder.build()
        task = builder.last_task  # ConGenTask from auto-prepare

        # Pattern 2: Auto-prepare from raw data
        builder = (ConGenModelBuilder
                   .from_bias('data/bias/model.json')
                   .with_oracle(oracle)
                   .with_examples_data(positive_examples=pos, negative_examples=neg))
        model = builder.build()
        task = builder.last_task

        # Pattern 3: CV build-once, prepare per fold
        model = (ConGenModelBuilder.from_bias('data/bias/model.json')
                 .with_oracle(oracle)
                 .build())
        for fold_pos, fold_neg in folds:
            task_input = ConGenModelBuilder.make_task_input(model, fold_pos, fold_neg)
            task = model.prepare_task(task_input, oracle)
    """

    def __init__(self):
        self._bias_path: Optional[str] = None

        # Oracle (optional, enables auto-prepare)
        self._oracle: Optional['FeatureModelOracle'] = None

        # Examples (optional, for convenience)
        self._examples_path: Optional[str] = None
        self._positive_examples: Optional[List[Dict[str, bool]]] = None
        self._negative_examples: Optional[List[Dict[str, bool]]] = None

        # Last prepared task (set by build() when examples are provided)
        self.last_task: Optional['ConGenTask'] = None

    @classmethod
    def from_bias(cls, bias_path: str) -> 'ConGenModelBuilder':
        """Create builder from bias JSON file."""
        builder = cls()
        builder._bias_path = bias_path
        return builder

    def with_oracle(self, oracle: 'FeatureModelOracle') -> 'ConGenModelBuilder':
        """Set oracle for auto-prepare during build()."""
        self._oracle = oracle
        return self

    def with_examples(self, examples_path: str) -> 'ConGenModelBuilder':
        """Set examples file path (contains both E+ and E-).

        Clears any previously set raw example data (last-call-wins).
        """
        self._examples_path = examples_path
        self._positive_examples = None
        self._negative_examples = None
        return self

    def with_examples_data(
            self,
            positive_examples: List[Dict[str, bool]],
            negative_examples: Optional[List[Dict[str, bool]]] = None
    ) -> 'ConGenModelBuilder':
        """Set example data directly (for CV folds).

        Clears any previously set file path (last-call-wins).
        """
        self._positive_examples = positive_examples
        self._negative_examples = negative_examples
        self._examples_path = None
        return self


    def build(self) -> ConGenModel:
        """Build and return configured ConGenModel.

        Computes negation at build time (requires oracle).
        Auto-prepares if examples are also set; the resulting task is
        stored on self.last_task for retrieval by the caller.

        Raises:
            ValueError: If bias path or oracle missing
        """
        self._validate()

        from conacq.bias import BiasIO
        from explanation.operations.algorithms.utils import negate_cnf_tseitin

        bias = BiasIO.load_from_json(self._bias_path)

        model = ConGenModel()
        model.constraint_map = bias.to_constraint_map()
        model.variables = bias.feature_ids

        # Compute negation at build time (requires oracle for next_available_id)
        next_tseitin_var = self._oracle.get_bg_data().next_available_id
        for key, c in model.constraint_map.items():
            neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
            model.negated_constraint_map[f"NOT({key})"] = neg_clauses
        model.next_available_id = next_tseitin_var

        # Auto-prepare when examples are present; cache the task on the builder
        self.last_task = None
        if self._has_examples():
            pos, neg = self._resolve_examples()
            task_input = self._make_task_input(model, pos, neg or [])
            self.last_task = model.prepare_task(task_input, self._oracle)

        return model

    def get_examples(self) -> Optional[Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]]:
        """Get resolved examples if any were provided."""
        if not self._has_examples():
            return None
        return self._resolve_examples()

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _has_examples(self) -> bool:
        """Check if examples were provided (file or data)."""
        return (self._examples_path is not None
                or self._positive_examples is not None)

    def _validate(self) -> None:
        """Validate builder state."""
        if self._bias_path is None:
            raise ValueError("Bias path required (use from_bias())")
        if self._oracle is None:
            raise ValueError("Oracle required (use with_oracle())")

    def _resolve_examples(self) -> Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]:
        """Load examples from path or return direct data."""
        if self._positive_examples is not None:
            return self._positive_examples, self._negative_examples or []

        from conacq.examples import ExampleIO
        examples = ExampleIO.load_json(self._examples_path)
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        return pos, neg

    @staticmethod
    def _make_task_input(model: ConGenModel,
                         positive_examples: List[Dict[str, bool]],
                         negative_examples: List[Dict[str, bool]]):
        """Build a TaskInput from example lists."""
        from explanation.models.task_preparation import TaskInput
        from explanation.models.testsuite import Assignment, TestCase, TestSuite

        def to_testsuite(examples):
            testcases = [
                TestCase(assignments=[
                    Assignment(feature=name, value=value)
                    for name, value in ex.items()
                ])
                for ex in examples
            ]
            return TestSuite(testcases=testcases)

        return TaskInput(
            positive_test_cases=to_testsuite(positive_examples),
            negative_test_cases=to_testsuite(negative_examples),
            for_redundancy=True,
        )
