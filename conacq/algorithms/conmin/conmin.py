"""ConMin: passive maximally-general constraint acquisition.

`acquire` runs paper Algorithm 1 in full: the consistency gate + AcqMSS Stage-1
(the admissible pool A, maximally specific), then AcqMinCover + support⁺ + Reduce.

Reference: Paper Algorithm 1 (NE pre-computed by the caller)
    ConMin(E+, NE, B, BG) -> KB
    1: A <- Phi
    2: if IsConsistent(E+, NE, BG) then
    3:   A <- AdmPoolMSS(Phi, B, NE, E+, BG)      # == AcqMSS.find_mss (Stage 1)
    4: end if
    5: <C, U> <- AcqMinCover(A, E-, BG)           # min cover of the negatives
    6: S <- { c in A \\ Cflat : support+(c) >= k }  # positively-supported survivors
    7: KB <- Cflat u S u { not(e-) : e- in U }
    8: return Reduce(KB, BG)                       # lines 5-8 in _cover_support_reduce

Callers that want Stage-1 only (the maximally-specific A) simply omit
`neg_encodings`/`support_count`: the lines 5-8 tail then reduces to an empty KB while
`ConMinResult.mss_ids` still carries A. Mode-agnostic: all data is assumption-based
(List[int]); the checker implementation decides the solver lifecycle.

Paper ↔ code name map (the AAAI paper is self-contained; some routines are shared with
SoSyM/ConGen and keep their repo names — no renames):
    AdmPoolMSS (paper Stage 1) = `AcqMSS.find_mss`  — same routine as SoSyM's AcqMss,
        shared with ConGen (do NOT rename the shared class).
    AcqMinCover (paper line 5)  = `AcqMinCover.cover` (invoked from `_compute_cover`).
    support⁺ (paper line 6)     = `support_count` (precomputed) + the `>= k` filter in
        `finish_kb` (structural, 0 solver calls).
    Reduce / GenerateNE / Split = same-named repo routines (kept).
    `acquire_pool_and_cover` / `finish_kb` are an IMPLEMENTATION split of lines 1-5 /
        6-8 for k-sweep reuse — not paper routines.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Mapping, Optional, Sequence

from conacq.algorithms.acqmss import AcqMSS, Reduce
from explanation.api import ConsistencyChecker
from profiling import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)

from .acqmincover import AcqMinCover, CoverResult, NegEncoding


@dataclass
class ConMinResult:
    """Result of ConMin acquisition.

    Exposes the three passive-strategy eval slices as intermediate outputs of one
    run (design brief §9a). P1 fills only the Stage-1 slice (``mss_ids`` = A); the
    cover/support/fallback/uncoverable/kb slices default empty until P2-P3 assemble
    them. Fields are defaulted so partial construction (the P1 success path AND the
    inconsistent-gate early return) can never omit a required argument.
    """

    # P1-filled (no default): the Stage-1 slice and its sizes.
    mss_ids: List[int]            # A = Stage-1 admissible pool (maximally specific)
    n_bias: int
    n_mss: int
    # Stage-2..5 slices + counts (defaulted).
    cover_ids: List[int] = field(default_factory=list)          # C   (P2)
    support_ids: List[int] = field(default_factory=list)        # S   (P3)
    fallback_ids: List[int] = field(default_factory=list)       # not(e-) for e- in U (P3)
    uncoverable: List[int] = field(default_factory=list)        # U   (P2/P3)
    kb_assumption_ids: List[int] = field(default_factory=list)  # ConMin final post-Reduce (P3)
    redundant_ids: List[int] = field(default_factory=list)      # dropped by Reduce (P3)
    n_kb: int = 0
    n_components: int = 0
    largest_component: int = 0
    n_greedy_fallback: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass(frozen=True)
class _CoverState:
    """Cover-once state for a k-sweep (paper Algorithm 1 lines 1-5 done).

    ``acquire_pool_and_cover`` produces this once per (KB, example-set, fold,
    raw/reduced); ``finish_kb`` then runs lines 6-8 for each k over it. The admissible
    pool ``mss`` (=A) and the cover ``cover_ids`` (=C) are k-invariant, so the sweep
    only re-runs support⁺ + assemble + Reduce — bit-identical to a fresh ``acquire``.
    """

    mss: List[int]
    cover: CoverResult
    cover_ids: List[int]
    cover_set: frozenset
    n_bias: int
    n_neg_tv: int
    n_e_pos: int


class ConMin:
    """ConMin constraint acquisition algorithm (full Algorithm 1).

    Mode-agnostic: all data is assumption-based (List[int]). The checker
    implementation determines the solver lifecycle.
    """

    def __init__(self, checker: ConsistencyChecker,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.checker = checker
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        self.result: Optional[ConMinResult] = None

    @measure_time('conmin_runtime')
    @count_calls('conmin_calls')
    def acquire(
            self,
            set_b: Sequence[int],
            set_bg: Sequence[int],
            set_tc: Sequence[int],
            set_neg_tv: Optional[List[int]] = None,
            negation_map: Optional[Dict[int, int]] = None,
            neg_encodings: Sequence[NegEncoding] = (),
            support_count: Optional[Mapping[int, int]] = None,
            k: int = 1,
    ) -> ConMinResult:
        """Acquire the ConMin knowledge base (paper Algorithm 1, lines 1-8).

        Gate (line 2) + AcqMSS (line 3) give the admissible pool A; lines 5-8
        (AcqMinCover + support⁺ + Reduce) run in ``_cover_support_reduce``.

        Args:
            set_b: Bias constraint assumption IDs (B)
            set_bg: Background knowledge assumption IDs (BG)
            set_tc: Positive example assumption IDs (E+)
            set_neg_tv: Negated example assumption IDs (NE) — Stage-1 context
            negation_map: assumption ID -> negated ID, used by the Reduce step (line 8)
            neg_encodings: per-e- full-config assignment aids for AcqMinCover's
                rejection test (line 5). Omit ((), the default) for a Stage-1-only run.
            support_count: bias aid -> support⁺; drives S (line 6). Omitted -> S = ∅.
            k: support threshold for S (line 6).

        Returns:
            ConMinResult: ``mss_ids`` = A; ``kb_assumption_ids`` = the final KB
            (Cflat ∪ S ∪ fallbacks, post-Reduce). All empty when E+ is inconsistent
            with NE ∪ BG; the KB is empty (A only) when ``neg_encodings`` is omitted.
        """
        state = self.acquire_pool_and_cover(
            set_b, set_bg, set_tc, set_neg_tv, negation_map, neg_encodings)
        if state is None:  # gate tripped — self.result is the empty gate-trip result
            return self.result
        self.result = self.finish_kb(
            state, support_count, k, set_bg, negation_map,
            metadata={'n_neg_tv': state.n_neg_tv, 'n_e_pos': state.n_e_pos, 'k': k})
        return self.result

    def acquire_pool_and_cover(
            self,
            set_b: Sequence[int],
            set_bg: Sequence[int],
            set_tc: Sequence[int],
            set_neg_tv: Optional[Sequence[int]] = None,
            negation_map: Optional[Dict[int, int]] = None,
            neg_encodings: Sequence[NegEncoding] = (),
    ) -> Optional[_CoverState]:
        """Paper Algorithm 1 lines 1-5 (gate + AcqMSS + AcqMinCover), run ONCE.

        Returns a ``_CoverState`` for a k-sweep over ``finish_kb`` (lines 6-8), or
        ``None`` if the consistency gate trips (``self.result`` is then the empty
        gate-trip result). The cover (line 5) is k-invariant, so the eval computes it
        once per (fold, raw/reduced) and sweeps k over ``finish_kb`` only — reusing the
        pool + cover bit-identically to a fresh ``acquire`` at each k.
        """
        set_neg_tv = list(set_neg_tv or [])
        negation_map = negation_map or {}
        # Task solve-fields arrive as immutable tuples; work on lists.
        set_b, set_bg, set_tc = list(set_b), list(set_bg), list(set_tc)

        logging.debug('>>> ConMin [B=%d, NE=%d, E+=%d, BG=%d]',
                      len(set_b), len(set_neg_tv), len(set_tc), len(set_bg))

        # Line 2: consistency gate — E+ must be consistent with NE union BG.
        inconsistent = self.checker.is_consistent_test_cases(
            set_neg_tv + set_bg,  # NE union BG
            set_tc,               # E+
            stop_at_first_violation=True
        )
        self.profiler.increment("paper_consistency_checks")
        # §9c classified counter for the ConMin Stage-0 gate (line 2), at BATCH
        # granularity (+1 per IsConsistent call) to stay comparable with ConGen's
        # paper_consistency_checks (also +1/call). ConMin-only (ADR-0018).
        self.profiler.increment("conmin_admpool_gate_checks")

        if len(inconsistent) > 0:
            logging.debug('<<< ConMin return Phi (E+ inconsistent with NE union BG)')
            self.result = ConMinResult(
                mss_ids=[],
                n_bias=len(set_b),
                n_mss=0,
                metadata={'error': 'E+ inconsistent with NE ∪ BG'}
            )
            return None

        # Line 3: A <- AcqMSS(Phi, B, NE, E+, BG) — maximally specific, UNREDUCED.
        acqmss = AcqMSS(self.checker, m=1, profiler_instance=self.profiler)
        mss = acqmss.find_mss(
            delta=[], set_b=set_b, set_neg_tv=set_neg_tv,
            set_tc=set_tc, set_bg=set_bg)
        logging.debug('AcqMSS: MSS size = %d', len(mss))

        # Line 5: <C, U> <- AcqMinCover(A, E-, BG) — k-invariant, computed once.
        return self._compute_cover(
            mss, neg_encodings, set_bg,
            n_bias=len(set_b), n_neg_tv=len(set_neg_tv), n_e_pos=len(set_tc))

    @measure_time('conmin_acqmincover_runtime')
    def _compute_cover(
            self,
            mss: Sequence[int],
            neg_encodings: Sequence[NegEncoding],
            set_bg: Sequence[int],
            n_bias: int,
            n_neg_tv: int,
            n_e_pos: int,
    ) -> _CoverState:
        """Paper Algorithm 1 line 5: <C, U> <- AcqMinCover(A, E-, BG); flatten compounds
        to constraint IDs. Timed as its own phase (``conmin_acqmincover_runtime``) so the eval
        attributes cover cost separately from Stage-1 / Reduce (§9b)."""
        cover = AcqMinCover(self.checker, profiler_instance=self.profiler).cover(
            mss, neg_encodings, set_bg)
        cover_ids = sorted(set().union(*(set(e) for e in cover.cover_elements))
                           if cover.cover_elements else set())
        return _CoverState(
            mss=list(mss), cover=cover, cover_ids=cover_ids,
            cover_set=frozenset(cover_ids),
            n_bias=n_bias, n_neg_tv=n_neg_tv, n_e_pos=n_e_pos)

    def finish_kb(
            self,
            state: _CoverState,
            support_count: Optional[Mapping[int, int]],
            k: int,
            set_bg: Sequence[int],
            negation_map: Optional[Dict[int, int]] = None,
            metadata: Optional[Dict] = None,
    ) -> ConMinResult:
        """Paper Algorithm 1 lines 6-8 (support⁺ + assemble + Reduce) for one k, over a
        precomputed ``_CoverState``. The k-sweep entry: A (mss) and C (cover) are
        k-invariant; only S / assemble / Reduce depend on k. Reduce is re-run per k."""
        support_count = support_count or {}
        negation_map = negation_map or {}
        mss, cover = state.mss, state.cover
        # Copy cover_ids: each per-k ConMinResult gets its own list (siblings mss_ids /
        # uncoverable are copied too), so a consumer mutating one k's result can't
        # corrupt the shared cover the k-sweep relies on.
        cover_ids, cover_set = list(state.cover_ids), state.cover_set

        # Line 6: S <- { c ∈ A \ Cflat : support⁺(c) ≥ k }
        support_ids = [c for c in mss
                       if c not in cover_set and support_count.get(c, 0) >= k]

        # Line 7: KB <- Cflat ∪ S ∪ { ¬e⁻ : e⁻ ∈ U } ; assemble in F → S → C order.
        fallback_ids = list(cover.uncoverable)
        assembled = fallback_ids + support_ids + cover_ids

        # Line 8: Reduce(KB, BG). set_neg_tv=[] — coverable NEs are redundant (entailed
        # by the cover) so omitting them from the Reduce input is equivalent.
        redundant, kb = Reduce(self.checker, self.profiler).reduce(
            assembled, [], set_bg, negation_map)

        logging.debug('<<< ConMin KB=%d (mss=%d, cover=%d, S=%d, U=%d, k=%d)',
                      len(kb), len(mss), len(cover_ids), len(support_ids),
                      len(fallback_ids), k)
        return ConMinResult(
            mss_ids=list(mss),
            cover_ids=cover_ids,
            support_ids=support_ids,
            fallback_ids=fallback_ids,
            uncoverable=list(cover.uncoverable),
            kb_assumption_ids=kb,
            redundant_ids=redundant,
            n_bias=state.n_bias,
            n_mss=len(mss),
            n_kb=len(kb),
            n_components=cover.n_components,
            largest_component=cover.largest_component,
            n_greedy_fallback=cover.n_greedy_fallback,
            metadata=metadata or {},
        )

    def _cover_support_reduce(
            self,
            mss: Sequence[int],
            neg_encodings: Sequence[NegEncoding],
            support_count: Mapping[int, int],
            k: int,
            set_bg: Sequence[int],
            negation_map: Dict[int, int],
            n_bias: int,
            metadata: Optional[Dict] = None,
    ) -> ConMinResult:
        """Paper Algorithm 1 lines 5-8 over a given admissible pool ``mss`` (= A).

        Thin wrapper over ``_compute_cover`` + ``finish_kb`` (the k-sweep split), kept
        so callers driving the assembly directly (design-brief strategy B, hand-built
        cover/support + stub checker) keep working.
        """
        state = self._compute_cover(
            mss, neg_encodings, set_bg, n_bias=n_bias,
            n_neg_tv=metadata.get('n_neg_tv', 0) if metadata else 0,
            n_e_pos=metadata.get('n_e_pos', 0) if metadata else 0)
        return self.finish_kb(state, support_count, k, set_bg, negation_map, metadata)
