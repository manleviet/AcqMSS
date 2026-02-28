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
        # Constraint NOT(name) -> negated CNF clauses (populated by builder)
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        # Feature name -> SAT variable ID (from bias)
        self.variables: Dict[str, int] = {}
        # Next available assumption ID (set by builder after negation)
        self.next_available_id: int = 0

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

    # Convenience getters (delegate to result)
    def get_c(self) -> List:
        """Get the set of potentially faulty constraints."""
        return self._require_task().set_c

    def get_b(self) -> List:
        """Get the background knowledge."""
        return self._require_task().set_b

    # def get_cf(self) -> List:
    #     """Get all constraints (C ∪ B) for redundancy detection.
    #
    #     Returns:
    #         List of all constraint IDs (set_c + set_b).
    #     """
    #     return self._require_task().get_cf()

    def get_kb(self) -> List[List]:
        """Get the full knowledge base with assumptions."""
        return self._require_task().set_kb

    def get_negation_map(self) -> dict:
        """Get the mapping from original to negated assumption IDs.

        Returns:
            Dict mapping original assumption ID to negated assumption ID,
            or empty dict if no negated forms.
        """
        return self._require_task().negation_map

    def get_assumptions(self) -> List:
        """Get the list of assumption literals."""
        return self._require_task().assumptions

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
