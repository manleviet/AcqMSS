"""
FM oracle KB model.

FMOracleModel is an immutable FM knowledge base: it holds the constraint maps, the
name↔id catalog (inherited from KBModel), and the next free assumption ID, and
derives a fresh PreparedTask per call via ``prepare_task`` (pure — no task state
stored on the model). Solver mode (``use_incremental``) is an operation/checker
concern owned by the caller, not the model. Loading an FM file is the builder's job
(FMOracleModelBuilder) — the model does not build itself.
"""

from typing import Optional

from conacq.kb_model import KBModel
from conacq.oracle.fm.task_preparation import FMOracleTaskPreparation
from explanation.api import PreparedTask, TaskInput


class FMOracleModel(KBModel):
    """Immutable FM knowledge base for oracle validation via ConsistencyChecker.

    Holds only KB data (constraint_map + negated_constraint_map + the name↔id catalog
    + next_available_id, all from KBModel). Per-task preparation is pure:
    ``prepare_task`` returns a fresh PreparedTask and stores nothing on the model. FM
    clauses go into set_kb (always active); feature assignments become
    assumption-guarded unit clauses:
      [-a_pos_i, fid]  → if a_pos_i active, feature must be true
      [-a_neg_i, -fid] → if a_neg_i active, feature must be false
    """

    def prepare_task(self, task_input: Optional[TaskInput] = None) -> PreparedTask:
        """Derive a fresh PreparedTask from this FM KB (pure).

        ``task_input`` is accepted for signature uniformity with the other models
        but unused: the oracle's task is fully determined by the FM constraints and
        variables. Each call builds a new task; the model is never mutated.
        """
        return FMOracleTaskPreparation.prepare_task(self)
