"""Strategy -> exact (condition, negatives, k) row filter (v1 "Strategy -> CSV filter").

Sentinels verified against ``REAL-FM-7_long.csv`` (2026-07-26): each pinned filter
selects exactly 18 rows (six samplings x 3 folds) / 15 with exclude-2COV, and reproduces
the CW-Main anchors. ``negatives`` and ``k`` are matched EXACTLY (``k == ''`` for the
blank strategies, ``k == '1'`` for ConMin) — never "any", which would sweep the k-sweep /
reduced rows into one cell (C-union-S alone spans 144 rows across k x negatives).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Filter:
    condition: str
    negatives: str
    k: str


# Paper column -> filter, in paper super-column order.
STRATEGIES: dict[str, Filter] = {
    "A": Filter("A", "n/a", ""),
    "C": Filter("C", "raw", ""),
    "C∪S": Filter("C∪S", "raw", "1"),
    "QuAcq": Filter("QuAcq", "n/a", ""),
    "QuAcq-active": Filter("QuAcq-active", "n/a", ""),
}


def select(rows: list[dict], strategy: str, *, exclude_2cov: bool = True,
           k: Optional[str] = None, negatives: Optional[str] = None) -> list[dict]:
    """Rows matching ``strategy`` exactly.

    ``k`` / ``negatives`` override the strategy defaults for the appendix tables that
    sweep those axes (``k`` for app-ksweep, ``negatives`` for app-rawred).
    """
    spec = STRATEGIES[strategy]
    want_k = spec.k if k is None else k
    want_neg = spec.negatives if negatives is None else negatives
    out = []
    for row in rows:
        if row.get("condition") != spec.condition:
            continue
        if row.get("negatives") != want_neg:
            continue
        if row.get("k") != want_k:
            continue
        if exclude_2cov and row.get("example_set") == "2cov":
            continue
        out.append(row)
    return out
