"""Builder for creating configured ConGenModel instances.

Mirrors DiagnosisModelBuilder pattern. Encapsulates file loading,
model creation, and prepare() invocation.
"""

from typing import Dict, List, Optional, Tuple

from .congen_model import ConGenModel


class ConGenModelBuilder:
    """Fluent builder for ConGenModel.

    Examples:
        # From files (with examples)
        model = (ConGenModelBuilder
            .from_bias_and_fm_uvl('data/bias/model.json', 'data/fms/model.uvl')
            .with_examples('data/examples/examples.json')
            .use_incremental(True)
            .build())

        # Without examples (for CV — build once, prepare per fold)
        model = (ConGenModelBuilder
            .from_bias_and_fm_uvl('data/bias/model.json', 'data/fms/model.uvl')
            .use_incremental(True)
            .build())
        model.prepare(positive_examples=fold_pos, negative_examples=fold_neg)
    """

    def __init__(self):
        # Bias
        self._bias_path: Optional[str] = None

        # Feature Model
        self._fm_source_type: Optional[str] = None
        self._fm_path: Optional[str] = None

        # Examples
        self._examples_path: Optional[str] = None

        self._positive_examples: Optional[List[Dict[str, bool]]] = None
        self._negative_examples: Optional[List[Dict[str, bool]]] = None

        # Mode flags - Default is True since need negation bias constraints and NE
        # self._for_redundancy: bool = True

        # Solver configuration
        self._use_incremental: bool = True

    @classmethod
    def from_bias_and_fm_fide(cls, bias_path: str, fide_fm_path: str) -> 'ConGenModelBuilder':
        """Create builder from bias and FeatureIDE feature model files."""
        builder = cls()
        builder._bias_path = bias_path
        builder._fm_source_type = 'fide'
        builder._fm_path = fide_fm_path
        return builder

    @classmethod
    def from_bias_and_fm_uvl(cls, bias_path: str, uvl_fm_path: str) -> 'ConGenModelBuilder':
        """Create builder from bias and UVL feature model files."""
        builder = cls()
        builder._bias_path = bias_path
        builder._fm_source_type = 'uvl'
        builder._fm_path = uvl_fm_path
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
        """Build and return configured ConGenModel.

        If examples are provided, calls prepare() and returns a fully prepared model.
        If no examples, returns an unprepared model (for CV — use prepare() per fold).

        Raises:
            ValueError: If bias/FM paths missing
        """
        self._validate()

        from acqmss.bias import BiasIO

        bias = BiasIO.load_from_json(self._bias_path)

        # Build model
        model = ConGenModel()
        model.constraint_map, model.negated_constraint_map, model.next_tseitin_var \
            = bias.to_constraint_maps_with_negation()
        model.variables = bias.feature_ids
        model.root_feature = bias.root_feature
        model.use_incremental = self._use_incremental

        # Set examples + prepare only if examples provided
        if self._has_examples():
            pos_examples, neg_examples = self._resolve_examples()
            # model.task_input = TaskInput(
            #     positive_test_cases=ConGenModel._examples_to_testsuite(pos_examples),
            #     negative_test_cases=ConGenModel._examples_to_testsuite(neg_examples),
            #     for_redundancy=True
            # )
            model.prepare(positive_examples=pos_examples, negative_examples=neg_examples)

        return model

    def _has_examples(self) -> bool:
        """Check if examples were provided (file or data)."""
        return (self._examples_path is not None
                or self._positive_examples is not None)

    def _validate(self) -> None:
        """Validate builder state."""
        if self._bias_path is None or self._fm_path is None:
            raise ValueError(
                "Source must be specified (use from_bias_and_fm_uvl() or from_bias_and_fm_fide())")

    def _resolve_examples(self) -> Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]:
        """Load examples from path or return direct data."""
        if self._positive_examples is not None:
            return self._positive_examples, self._negative_examples

        from acqmss.examples import ExampleIO
        examples = ExampleIO.load_json(self._examples_path)
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        return pos, neg
