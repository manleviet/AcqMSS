"""Builder for creating configured ConGenModel instances.

Handles bias loading, solver config, and optional auto-prepare.
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from .congen_model import ConGenModel

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle


class ConGenModelBuilder:
    """Fluent builder for ConGenModel.

    Examples:
        # Pattern 1: Auto-prepare from file
        oracle = FeatureModelOracle('data/fms/model.uvl')
        model = (ConGenModelBuilder
                 .from_bias('data/bias/model.json')
                 .with_oracle(oracle)
                 .with_examples('data/examples/model.json')
                 .build())  # Returns prepared model

        # Pattern 2: Auto-prepare from raw data
        model = (ConGenModelBuilder
                 .from_bias('data/bias/model.json')
                 .with_oracle(oracle)
                 .with_examples_data(positive_examples=pos, negative_examples=neg)
                 .build())  # Returns prepared model

        # Pattern 3: CV build-once, prepare per fold
        model = ConGenModelBuilder.from_bias('data/bias/model.json').build()
        for fold_pos, fold_neg in folds:
            model.prepare(oracle, positive_examples=fold_pos, negative_examples=fold_neg)
    """

    def __init__(self):
        self._bias_path: Optional[str] = None

        # Oracle (optional, enables auto-prepare)
        self._oracle: Optional['FeatureModelOracle'] = None

        # Examples (optional, for convenience)
        self._examples_path: Optional[str] = None
        self._positive_examples: Optional[List[Dict[str, bool]]] = None
        self._negative_examples: Optional[List[Dict[str, bool]]] = None

        # Solver configuration
        self._use_incremental: bool = True

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

    def use_incremental(self, enabled: bool = True) -> 'ConGenModelBuilder':
        """Set incremental solver mode."""
        self._use_incremental = enabled
        return self

    def build(self) -> ConGenModel:
        """Build and return configured ConGenModel.

        Auto-prepares if both oracle and examples are set.
        Otherwise returns unprepared model for manual prepare().

        Raises:
            ValueError: If bias path missing
        """
        self._validate()

        from conacq.bias import BiasIO

        bias = BiasIO.load_from_json(self._bias_path)

        model = ConGenModel()
        model.constraint_map = bias.to_constraint_map()
        model.variables = bias.feature_ids
        model._use_incremental = self._use_incremental

        # Auto-prepare when oracle + examples present
        if self._oracle and self._has_examples():
            pos, neg = self._resolve_examples()
            model.prepare(
                oracle=self._oracle,
                positive_examples=pos,
                negative_examples=neg or []
            )

        return model

    def get_examples(self) -> Optional[Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]]:
        """Get resolved examples if any were provided."""
        if not self._has_examples():
            return None
        return self._resolve_examples()

    def _has_examples(self) -> bool:
        """Check if examples were provided (file or data)."""
        return (self._examples_path is not None
                or self._positive_examples is not None)

    def _validate(self) -> None:
        """Validate builder state."""
        if self._bias_path is None:
            raise ValueError("Bias path required (use from_bias())")

    def _resolve_examples(self) -> Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]:
        """Load examples from path or return direct data."""
        if self._positive_examples is not None:
            return self._positive_examples, self._negative_examples or []

        from conacq.examples import ExampleIO
        examples = ExampleIO.load_json(self._examples_path)
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        return pos, neg
