"""Shared fluent base for bias+oracle model builders (ConGen, QuAcq).

Factors the ``load bias → instantiate → negation-via-oracle`` skeleton common to
``ConGenModelBuilder`` and ``QuAcqModelBuilder`` into one template, leaving each
concrete builder only two hooks: which model class to instantiate, and what to do
once negation is computed (apply solver mode, assignment maps, auto-prepare).

This lives in ``conacq`` (the application), NOT ``explanation`` (the framework):
it imports ``conacq.bias`` and is typed against the conacq ``FMOracle``,
so placing it in the framework would leak app knowledge into it — the boundary
guard forbids that (explanation must not import conacq). It inherits the framework
base ``AbstractModelBuilder`` through the single public door, ``explanation.api``.
"""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from explanation.api import AbstractModelBuilder

if TYPE_CHECKING:
    from conacq.oracle import OracleData


class OracleBiasModelBuilder(AbstractModelBuilder):
    """Fluent base for bias+oracle models (ConGen, QuAcq).

    ``build()`` (inherited template) runs ``_validate`` then ``_create_model``.
    ``_create_model`` here is the shared bias-load + negation-via-oracle flow; the
    model-specific parts are delegated to ``_create_model_instance()`` and
    ``_post_negation_build(model)``.
    """

    def __init__(self) -> None:
        super().__init__()
        self._bias_path: Optional[str] = None
        self._oracle: Optional['OracleData'] = None
        self._use_incremental: bool = True

    @classmethod
    def from_bias(cls, bias_path: str) -> 'OracleBiasModelBuilder':
        """Create builder from a bias JSON file."""
        builder = cls()
        builder._bias_path = bias_path
        return builder

    def with_oracle(self, oracle: 'OracleData') -> 'OracleBiasModelBuilder':
        """Set the provisioning snapshot (required — supplies BG data + next_available_id).

        Takes the frozen OracleData, not the live oracle: the builder provisions
        the model (job ②) and must not read a live actor's state (ADR-0009).
        """
        self._oracle = oracle
        return self

    def use_incremental(self, enabled: bool = True) -> 'OracleBiasModelBuilder':
        """Set incremental solver mode (the subclass hook applies it to the model)."""
        self._use_incremental = enabled
        return self

    def _validate(self) -> None:
        """Require a bias path and an oracle."""
        if self._bias_path is None:
            raise ValueError("Bias path required (use from_bias())")
        if self._oracle is None:
            raise ValueError("Oracle required (use with_oracle())")

    def _create_model(self) -> Any:
        """Load bias, instantiate the model, compute negation, run the post hook."""
        from conacq.bias import BiasIO
        from explanation.api import negate_cnf_tseitin

        bias = BiasIO.load_from_json(self._bias_path)

        model = self._create_model_instance()
        model.constraint_map = bias.to_constraint_map()
        model.name_to_id = bias.feature_ids
        model.id_to_name = {vid: name for name, vid in bias.feature_ids.items()}

        # Compute negation at build time (oracle supplies the first free Tseitin id).
        next_tseitin_var = self._oracle.get_bg_data().next_available_id
        for key, clauses in model.constraint_map.items():
            neg_clauses, next_tseitin_var = negate_cnf_tseitin(clauses, next_tseitin_var)
            model.negated_constraint_map[f"NOT({key})"] = neg_clauses
        model.next_available_id = next_tseitin_var

        self._post_negation_build(model)
        return model

    @abstractmethod
    def _create_model_instance(self) -> Any:
        """Return a new, empty model object (ConGenModel / QuAcqModel)."""
        ...

    def _post_negation_build(self, model: Any) -> None:
        """Hook run after negation: apply solver mode, assignment maps, auto-prepare.

        Default is a no-op; each subclass overrides it. (T11.4 will fold a frozen
        OracleData snapshot here so prepare_task needs no live oracle parameter.)
        """
