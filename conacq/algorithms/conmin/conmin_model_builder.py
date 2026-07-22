"""Fluent builder for ConMinModel, mirroring ConGenModelBuilder.

The bias-load → negation-via-oracle skeleton lives in ``OracleBiasModelBuilder``;
this builder only supplies the model-instance hook. The model it returns is a pure
KB: preparation (task + describe) is derived per run via ``model.prepare_task(...)``,
not baked in at build time. Solver mode is the caller's, not the model's.
"""

from __future__ import annotations

from conacq.oracle_bias_model_builder import OracleBiasModelBuilder

from .conmin_model import ConMinModel


class ConMinModelBuilder(OracleBiasModelBuilder[ConMinModel]):
    """Fluent builder for ConMinModel.

    Examples:
        oracle = FMOracle('data/fms/model.uvl')
        model = (ConMinModelBuilder
                 .from_bias('data/bias/model.json')
                 .with_oracle_data(oracle.oracle_data)
                 .build())  # pure KB; call model.prepare_task(...) to get a task
    """

    # === OracleBiasModelBuilder template hook ===

    def _create_model_instance(self) -> ConMinModel:
        """Return a new, empty ConMinModel (bias KB filled by the base template)."""
        return ConMinModel()
