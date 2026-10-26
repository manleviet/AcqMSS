"""SAT machinery for the dead-feature analysis (glucose4, one incremental solver per theory).

Constraints are selector-guarded: constraint c contributes (clause ∨ ¬s_c) for each of its
clauses, and is active iff s_c is assumed. Every consistency check is one ``solve`` under
assumptions (active selectors + literals), counted in ``calls``.

- ``dead_features``: f is dead in Θ iff Θ ∧ f is UNSAT. Aggregation: every model found marks
  all features it selects as attainable, so only still-unmarked features cost a SAT call.
- ``core_features``: f is core iff Θ ∧ ¬f is UNSAT (aggregated the same way on deselection).
- ``quickxplain``: one minimal conflict set (Junker 2004) among candidate constraints.
- ``hs_diagnosis``: minimum-cardinality diagnosis by breadth-first HS-tree (Reiter 1987) over
  QuickXPlain conflicts of the positive test cases, children in preference order, nodes that
  accept a required negative pruned (removing constraints only accepts more examples).
"""
from __future__ import annotations

from collections import deque
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from pysat.solvers import Solver

ROOT_LIT = 1


class SelectorTheory:
    def __init__(self, n_vars: int, constraints: Dict[str, Sequence[Sequence[int]]],
                 base: Iterable[Sequence[int]] = ()):
        self.n_vars, self.sel, self.calls = n_vars, {}, 0
        self.solver = Solver(name='glucose4')
        for cl in base:
            self.solver.add_clause(list(cl))
        nxt = n_vars + 1
        for name, clauses in constraints.items():
            self.sel[name] = nxt
            for cl in clauses:
                self.solver.add_clause(list(cl) + [-nxt])
            nxt += 1

    def sat(self, names: Iterable[str], lits: Iterable[int] = ()) -> bool:
        self.calls += 1
        return self.solver.solve(assumptions=[self.sel[n] for n in names] + list(lits))

    def selected(self) -> Tuple[set, set]:
        """(selected, deselected) features of the last model."""
        model = self.solver.get_model()
        feats = [l for l in model if abs(l) <= self.n_vars]
        return {l for l in feats if l > 0}, {-l for l in feats if l < 0}

    def close(self):
        self.solver.delete()


def dead_features(th: SelectorTheory, names: Sequence[str]) -> Tuple[List[int], int]:
    """Dead features of names ∪ root, aggregated; returns (dead, SAT calls used)."""
    start, attainable, dead = th.calls, set(), []
    for f in range(1, th.n_vars + 1):
        if f in attainable:
            continue
        if th.sat(names, [ROOT_LIT, f]):
            attainable |= th.selected()[0]
        else:
            dead.append(f)
    return dead, th.calls - start


def core_features(th: SelectorTheory, names: Sequence[str], dead: Iterable[int]) -> List[int]:
    """Features entailed by names ∪ root (dead features excluded), aggregated."""
    skip, core = set(dead), []
    for f in range(1, th.n_vars + 1):
        if f in skip:
            continue
        if th.sat(names, [ROOT_LIT, -f]):
            skip |= th.selected()[1]
        else:
            core.append(f)
    return core


def quickxplain(th: SelectorTheory, lits: Sequence[int], cands: Sequence[str]) -> Optional[List[str]]:
    """Minimal CS ⊆ cands with CS ∪ lits UNSAT; None if cands ∪ lits is SAT."""
    if th.sat(cands, lits):
        return None
    if not cands:
        return []

    def qxi(bg, delta, c):
        if delta and not th.sat(bg, lits):
            return []
        if len(c) == 1:
            return list(c)
        k = len(c) // 2
        d2 = qxi(bg + c[:k], c[:k], c[k:])
        d1 = qxi(bg + d2, d2, c[:k])
        return d1 + d2

    return qxi([], [], list(cands))


def hs_diagnosis(th: SelectorTheory, cands: Sequence[str], positives: Sequence[int],
                 negatives: Sequence[Sequence[int]], node_limit: int = 2000):
    """Minimum-cardinality D ⊆ cands such that, with S = cands ∖ D, every f in positives is
    alive (S ∪ root ∪ {f} SAT) and every e⁻ in negatives stays rejected (S ∪ root ∪ e⁻ UNSAT).
    ``cands`` is in removal-preference order. Returns (D or None, status, checks, nodes)."""
    start, rank = th.calls, {c: i for i, c in enumerate(cands)}
    queue, seen, nodes = deque([()]), {()}, 0
    while queue:
        if nodes >= node_limit:
            return None, 'node_limit', th.calls - start, nodes
        path = queue.popleft()
        nodes += 1
        removed = set(path)
        keep = [c for c in cands if c not in removed]
        if any(th.sat(keep, [ROOT_LIT] + list(e)) for e in negatives):
            continue                      # accepts a negative; supersets do too → prune
        f = next((f for f in positives if not th.sat(keep, [ROOT_LIT, f])), None)
        if f is None:
            return list(path), 'found', th.calls - start, nodes
        for c in quickxplain(th, [ROOT_LIT, f], keep):
            child = tuple(sorted(removed | {c}, key=rank.get))
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return None, 'none', th.calls - start, nodes
