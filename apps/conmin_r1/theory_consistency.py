"""Consistency of a delivered theory with the root axiom, and the UNSAT reporting rule.

Rule (decided 2026-10-25): an UNSAT delivered theory is its own category. It is never scored
(no P/R/F1 is assigned to it) and never dropped silently: every aggregate is computed over
the consistent folds and annotated "(n UNSAT)".
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

from pysat.solvers import Solver

ROOT = [[1]]          # root unit for all five FMs (FMOracle.get_root_clauses(), checked)


def sat(clauses: Iterable[Sequence[int]]) -> int:
    with Solver(name='glucose4', bootstrap_with=[list(c) for c in clauses]) as s:
        return int(s.solve())


def consistent_with_root(learned, ne=()) -> int:
    """1 iff learned ∪ NE ∪ root is satisfiable (the delivered theory with the root axiom)."""
    return sat(list(learned) + [list(c) for c in ne] + ROOT)


def unsat_note(n_unsat: int) -> str:
    return f'({n_unsat} UNSAT)' if n_unsat else ''


def consistent_values(values, flags) -> list:
    """Values of the consistent folds only (flags: 1 = consistent)."""
    return [v for v, ok in zip(values, flags) if ok]


def mean_or_none(values) -> Optional[float]:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None
