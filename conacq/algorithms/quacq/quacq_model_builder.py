"""Fluent builder for QuAcqModel, mirroring ConGenModelBuilder API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .quacq_model import QuAcqModel

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle


class QuAcqModelBuilder:
    """Fluent builder for QuAcqModel.

    Examples:
        oracle = FeatureModelOracle('data/fms/model.uvl')
        model = (QuAcqModelBuilder
                 .from_bias('data/bias/model.json')
                 .with_oracle(oracle)
                 .build())  # Returns prepared model with task ready
    """

    def __init__(self) -> None:
        self._bias_path: Optional[str] = None
        self._oracle: Optional[FeatureModelOracle] = None
        self._use_incremental: bool = True

    @classmethod
    def from_bias(cls, bias_path: str) -> QuAcqModelBuilder:
        """Create builder from bias JSON file."""
        builder = cls()
        builder._bias_path = bias_path
        return builder

    def with_oracle(self, oracle: FeatureModelOracle) -> QuAcqModelBuilder:
        """Set oracle (required). Enables auto-prepare during build()."""
        self._oracle = oracle
        return self

    def use_incremental(self, enabled: bool = True) -> QuAcqModelBuilder:
        """Set incremental solver mode."""
        self._use_incremental = enabled
        return self

    def build(self) -> QuAcqModel:
        """Build and return prepared QuAcqModel.

        Computes negation at build time, then auto-prepares.

        Raises:
            ValueError: If bias path or oracle missing
        """
        self._validate()

        from conacq.bias import BiasIO
        from explanation.operations.algorithms.utils import negate_cnf_tseitin

        bias = BiasIO.load_from_json(self._bias_path)

        model = QuAcqModel()
        model.constraint_map = bias.to_constraint_map()
        model.variables = bias.feature_ids
        model.features = {var_id: name for name, var_id in model.variables.items()}
        model.use_incremental = self._use_incremental

        # Compute negation at build time (before prepare)
        next_tseitin_var = self._oracle.get_bg_data().next_available_id
        for key, c in model.constraint_map.items():
            neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
            model.negated_constraint_map[f"NOT({key})"] = neg_clauses
        model.next_available_id = next_tseitin_var

        model.pos_assignment_to_assumption = dict(self._oracle.get_bg_data().pos_assignment_to_assumption)
        model.neg_assignment_to_assumption = dict(self._oracle.get_bg_data().neg_assignment_to_assumption)

        model.prepare(self._oracle)
        return model

    def _validate(self) -> None:
        """Validate builder state."""
        if self._bias_path is None:
            raise ValueError("Bias path required (use from_bias())")
        if self._oracle is None:
            raise ValueError("Oracle required (use with_oracle())")
