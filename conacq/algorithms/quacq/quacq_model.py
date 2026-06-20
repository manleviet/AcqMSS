"""
Model for QuAcq constraint acquisition.

Thin KB + codec container parallel to ConGenModel.
Stores bias data; delegates preparation to QuAcqTaskPreparation.

prepare_task(oracle) -> QuAcqTask with attached codec + describe.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from explanation.models.codec import VariableCodec

from .task_preparation import QuAcqTask, QuAcqTaskPreparation

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle


class QuAcqModel:
    """Thin KB container for QuAcq interactive learning.

    Holds bias constraint_map, variables, negated_constraint_map, and
    next_available_id (ModelProtocol).

    Call prepare_task(oracle) to obtain a fresh QuAcqTask with attached
    VariableCodec (codec.pos/neg_assignment_to_assumption populated from
    BGData Part 4).

    The returned task is the sole carrier of codec, describe, and all
    SAT-layer state.  Runners and algorithms must hold the task directly;
    no facade methods delegate back through this model.
    """

    def __init__(self) -> None:
        # ModelProtocol fields
        self.constraint_map: Dict[str, List[List[int]]] = {}
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        self.variables: Dict[str, int] = {}
        self.next_available_id: int = 0

    # -------------------------------------------------------------------------
    # Sole public entry point: prepare_task
    # -------------------------------------------------------------------------

    def prepare_task(self, oracle: 'FeatureModelOracle') -> QuAcqTask:
        """Prepare a fresh QuAcqTask from bias + oracle.

        Builds VariableCodec with:
          - id_to_name: {var_id: feature_name}
          - pos_assignment_to_assumption: from BGData Part 4
          - neg_assignment_to_assumption: from BGData Part 4

        Attaches codec and describe to the returned task.

        Args:
            oracle: FeatureModelOracle for BG data and feature IDs

        Returns:
            Fresh QuAcqTask with task.codec and task.describe attached.
        """
        preparation = QuAcqTaskPreparation()
        output = preparation.prepare(self, oracle)

        assert isinstance(output.task, QuAcqTask)
        task = output.task

        # Build codec: id_to_name from variables; pos/neg maps from BGData Part 4
        bg_data = oracle.get_bg_data()
        codec = VariableCodec(
            id_to_name={vid: name for name, vid in self.variables.items()},
            pos_assignment_to_assumption=dict(bg_data.pos_assignment_to_assumption),
            neg_assignment_to_assumption=dict(bg_data.neg_assignment_to_assumption),
        )
        task.codec = codec
        task.describe = output.description_provider

        return task

    # -------------------------------------------------------------------------
    # KB resolution helpers (used by runners to map assumption IDs -> names)
    # -------------------------------------------------------------------------

    def resolve_kb(self, task: QuAcqTask,
                   kb_assumption_ids: List[int]) -> Tuple[List[str], List[List[int]]]:
        """Resolve assumption IDs to constraint names and raw clauses.

        Args:
            task: QuAcqTask whose describe provider maps IDs to names
            kb_assumption_ids: List of learned KB assumption IDs

        Returns:
            Tuple of (constraint_names, combined_raw_clauses)
        """
        provider = task.describe
        names = [provider.get_description(aid) for aid in kb_assumption_ids]
        clauses: List[List[int]] = []
        for aid in kb_assumption_ids:
            name = provider.get_description(aid)
            if name in self.constraint_map:
                clauses.extend(self.constraint_map[name])
        return names, clauses
