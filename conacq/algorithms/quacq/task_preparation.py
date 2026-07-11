"""
QuAcqTask: assumption-ID-based task for QuAcq constraint acquisition.

Parallel to ConGenTask — uses integer assumption IDs instead of string IDs,
inherits DiagnosisTask for set_kb/assumptions/negation_map/set_b fields.
Also contains QuAcqTaskPreparation (co-located: creation logic next to data).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Tuple

from explanation.api import (
    DescriptionProvider,
    DiagnosisTask,
    PreparedTask,
    prepare_kb,
)
if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle
    from .quacq_model import QuAcqModel


@dataclass(frozen=True)
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
                oracle: FeatureModelOracle) -> PreparedTask:
        """Prepare QuAcqTask from model and oracle.

        Build-then-freeze: accumulate into locals, construct frozen QuAcqTask once.

        Args:
            model: QuAcqModel with bias constraint_map
            oracle: FeatureModelOracle for BG data and feature IDs

        Returns:
            PreparedTask with QuAcqTask and DescriptionProvider
        """
        provider = DescriptionProvider()

        # Local accumulation
        set_kb: List[List[int]] = []
        assumptions: List[int] = []
        negation_map: Dict[int, int] = {}

        # Step 0: Copy BG data from Oracle (root constraint pair)
        bg_data = oracle.get_bg_data()
        set_kb.extend(bg_data.set_kb)
        assumptions.extend(list(bg_data.assumptions))
        negation_map.update(bg_data.negation_map)
        for aid, desc in bg_data.descriptions.items():
            provider.add_constraint_description(aid, desc)

        # Copy Part 4 data from BGData (feature assignment assumptions)
        set_kb.extend(bg_data.assignment_clauses)
        assumptions.extend(bg_data.assignment_assumptions)

        # Step 1: Assign assumption IDs (negated forms from builder)
        id_assumption = model.next_available_id
        bias_start_pos = len(assumptions)
        id_assumption = prepare_kb(
            set_kb, assumptions, negation_map, provider,
            model.constraint_map, id_assumption, model.negated_constraint_map)
        # Assign set_b and set_c from assumptions
        set_b, set_c = self._assign_sets(assumptions, bias_start_pos)

        # Step 2: Build constraint_clauses mapping
        constraint_clauses: Dict[int, List[List[int]]] = {}
        for aid in set_c:
            name = provider.get_description(aid)
            if name in model.constraint_map:
                constraint_clauses[aid] = model.constraint_map[name]

        task = QuAcqTask(
            set_c=set_c, set_b=set_b, set_kb=set_kb,
            negation_map=negation_map, assumptions=assumptions,
            constraint_clauses=constraint_clauses)
        return PreparedTask(task, provider)

    @staticmethod
    def _assign_sets(assumptions: List[int], bias_start_pos: int) -> Tuple[List[int], List[int]]:
        """Compute (set_b, set_c) from assumptions."""
        set_b = [assumptions[0]]
        set_c = list(assumptions[bias_start_pos::2])
        return set_b, set_c
