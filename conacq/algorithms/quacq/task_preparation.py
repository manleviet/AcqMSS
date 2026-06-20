"""
QuAcqTask: assumption-ID-based task for QuAcq constraint acquisition.

Parallel to ConGenTask — uses integer assumption IDs instead of string IDs,
inherits DiagnosisTask for set_kb/assumptions/negation_map/set_b fields.
Also contains QuAcqTaskPreparation (co-located: creation logic next to data).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Dict

from explanation.models.task_preparation import (
    DescriptionProvider,
    DiagnosisTask,
    PreparationOutput,
    prepare_kb,
    _ASSUMPTION_PAIR_STRIDE,
)
from conacq.algorithms.oracle_aware_task_preparation import OracleAwareTaskPreparation

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle
    from .quacq_model import QuAcqModel


@dataclass
class QuAcqTask(DiagnosisTask):
    """Immutable task for QuAcq constraint acquisition.

    Inherits from DiagnosisTask:
        set_c:         Bias constraint assumption IDs (same role as ConGenTask)
        set_b:         BG assumption IDs (from BGData root constraint)
        set_kb:        Full KB with assumption guards
        negation_map:  {assumption_id -> negated_assumption_id}
        assumptions:   All assumption IDs

    QuAcq-specific immutable data:
        constraint_clauses:   assumption_id -> raw CNF clauses (no guards)

    Mutable state (remaining_bias, learned_kb, n_queries, query_history)
    lives in the QuAcq algorithm, not here.
    """
    # assumption_id -> raw clauses (WITHOUT assumption guards, for violation checking)
    constraint_clauses: Dict[int, List[List[int]]] = field(default_factory=dict)

    def get_constraint_vars(self, assumption_id: int) -> set:
        """Feature names referenced by constraint with given assumption ID.

        Uses codec to translate raw clause variable IDs to feature names.
        Returns empty set if assumption_id unknown or codec not attached.
        """
        if self.codec is None:
            return set()
        clauses = self.constraint_clauses.get(assumption_id, [])
        return self.codec.get_constraint_vars(clauses)

    def get_constraints_with_scope(self, scope: set, remaining_bias: set) -> list:
        """Bias constraint IDs whose variables match scope.

        Prefers exact scope match (c_vars == scope). Falls back to subset
        match (c_vars ⊆ scope) if no exact matches found.
        """
        exact = []
        subset = []
        for aid in remaining_bias:
            c_vars = self.get_constraint_vars(aid)
            if not c_vars:
                continue
            if c_vars == scope:
                exact.append(aid)
            elif c_vars.issubset(scope):
                subset.append(aid)
        return exact if exact else subset


class QuAcqTaskPreparation(OracleAwareTaskPreparation):
    """Prepare QuAcqTask from bias + oracle. No E+/E-.

    Assumption ID layout (QuAcq owns Parts 5-6):
      Parts 1-4: Owned by Oracle (see OracleTaskPreparation)
      Part 5:    Tseitin vars (negated bias constraints)   <- This method
      Part 6:    Bias constraint assumptions (paired)      <- This method
    """

    def prepare(self, model: QuAcqModel,
                oracle: FeatureModelOracle) -> PreparationOutput:
        """Prepare QuAcqTask from model and oracle.

        Args:
            model: QuAcqModel with bias constraint_map
            oracle: FeatureModelOracle for BG data and feature IDs

        Returns:
            PreparationOutput with QuAcqTask and DescriptionProvider
        """
        result = QuAcqTask()
        provider = DescriptionProvider()

        # Step 0: Copy BG data from Oracle (Parts 3 + 4).
        # Part 3: root constraint pair (shared with ConGen via mixin).
        # Part 4: feature assignment assumptions (QuAcq-specific pruning).
        bg_data = oracle.get_bg_data()
        self._copy_bg_data_part3(result, provider, bg_data)
        self._copy_bg_data_part4(result, bg_data)

        # Step 1: Assign assumption IDs (negated forms from builder)
        id_assumption = model.next_available_id
        bias_start_pos = len(result.assumptions)
        id_assumption = prepare_kb(
            result, provider, model.constraint_map,
            id_assumption, model.negated_constraint_map)
        # Assign set_b and set_c from assumptions
        self._assign_sets(result, bias_start_pos)

        # Step 2: Build constraint_clauses mapping
        for aid in result.set_c:
            name = provider.get_description(aid)
            if name in model.constraint_map:
                result.constraint_clauses[aid] = model.constraint_map[name]

        return PreparationOutput(result, provider)

    @staticmethod
    def _assign_sets(result: QuAcqTask, bias_start_pos: int) -> None:
        """Assign set_b and set_c from assumptions."""
        result.set_b = [result.assumptions[0]]
        result.set_c = list(result.assumptions[bias_start_pos::_ASSUMPTION_PAIR_STRIDE])
