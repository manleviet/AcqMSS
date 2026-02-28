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


class QuAcqTaskPreparation:
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

        # Step 0: Copy BG data from Oracle (root constraint pair)
        bg_data = oracle.get_bg_data()
        result.set_kb.extend(bg_data.set_kb)
        result.assumptions.extend(list(bg_data.assumptions))
        result.negation_map.update(bg_data.negation_map)
        for aid, desc in bg_data.descriptions.items():
            provider.add_constraint_description(aid, desc)

        # Copy Part 4 data from BGData (feature assignment assumptions)
        result.set_kb.extend(bg_data.assignment_clauses)
        result.assumptions.extend(bg_data.assignment_assumptions)

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
