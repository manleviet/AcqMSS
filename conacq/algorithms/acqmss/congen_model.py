"""
Model for ConGen algorithm.

An immutable KB: bias constraint_map + name↔id catalog (inherited from KBModel).
``prepare_task`` derives a fresh PreparedTask per call (pure); the model stores no
task state, no description provider, no root constraint, and no solver-mode field
(that is a caller/checker concern). ``resolve_result`` is STATELESS — the describe
provider (from the PreparedTask) and the root clauses (from the OracleData snapshot)
are passed in per call, never read off stored task state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

from conacq.kb_model import KBModel
from explanation.api import DescriptionProvider, PreparedTask

from .task_preparation import ConGenTaskInput, ConGenTaskPreparation

if TYPE_CHECKING:
    from .congen import ConGenResult


class ConGenModel(KBModel):
    """Immutable ConGen KB (bias constraints + name↔id catalog).

    Pure data container. prepare_task builds a fresh ConGenTask (via
    ConGenTaskPreparation); the model holds no task, no description provider, no
    root constraint, no solver mode.

    Usage:
        oracle = FMOracle('data/fms/model.uvl')
        model = (ConGenModelBuilder
                 .from_bias('data/bias/model.json')
                 .with_oracle_data(oracle.oracle_data)
                 .build())
        task_input = ConGenTaskInput.from_examples(oracle.oracle_data, pos, neg)
        prepared = model.prepare_task(task_input)
        task = prepared.task  # ConGenTask with assumption IDs
    """

    def prepare_task(self, task_input: ConGenTaskInput) -> PreparedTask:
        """Assign assumption IDs and build a fresh ConGenTask (pure).

        Consumes a ConGenTaskInput carrying the oracle's frozen provisioning
        snapshot plus this fold's E+/E-; returns a new PreparedTask (task +
        describe). Can be called repeatedly (e.g. per CV fold) — no state is kept.
        The signature is unified with the other models; the input TYPE is ConGen's
        own (not a shared union — ADR-0006).
        """
        return ConGenTaskPreparation().prepare(self, task_input)

    def resolve_result(
            self,
            result: "ConGenResult",
            describe: DescriptionProvider,
            root_clauses: List[List[int]],
    ) -> Tuple[List[List[int]], List[List[int]], List[str], List[str]]:
        """Resolve a ConGenResult into clauses and names (stateless).

        The describe provider (from the PreparedTask) and the root BG clauses (from
        the OracleData snapshot) are passed in — the model keeps no baton between
        prepare and resolve, so a wrong call order cannot silently drop the BG (a
        stored root-clause baton with an ``or []`` fallback masked exactly that).

        Returns:
            (bg_clauses, kb_clauses, kb_names, redundant_names)
        """
        bg_clauses = root_clauses
        kb_clauses, kb_names = self._resolve_ids(describe, result.kb_assumption_ids)
        _, redundant_names = self._resolve_ids(describe, result.redundant_ids)
        return bg_clauses, kb_clauses, kb_names, redundant_names

    def _resolve_ids(
            self,
            describe: DescriptionProvider,
            assumption_ids: List[int],
    ) -> Tuple[List[List[int]], List[str]]:
        """Resolve assumption IDs to clauses (from this KB's constraint_map) and
        names (from the given describe provider). Stateless."""
        clauses: List[List[int]] = []
        names: List[str] = []
        for aid in assumption_ids:
            name = describe.get_description(aid)
            names.append(name)
            if name in self.constraint_map:
                clauses.extend(self.constraint_map[name])
        return clauses, names
