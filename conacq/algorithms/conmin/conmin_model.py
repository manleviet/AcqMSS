"""Model for ConMin (pure KB container; ``prepare_task`` derives a fresh task).

An immutable KB: bias ``constraint_map`` + name↔id catalog (inherited from KBModel).
``prepare_task`` delegates to ``ConMinTaskPreparation`` (pure, repeatable per fold).

``resolve_result`` (P4b) returns a 5-part DECOMPOSITION of a ``ConMinResult``,
DELIBERATELY DIVERGING from ``ConGenModel.resolve_result``'s 4-tuple: it adds a
``fallback_clauses`` slice (¬e⁻ memorized rejections, which ConGen has no analogue
for) and FM-filters the names. NOT drop-in substitutable for ConGen's resolver
(different arity + return shape); it lives in ``conmin/`` and ConGen's is untouched.
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

    def prepare_task(self, task_input: ConMinTaskInput,
                     minimize: bool = True, profiler=None) -> PreparedTask:
        """Assign assumption IDs and build a fresh ConMinTask (pure, repeatable).

        ``minimize`` selects the negative encoding (P4d raw/reduced sweep): True
        (default) = REDUCED (each ¬e⁻ = subset-minimal conflict via QuickXplain);
        False = RAW (negate the full assignment, no oracle QuickXplain). Assumption
        IDs are identical either way, so the Stage-1 golden is preserved. ``profiler``
        (optional) counts GenerateNE's preprocessing QuickXplain separately (GAP B)."""
        return ConMinTaskPreparation(
            minimize=minimize, profiler=profiler).prepare(self, task_input)

    def resolve_result(
            self,
            result: "ConMinResult",
            describe: DescriptionProvider,
            root_clauses: Sequence[Sequence[int]],
            set_kb: Sequence[Sequence[int]] = (),
            negation_map: Optional[Dict[int, int]] = None,
    ) -> Tuple[List[List[int]], List[List[int]], List[str], List[List[int]], List[str]]:
        """Resolve a ConMinResult into a 5-part DECOMPOSITION.

        The delivered theory = LEARNED FM ∪ {¬e⁻ fallbacks} ∪ {root}. Each part is
        returned SEPARATELY so downstream metrics choose what to use — the policy of
        which metric uses which part lives in the paper (brief §9), NOT here:

        - ``bg_clauses`` — the FM root non-emptiness axiom (given, not learned; the
          root P4a dropped from the acquisition BG and recorded on ``root_axiom``).
        - ``kb_clauses`` / ``kb_names`` — the LEARNED FM constraints (C∪S post-Reduce):
          the ``kb_assumption_ids`` whose name is a bias constraint. The view for
          semantic P/R/F1 (which runs over the bias-constraint vocabulary; ¬e⁻ and
          root are not in it, so they are out — not cherry-picking).
        - ``fallback_clauses`` — the memorized rejections of uncoverable negatives,
          resolved from the task ``set_kb`` (NOT ``constraint_map``). Each is the
          negation of the oracle-entailed MINIMAL CONFLICT (strictly ⊇ ¬(full e⁻
          assignment) — the correct, non-over-rejecting fallback). Needed for
          exact-equivalence (dropping them understates it when a negative is not
          rejectable by any bias constraint). Usually empty (ConMin expects U=∅).
        - ``redundant_names`` — the learned-FM constraints Reduce dropped. FM-FILTERED
          by design: a ¬e⁻ Reduce dropped (rare — it was entailed, so exact-equivalence
          is unaffected) is NOT reported here; only its accounting is lost (see §9c).

        Every NON-FM kb id IS a ¬e⁻ fallback and MUST resolve to a clause; if one
        cannot (empty/mismatched ``set_kb`` or missing ``negation_map`` entry) this
        RAISES rather than silently dropping it — a fallback lost from the delivered
        theory would understate exact-equivalence with no signal (foot-gun #5). The
        defaults ``set_kb=()`` / ``negation_map=None`` are safe ONLY for U=∅ callers
        (no non-FM ids ⇒ no resolution attempted ⇒ no raise).

        ``set_kb`` + ``negation_map`` come from the prepared ConMinTask (stateless —
        passed in, never stored). Returns:
            (bg_clauses, kb_clauses, kb_names, fallback_clauses, redundant_names)
        """
        negation_map = negation_map or {}
        bg_clauses = root_clauses
        kb_clauses, kb_names = self._resolve_fm(describe, result.kb_assumption_ids)

        # ¬e⁻ fallbacks = the kb ids that are NOT bias constraints (memorized
        # negatives). support/cover ids are bias constraints, so a non-FM kb id is
        # ALWAYS a fallback and must resolve — else it vanishes from the theory.
        fallback_clauses: List[List[int]] = []
        for aid in result.kb_assumption_ids:
            if describe.get_description(aid) not in self.constraint_map:
                clause = self._resolve_fallback_clause(aid, set_kb, negation_map)
                if not clause:  # None (no match) or [] (degenerate empty ⇒ UNSAT)
                    raise ValueError(
                        f"ConMin kb id {aid} is a ¬e⁻ fallback (name not a bias "
                        f"constraint) but its clause could not be resolved: "
                        f"set_kb has {len(set_kb)} clauses, negation_map "
                        f"{'has' if aid in negation_map else 'MISSING'} id {aid}. "
                        f"Pass the prepared task's set_kb + negation_map; a fallback "
                        f"must not be silently dropped from the delivered theory.")
                fallback_clauses.append(clause)

        _, redundant_names = self._resolve_fm(describe, result.redundant_ids)
        return bg_clauses, kb_clauses, kb_names, fallback_clauses, redundant_names

    def resolve_slice(
            self,
            describe: DescriptionProvider,
            assumption_ids: Sequence[int],
    ) -> Tuple[List[List[int]], List[str]]:
        """Resolve a passive-strategy slice (A=``mss_ids`` / C=``cover_ids`` / C∪S) to
        its LEARNED-FM (clauses, names) — the same bias-constraint filter as
        ``kb_names``, so P/R/F1 for every slice ranges over the same FM/bias vocabulary
        (¬e⁻/root excluded). Public entry for the P4d eval (§9a: three slices of one
        run, resolved + compared separately)."""
        return self._resolve_fm(describe, assumption_ids)

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
        """The fallback clause for a NE id, from the task KB. Its blocking clause is
        ``[-l1,…,-lk, -ne_id]`` (the l_i are the minimal-conflict feature literals);
        distinguish it from the NE's negation clause ``[-ne_id, -negation_map[ne_id]]``
        by the ABSENCE of ``-negation_map[ne_id]`` (the combine clause ``[+ne_id, …]``
        never matches ``-ne_id``), then strip the ``-ne_id`` guard — returns the
        negation of the minimal conflict.

        Returns None (⇒ the caller fails loud) when no clause matches OR when ``ne_id``
        has no ``negation_map`` entry: without it the ne-clause cannot be safely told
        apart from the negation clause, so guessing the first ``-ne_id`` clause (which
        could return a wrong remainder — the P3-Critical bug class) is REFUSED, not
        silently attempted.

        NOTE on the FM/fallback split at the call site: multi-negative per-e⁻ ids are
        left UNREGISTERED in ``describe`` (only the combined id is), so their
        ``get_description`` returns ``str(id)`` — never a bias name (which are
        ``c``-prefixed), so they classify as fallbacks correctly."""
        neg = negation_map.get(ne_id)
        if neg is None:
            return None  # cannot safely disambiguate ne-clause vs negation clause
        for clause in set_kb:
            if -ne_id in clause and -neg not in clause:
                return [lit for lit in clause if lit != -ne_id]
        return None
