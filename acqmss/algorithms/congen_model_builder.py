"""Builder for creating configured ConGenModel instances.

Handles bias loading and solver config only.
Oracle creation is the caller's responsibility.
"""

from typing import Dict, List, Optional, Tuple

from .congen_model import ConGenModel


class ConGenModelBuilder:
    """Fluent builder for ConGenModel.

    Examples:
        # Build model, prepare separately
        model = ConGenModelBuilder.from_bias('data/bias/model.json').build()
        oracle = FeatureModelOracle('data/fms/model.uvl')
        model.prepare(oracle, positive_examples=pos, negative_examples=neg)

        # For CV: build once, prepare per fold
        model = ConGenModelBuilder.from_bias('data/bias/model.json').build()
        oracle = FeatureModelOracle('data/fms/model.uvl')
        for fold_pos, fold_neg in folds:
            model.prepare(oracle, positive_examples=fold_pos, negative_examples=fold_neg)
    """

    def __init__(self):
        self._bias_path: Optional[str] = None

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

    def with_examples(self, examples_path: str) -> 'ConGenModelBuilder':
        """Set examples file path (contains both E+ and E-)."""
        self._examples_path = examples_path
        return self

    def with_examples_data(
            self,
            positive: List[Dict[str, bool]],
            negative: List[Dict[str, bool]]
    ) -> 'ConGenModelBuilder':
        """Set example data directly (for CV folds)."""
        self._positive_examples = positive
        self._negative_examples = negative
        return self

    def use_incremental(self, enabled: bool = True) -> 'ConGenModelBuilder':
        """Set incremental solver mode."""
        self._use_incremental = enabled
        return self

    def build(self) -> ConGenModel:
        """Build and return configured ConGenModel (unprepared).

        Returns model with bias loaded. Caller must call
        model.prepare(oracle, pos_examples, neg_examples) before use.

        Raises:
            ValueError: If bias path missing
        """
        self._validate()

        from acqmss.bias import BiasIO

        bias = BiasIO.load_from_json(self._bias_path)

        model = ConGenModel()
        model.constraint_map = bias.to_constraint_map()
        model.variables = bias.feature_ids
        model._use_incremental = self._use_incremental

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
            return self._positive_examples, self._negative_examples

        from acqmss.examples import ExampleIO
        examples = ExampleIO.load_json(self._examples_path)
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        return pos, neg
