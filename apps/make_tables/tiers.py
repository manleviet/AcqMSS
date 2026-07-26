"""The three metric tiers (v2 G1): Description, Clause, Semantic. P & R separate.

Order Desc -> Clause -> Sem (strictest first). Desc is strict — no alias tolerance;
we surface the raw ``desc_*`` columns. Each tier returns a ``CellStat`` per metric so
the renderer formats / daggers uniformly.
"""
from __future__ import annotations

from .aggregate import CellStat, cv_mean

# (label, CSV column prefix) in the fixed Desc -> Clause -> Sem order.
TIERS = (("Desc", "desc"), ("Clause", "clause"), ("Sem", "sem"))


def prf(rows: list[dict], prefix: str) -> dict[str, CellStat]:
    """{'p','r','f1'} CellStats for one tier (``prefix`` in {desc, clause, sem})."""
    return {metric: cv_mean(rows, f"{prefix}_{metric}") for metric in ("p", "r", "f1")}
