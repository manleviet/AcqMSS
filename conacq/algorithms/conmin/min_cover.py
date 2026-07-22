"""Pure combinatorial minimum-cover solver for AcqMinCover (design brief §3, v2 note).

No solver, no checker, no ``explanation``/``profiling`` import — plain set operations
over a coverage map, so it is unit-testable with hand-built inputs and stays on the
right side of the boundary guard.

Vocabulary:
- **element**: a cover element = ``frozenset`` of constraint assumption IDs. A
  singleton ``{c}`` is the normal case; a compound ``{c1, c2, …}`` comes from the
  QuickXplain branch (a partial negative that no single constraint rejects).
- **negative**: any hashable id of an ``e⁻`` the element rejects.
- **cover**: ``Dict[element, Set[negative]]`` — which negatives each element rejects.

The divide-and-conquer claim (v2 note §2): minimum cover is *separable across the
connected components* of the coverage graph, so we split, solve each component
exactly (or greedily above ``tau``), and union. All results are deterministic (ties
broken by a stable sort key) so runs are reproducible.
"""

from __future__ import annotations

import itertools
from typing import Callable, Dict, FrozenSet, List, Optional, Set, Tuple

Element = FrozenSet[int]


def _key(element: Element) -> Tuple[int, ...]:
    """Stable sort key for a cover element (a frozenset has no intrinsic order)."""
    return tuple(sorted(element))


def weight(element: Element, unit_weight: Optional[Callable[[int], float]] = None) -> float:
    """Generality weight of a cover element.

    ``unit_weight is None`` ⇒ ``w ≡ 1`` per constraint, i.e. ``len(element)`` (plain
    minimum cardinality; a compound element weighs its size, so it is dispreferred).
    Otherwise ``Σ unit_weight(c)`` over the element's constraints (e.g. arity in P4).
    """
    if unit_weight is None:
        return len(element)
    return sum(unit_weight(c) for c in element)


def connected_components(
        cover: Dict[Element, Set[int]],
) -> List[Tuple[Set[Element], Set[int]]]:
    """Partition elements into connected components of the coverage graph.

    Two elements are linked iff they reject a shared negative (``cover[x] ∩ cover[y]
    ≠ ∅``); union-find closes this transitively. Returns ``[(elements_i, negs_i)]``
    with ``negs_i = ⋃ cover[x]``, in a deterministic order.
    """
    elements = sorted(cover.keys(), key=_key)
    parent: Dict[Element, Element] = {e: e for e in elements}

    def find(x: Element) -> Element:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: Element, b: Element) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    # Link every pair of elements that share a negative.
    neg_to_elems: Dict[int, List[Element]] = {}
    for e in elements:
        for n in cover[e]:
            neg_to_elems.setdefault(n, []).append(e)
    for elems in neg_to_elems.values():
        first = elems[0]
        for other in elems[1:]:
            union(first, other)

    groups: Dict[Element, List[Element]] = {}
    for e in elements:
        groups.setdefault(find(e), []).append(e)

    components: List[Tuple[Set[Element], Set[int]]] = []
    for elems in groups.values():
        negs: Set[int] = set()
        for e in elems:
            negs |= cover[e]
        components.append((set(elems), negs))
    components.sort(key=lambda comp: min(_key(e) for e in comp[0]))
    return components


def exact_cover(
        elements: Set[Element],
        negs: Set[int],
        cover: Dict[Element, Set[int]],
        unit_weight: Optional[Callable[[int], float]] = None,
) -> Set[Element]:
    """Minimum-cardinality-first exact weighted cover of ``negs`` using ``elements``.

    Tries covers of size 1, then 2, …; at the first size that admits a cover, returns
    the minimum-``Σweight`` combination (ties broken by the stable element order, so
    the result is deterministic). Intended for small components (``|elements| ≤ tau``).
    """
    negs = set(negs)
    if not negs:
        return set()
    ordered = sorted(elements, key=_key)
    for k in range(1, len(ordered) + 1):
        best: Optional[Tuple[Element, ...]] = None
        best_w: Optional[float] = None
        for combo in itertools.combinations(ordered, k):
            covered: Set[int] = set()
            for e in combo:
                covered |= cover[e]
            if negs <= covered:
                w = sum(weight(e, unit_weight) for e in combo)
                if best is None or w < best_w:
                    best, best_w = combo, w
        if best is not None:
            return set(best)
    return set()  # unreachable when every negative in ``negs`` has a coverer


def greedy_cover(
        elements: Set[Element],
        negs: Set[int],
        cover: Dict[Element, Set[int]],
        unit_weight: Optional[Callable[[int], float]] = None,
) -> Set[Element]:
    """H(d)=1+ln d greedy weighted cover — the fallback for components above ``tau``.

    Repeatedly take the element rejecting the most still-uncovered negatives; ties
    broken by lower weight, then by the stable element order.
    """
    remaining = set(negs)
    ordered = sorted(elements, key=_key)
    selected: Set[Element] = set()
    while remaining:
        best: Optional[Element] = None
        best_gain = 0
        best_w: Optional[float] = None
        for e in ordered:
            if e in selected:
                continue
            gain = len(cover[e] & remaining)
            if gain == 0:
                continue
            w = weight(e, unit_weight)
            if best is None or gain > best_gain or (gain == best_gain and w < best_w):
                best, best_gain, best_w = e, gain, w
        if best is None:
            break  # remaining negatives are uncoverable by the given elements
        selected.add(best)
        remaining -= cover[best]
    return selected


def irredundant(
        selected: Set[Element],
        negs: Set[int],
        cover: Dict[Element, Set[int]],
) -> Set[Element]:
    """Drop any element whose removal still leaves every negative covered.

    Set-based, no solver. Iterates in the stable element order for determinism;
    guarantees a subset-minimal cover even after the greedy fallback fires.
    """
    negs = set(negs)
    keep = set(selected)
    for e in sorted(selected, key=_key):
        if e not in keep:
            continue
        others = keep - {e}
        covered: Set[int] = set()
        for x in others:
            covered |= cover[x]
        if negs <= covered:
            keep = others
    return keep
