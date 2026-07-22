"""Model for ConMin (pure KB container; ``prepare_task`` derives a fresh task).

An immutable KB: bias ``constraint_map`` + name↔id catalog (inherited from KBModel).
``prepare_task`` delegates to ``ConMinTaskPreparation`` (pure, repeatable per fold).

``resolve_result`` is DEFERRED to P3/P4 — additive, no rework: ``KBModel`` is
concrete and ``BaseRunner`` declares no resolve, so a ``ConMinModel`` carrying only
``prepare_task`` is valid. When added it mirrors ``ConGenModel.resolve_result``'s
4-tuple (ConMin Reduces, like ConGen) but maps ``ConMinResult``'s slices — ConMin's
result has no ``redundant_ids`` field, so ConGen's resolver cannot be copied verbatim.
"""

from __future__ import annotations

from conacq.kb_model import KBModel
from explanation.api import PreparedTask

from .task_preparation import ConMinTaskInput, ConMinTaskPreparation


class ConMinModel(KBModel):
    """Immutable ConMin KB (bias constraints + name↔id catalog).

    Pure data container. ``prepare_task`` builds a fresh ``ConMinTask`` via
    ``ConMinTaskPreparation`` (delegating to ConGen's Stage-1 prep); the model holds
    no task, no describe provider, no solver mode.

    Usage:
        oracle = FMOracle('data/fms/model.uvl')
        model = (ConMinModelBuilder
                 .from_bias('data/bias/model.json')
                 .with_oracle_data(oracle.oracle_data)
                 .build())
        task_input = ConMinTaskInput.from_examples(oracle.oracle_data, pos, neg)
        prepared = model.prepare_task(task_input)
        task = prepared.task  # ConMinTask with assumption IDs
    """

    def prepare_task(self, task_input: ConMinTaskInput) -> PreparedTask:
        """Assign assumption IDs and build a fresh ConMinTask (pure, repeatable)."""
        return ConMinTaskPreparation().prepare(self, task_input)
