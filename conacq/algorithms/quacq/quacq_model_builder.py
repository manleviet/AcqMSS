"""Fluent builder for QuAcqModel, mirroring ConGenModelBuilder API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .quacq_model import QuAcqModel

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle
    from .task_preparation import QuAcqTask


class QuAcqModelBuilder:
    """Fluent builder for QuAcqModel.

    Examples:
        oracle = FeatureModelOracle('data/fms/model.uvl')
        builder = (QuAcqModelBuilder
                   .from_bias('data/bias/model.json')
                   .with_oracle(oracle))
        model = builder.build()
        task = builder.last_task   # QuAcqTask prepared during build()
        checker = CheckerFactory.create_from_task(task)
    """

    def __init__(self) -> None:
        self._bias_path: Optional[str] = None
        self._oracle: Optional[FeatureModelOracle] = None

        # Last prepared task (set by build())
        self.last_task: Optional['QuAcqTask'] = None

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

    def build(self) -> QuAcqModel:
        """Build and return prepared QuAcqModel.

        Computes negation at build time, then prepares a QuAcqTask.
        The prepared task is stored on self.last_task for retrieval by callers.

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

        # Compute negation at build time (before prepare)
        next_tseitin_var = self._oracle.get_bg_data().next_available_id
        for key, c in model.constraint_map.items():
            neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
            model.negated_constraint_map[f"NOT({key})"] = neg_clauses
        model.next_available_id = next_tseitin_var

        self.last_task = model.prepare_task(self._oracle)
        return model

    def _validate(self) -> None:
        """Validate builder state."""
        if self._bias_path is None:
            raise ValueError("Bias path required (use from_bias())")
        if self._oracle is None:
            raise ValueError("Oracle required (use with_oracle())")
