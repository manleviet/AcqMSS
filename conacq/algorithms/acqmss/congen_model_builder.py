"""Builder for creating configured ConGenModel instances.

Handles bias loading, solver config, and optional auto-prepare. The bias-load →
negation-via-oracle skeleton lives in OracleBiasModelBuilder; this builder adds
example handling and supplies the two template hooks.
"""

from typing import Dict, List, Optional, Tuple

from conacq.oracle_bias_model_builder import OracleBiasModelBuilder

from .congen_model import ConGenModel


class ConGenModelBuilder(OracleBiasModelBuilder):
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
        model = (ConGenModelBuilder.from_bias('data/bias/model.json')
                 .with_oracle(oracle)
                 .build())
        for fold_pos, fold_neg in folds:
            model.prepare(oracle, positive_examples=fold_pos, negative_examples=fold_neg)
    """

    def __init__(self):
        super().__init__()
        # Examples (optional, for convenience)
        self._examples_path: Optional[str] = None
        self._positive_examples: Optional[List[Dict[str, bool]]] = None
        self._negative_examples: Optional[List[Dict[str, bool]]] = None

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

    # === OracleBiasModelBuilder template hooks ===

    def _create_model_instance(self) -> ConGenModel:
        """Return a new, empty ConGenModel."""
        return ConGenModel()

    def _post_negation_build(self, model: ConGenModel) -> None:
        """Apply solver mode, then auto-prepare when examples were provided."""
        model._use_incremental = self._use_incremental
        if self._has_examples():
            pos, neg = self._resolve_examples()
            model.prepare(
                oracle=self._oracle,
                positive_examples=pos,
                negative_examples=neg or []
            )

    # === Public / internal helpers ===

    def get_examples(self) -> Optional[Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]]:
        """Get resolved examples if any were provided."""
        if not self._has_examples():
            return None
        return self._resolve_examples()

    def _has_examples(self) -> bool:
        """Check if examples were provided (file or data)."""
        return (self._examples_path is not None
                or self._positive_examples is not None)

    def _resolve_examples(self) -> Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]:
        """Load examples from path or return direct data."""
        if self._positive_examples is not None:
            return self._positive_examples, self._negative_examples or []

        from conacq.examples import ExampleIO
        examples = ExampleIO.load_json(self._examples_path)
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        return pos, neg
