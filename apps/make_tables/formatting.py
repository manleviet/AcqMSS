"""Render ``CellStat`` values per v1 rounding; build ``Cell`` render-objects for the tables.

``fmt`` gives the plain rounded string (v1 rounding). ``Cell`` carries the rounded text
plus the two v3 markers a renderer applies: a dagger (non-converged, v2 G2.3) and bold
(per-row best value — computed via ``bold_winners``, NEVER hardcoded to a column).
"""
from __future__ import annotations

from collections import namedtuple
from typing import Optional

from .aggregate import CellStat

MISSING = "--"

# metric kind -> decimal places (v1 rounding). 'checks' is integer-rounded separately.
_DECIMALS = {"rate": 2, "size": 1, "runtime": 1, "queries": 1}

# A render-ready cell: the rounded text + whether to dagger / bold it (renderer-agnostic).
# ``raw`` marks text that is ALREADY rendered LaTeX (the compact "P/R/F1" cell, which carries
# its own \textbf/\dagger markup): the renderer passes it through untouched instead of escaping
# it. Defaulted so every existing 3-positional ``Cell(text, dagger, bold)`` call still works.
Cell = namedtuple("Cell", "text dagger bold raw", defaults=(False,))


def fmt(stat: Optional[CellStat], kind: str = "rate", *, dagger: str = "") -> str:
    """Format a cell value with fixed decimals; append ``dagger`` iff non-converged."""
    if stat is None or stat.value is None:
        return MISSING
    if kind == "checks" or (kind == "size" and abs(stat.value) >= 1000):
        # A theory size in the thousands is reported to the unit: the tenth of a constraint that
        # a fold-mean produces is below the resolution the quantity actually has, and the paper
        # prints $3{,}048$ for it. Runtimes and query counts keep their decimal — there the
        # fraction is a real measurement, not an artefact of averaging integers.
        text = str(int(round(stat.value)))
    else:
        text = f"{stat.value:.{_DECIMALS.get(kind, 2)}f}"
    return f"{text}{dagger}" if (dagger and stat.nonconverged) else text


def make_cell(stat: Optional[CellStat], kind: str = "rate", *, bold: bool = False) -> Cell:
    """A render-ready ``Cell``: rounded text + dagger flag (non-converged) + bold flag."""
    if stat is None or stat.value is None:
        return Cell(MISSING, False, False)
    return Cell(fmt(stat, kind), stat.nonconverged, bold)


def bold_winners(stats: list[Optional[CellStat]], kind: str = "rate") -> list[Cell]:
    """Cells for a row of comparable stats, bolding the max value(s) — computed, not hardcoded."""
    vals = [s.value for s in stats if s is not None and s.value is not None]
    best = max(vals) if vals else None
    return [
        make_cell(s, kind,
                  bold=(best is not None and s is not None and s.value is not None
                        and abs(s.value - best) < 1e-9))
        for s in stats
    ]
