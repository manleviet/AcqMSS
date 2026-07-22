"""AcqMinCover — divide-and-conquer minimum cover of the negatives (design brief §3,
AcqMinCover v2 note).

Phase A (here, checker-driven) builds the coverage map: for each negative ``e⁻`` the
constraints that reject it (``cand``), or — when no single constraint rejects a
*partial* negative — a compound QuickXplain conflict; a negative no element rejects
is uncoverable and goes to ``U``. Phases B–D (pure, in ``min_cover``) divide the map
into connected components, solve each exactly (or greedily above ``tau``), and drop
redundant elements.

This is the P2 engine in isolation: it takes ``neg_encodings`` as input and is
unit-tested with a stub checker. Wiring it into ``ConMin.acquire`` and feeding real
``neg_encodings`` from the task preparation is P3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, List, Optional, Sequence, Set, Tuple

from explanation.api import QuickXPlain
from profiling import get_global_profiler, AbstractProfiler

from .min_cover import connected_components, exact_cover, greedy_cover, irredundant

# Default exact-vs-greedy compute knob (design brief §8 decision 3; "20 was rejected
# as needlessly generous"). Measured on the number of cover elements in a component.
DEFAULT_TAU = 15


@dataclass(frozen=True)
class NegEncoding:
    """A negative example, encoded for the rejection test.

    ``assumption_ids`` are ``e⁻``'s assignment-assumption IDs to activate alongside a
    candidate constraint and the BG root. The task preparation produces these in P3
    (design brief §2); P2 hand-builds them.
    """

    neg_id: int
    assumption_ids: Tuple[int, ...]


@dataclass
class CoverResult:
    """Output of AcqMinCover: the cover elements plus the uncoverable negatives.

    ``cover_elements`` are cover elements (each a frozenset of constraint IDs); flatten
    via ``⋃`` at ConMin line 5 (P3). ``uncoverable`` are the ``neg_id``s that need a
    ``¬e⁻`` fallback clause. The three counters are the paper's cover-specific eval
    metrics (surfaced by the P4 runner).
    """

    cover_elements: List[FrozenSet[int]]
    uncoverable: List[int]
    n_components: int
    largest_component: int
    n_greedy_fallback: int


class AcqMinCover:
    """Divide-and-conquer minimum cover engine (mirrors the ``AcqMSS`` class shape)."""

    def __init__(
            self,
            checker,
            tau: int = DEFAULT_TAU,
            unit_weight: Optional[Callable[[int], float]] = None,
            profiler_instance: AbstractProfiler = None,
    ) -> None:
        self.checker = checker
        self.tau = tau
        self.unit_weight = unit_weight
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()

    def cover(
            self,
            admissible: Sequence[int],
            neg_encodings: Sequence[NegEncoding],
            bg: Sequence[int],
    ) -> CoverResult:
        """Cover the negatives with a minimum, generality-weighted set of elements.

        Args:
            admissible: admissible-pool constraint assumption IDs (``A``)
            neg_encodings: one ``NegEncoding`` per negative example
            bg: background-knowledge assumption IDs (the BG root)

        Returns:
            CoverResult with the cover elements and the uncoverable negatives.
        """
        admissible = list(admissible)
        bg = list(bg)

        cover: Dict[FrozenSet[int], Set[int]] = {}
        uncoverable: List[int] = []

        # --- Phase A: build the coverage map (checker-driven) ---
        for ne in neg_encodings:
            aids = list(ne.assumption_ids)
            cand: List[int] = []
            for c in admissible:
                self.profiler.increment("cover_rejection_checks")
                if not self.checker.is_consistent([c] + bg + aids):
                    cand.append(c)
            if cand:
                for c in cand:
                    cover.setdefault(frozenset([c]), set()).add(ne.neg_id)
            else:
                # No single constraint rejects e⁻ (partial negatives only, v2 §5).
                self.profiler.increment("cover_quickxplain_checks")
                conflict = QuickXPlain(self.checker, self.profiler).find_conflict(
                    admissible, bg + aids)
                if conflict:
                    cover.setdefault(frozenset(conflict), set()).add(ne.neg_id)
                else:
                    uncoverable.append(ne.neg_id)

        # --- Phase B: divide into connected components ---
        components = connected_components(cover)

        # --- Phase C: conquer (exact per small component, greedy above tau) ---
        selected: Set[FrozenSet[int]] = set()
        n_greedy = 0
        for elements_i, negs_i in components:
            if len(elements_i) <= self.tau:
                selected |= exact_cover(elements_i, negs_i, cover, self.unit_weight)
            else:
                selected |= greedy_cover(elements_i, negs_i, cover, self.unit_weight)
                n_greedy += 1

        # --- Phase D: irredundancy post-pass over all coverable negatives ---
        all_negs: Set[int] = set()
        for negs in cover.values():
            all_negs |= negs
        selected = irredundant(selected, all_negs, cover)

        return CoverResult(
            cover_elements=list(selected),
            uncoverable=uncoverable,
            n_components=len(components),
            largest_component=max((len(elems) for elems, _ in components), default=0),
            n_greedy_fallback=n_greedy,
        )
