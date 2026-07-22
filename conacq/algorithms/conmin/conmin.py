"""ConMin: passive maximally-general constraint acquisition.

P1 runs paper Algorithm 1 lines 1-4 only: the consistency gate plus AcqMSS Stage-1,
returning the admissible pool A (maximally specific, UNREDUCED). The cover +
support + Reduce steps (lines 5-8) land in P2-P3.

Reference: Paper Algorithm 1 (Stage 1, NE pre-computed by the caller)
    ConMin(E+, NE, B, BG) -> A          # P1 = lines 1-4 (this file)
    1: A <- Phi
    2: if IsConsistent(E+, NE, BG) then
    3:   A <- AdmPoolMSS(Phi, B, NE, E+, BG)   # == AcqMSS.find_mss
    4: end if
    ...   (lines 5-8: AcqMinCover + support + Reduce -> P2/P3)

Mode-agnostic: all data is assumption-based (List[int]); the checker implementation
decides the solver lifecycle.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Mapping, Optional, Sequence

from conacq.algorithms.acqmss import AcqMSS, Reduce
from explanation.api import ConsistencyChecker
from profiling import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)

from .acqmincover import AcqMinCover, NegEncoding


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


class ConMin:
    """ConMin constraint acquisition algorithm (P1: Stage-1 only).

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
        """Acquire the maximally-specific admissible pool A (Stage 1).

        Paper Algorithm 1 lines 1-4:
        2. if IsConsistent(E+, NE, BG) then A <- AcqMSS(Phi, B, NE, E+, BG)

        Args:
            set_b: Bias constraint assumption IDs (B)
            set_bg: Background knowledge assumption IDs (BG)
            set_tc: Positive example assumption IDs (E+)
            set_neg_tv: Negated example assumption IDs (NE)
            negation_map: Reserved for the P3 Reduce step; unused in P1 (kept for
                signature symmetry with ConGen and forward-compat)

        Returns:
            ConMinResult with ``mss_ids`` = A (unreduced). Empty when E+ is
            inconsistent with NE union BG.
        """
        set_neg_tv = set_neg_tv or []
        negation_map = negation_map or {}
        support_count = support_count or {}
        # Task solve-fields arrive as immutable tuples; work on lists.
        set_b, set_bg, set_tc, set_neg_tv = (
            list(set_b), list(set_bg), list(set_tc), list(set_neg_tv))

        logging.debug('>>> ConMin [B=%d, NE=%d, E+=%d, BG=%d]',
                      len(set_b), len(set_neg_tv), len(set_tc), len(set_bg))

        # Line 2: consistency gate — E+ must be consistent with NE union BG.
        inconsistent = self.checker.is_consistent_test_cases(
            set_neg_tv + set_bg,  # NE union BG
            set_tc,               # E+
            stop_at_first_violation=True
        )
        self.profiler.increment("paper_consistency_checks")

        if len(inconsistent) > 0:
            logging.debug('<<< ConMin return Phi (E+ inconsistent with NE union BG)')
            self.result = ConMinResult(
                mss_ids=[],
                n_bias=len(set_b),
                n_mss=0,
                metadata={'error': 'E+ inconsistent with NE ∪ BG'}
            )
            return self.result

        # Line 3: A <- AcqMSS(Phi, B, NE, E+, BG) — maximally specific, UNREDUCED.
        acqmss = AcqMSS(self.checker, m=1, profiler_instance=self.profiler)
        mss = acqmss.find_mss(
            delta=[],
            set_b=set_b,
            set_neg_tv=set_neg_tv,
            set_tc=set_tc,
            set_bg=set_bg
        )
        logging.debug('AcqMSS: MSS size = %d', len(mss))

        # Lines 5-8: cover → support → fallbacks → assemble → Reduce.
        self.result = self._cover_support_reduce(
            mss, neg_encodings, support_count, k, set_bg, negation_map,
            n_bias=len(set_b),
            metadata={'n_neg_tv': len(set_neg_tv), 'n_e_pos': len(set_tc), 'k': k})
        return self.result

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

        Factored out so the assembly + Reduce can be driven directly (design-brief
        strategy B) with a hand-built cover/support and a stub checker.
        """
        # Line 5: <C, U> <- AcqMinCover(A, E-, BG) ; flatten compounds to constraints.
        cover = AcqMinCover(self.checker, profiler_instance=self.profiler).cover(
            mss, neg_encodings, set_bg)
        cover_ids = sorted(set().union(*(set(e) for e in cover.cover_elements))
                           if cover.cover_elements else set())
        cover_set = set(cover_ids)

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

        logging.debug('<<< ConMin KB=%d (mss=%d, cover=%d, S=%d, U=%d)',
                      len(kb), len(mss), len(cover_ids), len(support_ids),
                      len(fallback_ids))
        return ConMinResult(
            mss_ids=list(mss),
            cover_ids=cover_ids,
            support_ids=support_ids,
            fallback_ids=fallback_ids,
            uncoverable=list(cover.uncoverable),
            kb_assumption_ids=kb,
            redundant_ids=redundant,
            n_bias=n_bias,
            n_mss=len(mss),
            n_kb=len(kb),
            n_components=cover.n_components,
            largest_component=cover.largest_component,
            n_greedy_fallback=cover.n_greedy_fallback,
            metadata=metadata or {},
        )
