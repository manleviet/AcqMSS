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

        Always auto-prepares using the configured oracle.

        Raises:
            ValueError: If bias path or oracle missing
        """
        self._validate()

        from conacq.bias import BiasIO

        bias = BiasIO.load_from_json(self._bias_path)

        model = QuAcqModel()
        model.constraint_map = bias.to_constraint_map()
        model.variables = bias.feature_ids
        model.use_incremental = self._use_incremental

        model.prepare(self._oracle)
        return model

    def _validate(self) -> None:
        """Validate builder state."""
        if self._bias_path is None:
            raise ValueError("Bias path required (use from_bias())")
        if self._oracle is None:
            raise ValueError("Oracle required (use with_oracle())")
