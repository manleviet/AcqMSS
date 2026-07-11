"""Fluent builder for QuAcqModel, mirroring ConGenModelBuilder API.

The bias-load → negation-via-oracle skeleton lives in OracleBiasModelBuilder;
this builder supplies the two template hooks.
"""

from __future__ import annotations

from conacq.oracle_bias_model_builder import OracleBiasModelBuilder

from .quacq_model import QuAcqModel


class QuAcqModelBuilder(OracleBiasModelBuilder):
    """Fluent builder for QuAcqModel.

    Examples:
        oracle = FeatureModelOracle('data/fms/model.uvl')
        model = (QuAcqModelBuilder
                 .from_bias('data/bias/model.json')
                 .with_oracle(oracle)
                 .build())  # Returns prepared model with task ready
    """

    # === OracleBiasModelBuilder template hooks ===

    def _create_model_instance(self) -> QuAcqModel:
        """Return a new, empty QuAcqModel."""
        return QuAcqModel()

    def _post_negation_build(self, model: QuAcqModel) -> None:
        """Apply solver mode, copy BG assignment maps, then auto-prepare."""
        model.use_incremental = self._use_incremental
        bg_data = self._oracle.get_bg_data()
        model.pos_assignment_to_assumption = dict(bg_data.pos_assignment_to_assumption)
        model.neg_assignment_to_assumption = dict(bg_data.neg_assignment_to_assumption)
        model.prepare(self._oracle)
