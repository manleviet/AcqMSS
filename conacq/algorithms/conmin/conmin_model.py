"""Model for ConMin (pure KB container; ``prepare_task`` derives a fresh task).

An immutable KB: bias ``constraint_map`` + name↔id catalog (inherited from KBModel).
``prepare_task`` delegates to ``ConMinTaskPreparation`` (pure, repeatable per fold).

``resolve_result`` (P4b) mirrors ``ConGenModel.resolve_result``'s 4-tuple, mapping
from ``ConMinResult`` (``kb_assumption_ids`` + ``redundant_ids``, added in P3). It is
a mirror in ``conmin/`` — ConGen's resolver is not touched or shared.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

from conacq.kb_model import KBModel
from explanation.api import DescriptionProvider, PreparedTask

from .task_preparation import ConMinTaskInput, ConMinTaskPreparation

if TYPE_CHECKING:
    from .conmin import ConMinResult


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

    def resolve_result(
            self,
            result: "ConMinResult",
            describe: DescriptionProvider,
            root_clauses: Sequence[Sequence[int]],
            set_kb: Sequence[Sequence[int]] = (),
            negation_map: Optional[Dict[int, int]] = None,
    ) -> Tuple[List[List[int]], List[List[int]], List[str], List[List[int]], List[str]]:
        """Resolve a ConMinResult into a clean 5-part DECOMPOSITION (drops nothing).

        The delivered theory = LEARNED FM ∪ {¬e⁻ fallbacks} ∪ {root}. Each part is
        returned SEPARATELY so downstream metrics choose what to use — the policy of
        which metric uses which part lives in the paper (brief §9), NOT here:

        - ``bg_clauses`` — the FM root non-emptiness axiom (given, not learned; the
          root P4a dropped from the acquisition BG and recorded on ``root_axiom``).
        - ``kb_clauses`` / ``kb_names`` — the LEARNED FM constraints (C∪S post-Reduce):
          the ``kb_assumption_ids`` whose name is a bias constraint. The view for
          semantic P/R/F1 (which runs over the bias-constraint vocabulary; ¬e⁻ and
          root are not in it, so they are out — not cherry-picking).
        - ``fallback_clauses`` — the ¬e⁻ memorized rejections of uncoverable negatives,
          resolved from the task ``set_kb`` (NOT ``constraint_map``). Needed for
          exact-equivalence (dropping them understates it when a negative is not
          rejectable by any bias constraint). Usually empty (ConMin expects U=∅).
        - ``redundant_names`` — the learned-FM constraints Reduce dropped.

        ``set_kb`` + ``negation_map`` come from the prepared ConMinTask (stateless —
        passed in, never stored). Returns:
            (bg_clauses, kb_clauses, kb_names, fallback_clauses, redundant_names)
        """
        negation_map = negation_map or {}
        bg_clauses = root_clauses
        kb_clauses, kb_names = self._resolve_fm(describe, result.kb_assumption_ids)

        # ¬e⁻ fallbacks = the kb ids that are NOT bias constraints (memorized
        # negatives); resolve each one's clause from the task KB.
        fallback_clauses: List[List[int]] = []
        for aid in result.kb_assumption_ids:
            if describe.get_description(aid) not in self.constraint_map:
                clause = self._resolve_fallback_clause(aid, set_kb, negation_map)
                if clause is not None:
                    fallback_clauses.append(clause)

        _, redundant_names = self._resolve_fm(describe, result.redundant_ids)
        return bg_clauses, kb_clauses, kb_names, fallback_clauses, redundant_names

    def _resolve_fm(
            self,
            describe: DescriptionProvider,
            assumption_ids: Sequence[int],
    ) -> Tuple[List[List[int]], List[str]]:
        """Resolve ONLY the bias-constraint (learned FM) ids to (clauses, names). Ids
        whose name is not a bias constraint (¬e⁻ fallbacks) are skipped, so kb_names
        and kb_clauses stay consistent (no name-in / clause-out)."""
        clauses: List[List[int]] = []
        names: List[str] = []
        for aid in assumption_ids:
            name = describe.get_description(aid)
            if name in self.constraint_map:
                names.append(name)
                clauses.extend(self.constraint_map[name])
        return clauses, names

    @staticmethod
    def _resolve_fallback_clause(
            ne_id: int,
            set_kb: Sequence[Sequence[int]],
            negation_map: Dict[int, int],
    ) -> Optional[List[int]]:
        """The ¬e⁻ clause for a fallback NE id, from the task KB. Its blocking clause
        is ``[-l1,…,-lk, -ne_id]``; distinguish it from the NE's negation clause
        ``[-ne_id, -negation_map[ne_id]]`` by the ABSENCE of ``-negation_map[ne_id]``,
        then strip the ``-ne_id`` guard to recover the feature-level ¬e⁻."""
        neg = negation_map.get(ne_id)
        for clause in set_kb:
            if -ne_id in clause and (neg is None or -neg not in clause):
                return [lit for lit in clause if lit != -ne_id]
        return None
