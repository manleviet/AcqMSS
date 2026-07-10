"""
Model for QuAcq constraint acquisition.

Parallel to ConGenModel — stores bias data, delegates preparation
to QuAcqTaskPreparation, produces QuAcqTask.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

from conacq.kb_model import KBModel
from explanation.models import encoding
from explanation.models.assignment_assumption_map import AssignmentAssumptionMap
from explanation.models.task_preparation import DescriptionProvider

from .task_preparation import QuAcqTask, QuAcqTaskPreparation

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle


class QuAcqModel(KBModel):
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
        super().__init__()

        # Solver selection consumed by CheckerFactory.create_from_task()
        self.use_incremental: bool = True

        # Populated after prepare()
        self._task: Optional[QuAcqTask] = None
        self._description_provider: Optional[DescriptionProvider] = None

        self.pos_assignment_to_assumption: Dict[str, int] = {}
        self.neg_assignment_to_assumption: Dict[str, int] = {}

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

    def _require_task(self) -> QuAcqTask:
        """Return task or raise if not prepared."""
        if self._task is None:
            raise RuntimeError("Model not prepared. Call prepare() first.")
        return self._task

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
        """Get full KB: bias + root BG + Part 4 assignment clauses."""
        task = self._require_task()
        # return task.set_kb + task.assignment_clauses
        return task.set_kb

    def get_negation_map(self) -> dict:
        """Get the mapping from original to negated assumption IDs.

        Returns:
            Dict mapping original assumption ID to negated assumption ID,
            or empty dict if no negated forms.
        """
        return self._require_task().negation_map

    def get_assumptions(self) -> List:
        """Get all assumptions: bias + root BG + Part 4 assignments."""
        task = self._require_task()
        # return list(task.assumptions) + task.assignment_assumptions
        return list(task.assumptions)

    def config_to_assumptions(self, config: Dict[str, bool]) -> List[int]:
        """Convert feature config to Part 4 assignment assumption IDs.

        Args:
            config: Feature name -> bool assignment

        Returns:
            List of assumption IDs for the given feature assignments
        """
        return encoding.config_to_assignment_assumptions(
            config,
            AssignmentAssumptionMap(
                self.pos_assignment_to_assumption,
                self.neg_assignment_to_assumption))

    def get_constraint_vars(self, assumption_id: int) -> Set[str]:
        """Get feature names for constraint by assumption ID."""
        clauses = self._require_task().constraint_clauses.get(assumption_id, [])
        return encoding.get_constraint_vars(clauses, self.id_to_name)

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
        self._description_provider = output.describe

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

    def model_to_config(self, model):
        """Convert SAT model to configuration dictionary."""
        return encoding.variable_literals_to_config(model, self.id_to_name)

    def get_constraints_with_scope(self,
                                   scope: set,
                                   remaining_bias: set) -> List[int]:
        """Get bias constraint IDs whose variables match scope.

        Prefers exact scope match (c_vars == scope). Falls back to subset
        match (c_vars ⊆ scope) if no exact matches found.
        """
        exact = []
        subset = []
        task = self._require_task()
        # Collects bias constraints matching scope exactly or subset
        for aid in remaining_bias:
            c_vars = self.get_constraint_vars(aid)
            if not c_vars:
                continue
            if c_vars == scope:
                exact.append(aid)
            elif c_vars.issubset(scope):
                subset.append(aid)
        return exact if exact else subset
