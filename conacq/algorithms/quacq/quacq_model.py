"""
Model for QuAcq constraint acquisition.

Parallel to ConGenModel — stores bias data, delegates preparation
to QuAcqTaskPreparation, produces QuAcqTask.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from explanation.models.task_preparation import DescriptionProvider

from .task_preparation import QuAcqTask, QuAcqTaskPreparation

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle


class QuAcqModel:
    """Model for QuAcq interactive learning, parallel to ConGenModel.

    Pure data container for bias constraints and solver config.
    Oracle injected at prepare() time — model has no FM dependency.

    Usage:
        oracle = FeatureModelOracle('data/fms/model.uvl')
        model = (QuAcqModelBuilder
                 .from_bias('data/bias/model.json')
                 .with_oracle(oracle)
                 .build())  # Returns prepared model
        task = model.task  # QuAcqTask with assumption IDs
    """

    def __init__(self) -> None:
        # Constraint name -> raw CNF clauses
        self.constraint_map: Dict[str, List[List[int]]] = {}
        # Constraint NOT(name) -> negated CNF clauses (populated at prepare())
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        # Feature name -> SAT variable ID (from bias)
        self.variables: Dict[str, int] = {}
        # Store incremental preference for CheckerModel protocol
        self.use_incremental: bool = True

        # Populated after prepare()
        self._task: Optional[QuAcqTask] = None
        self._description_provider: Optional[DescriptionProvider] = None

    @property
    def task(self) -> Optional[QuAcqTask]:
        """Get prepared QuAcqTask (None if prepare() not called)."""
        return self._task

    @property
    def description_provider(self) -> DescriptionProvider:
        """Get DescriptionProvider for resolving assumption IDs to names.

        Raises:
            RuntimeError: If prepare() has not been called yet
        """
        if self._description_provider is None:
            raise RuntimeError("Call prepare() first")
        return self._description_provider

    def prepare(self, oracle: 'FeatureModelOracle') -> QuAcqTask:
        """Assign assumption IDs and build QuAcqTask.

        Args:
            oracle: FeatureModelOracle for BG data and feature IDs

        Returns:
            Prepared QuAcqTask with assumption IDs assigned
        """
        preparation = QuAcqTaskPreparation()
        output = preparation.prepare(self, oracle)
        assert isinstance(output.task, QuAcqTask)
        self._task = output.task
        self._description_provider = output.description_provider
        return self._task

    def resolve_kb(self, kb_assumption_ids: List[int]) -> Tuple[List[str], List[List[int]]]:
        """Resolve assumption IDs to constraint names and raw clauses.

        Args:
            kb_assumption_ids: List of learned KB assumption IDs

        Returns:
            Tuple of (constraint_names, combined_raw_clauses)
        """
        provider = self.description_provider
        names = [provider.get_description(aid) for aid in kb_assumption_ids]
        clauses: List[List[int]] = []
        for aid in kb_assumption_ids:
            name = provider.get_description(aid)
            if name in self.constraint_map:
                clauses.extend(self.constraint_map[name])
        return names, clauses

# Backward-compat alias for legacy code
InteractiveModel = QuAcqModel
