"""Table-5 aggregation shared by the r1 measures: make_tables' own strategy filters
(exclude 2cov; ConMin raw k=1; non-converged folds excluded unless all are, via cv_mean),
extended with the C∪S raw k-sweep. Rows are dicts with string fields
(condition / negatives / k / example_set / convergence_reason), like the long CSV."""
from __future__ import annotations

from typing import Dict, List

from apps.make_tables.aggregate import CellStat, cv_mean
from apps.make_tables.filters import Filter, STRATEGIES, select

SWEEP: Dict[str, Filter] = {
    **STRATEGIES, **{f'C∪S k={k}': Filter('C∪S', 'raw', str(k)) for k in (2, 3, 5)}}


def select_sweep(rows: List[dict], label: str) -> List[dict]:
    if label in STRATEGIES:
        return select(rows, label)
    return select(rows, 'C∪S', k=SWEEP[label].k)


def cell(rows: List[dict], col: str) -> CellStat:
    return cv_mean(rows, col)


def value(stat: CellStat, ndigits: int | None = 4):
    if stat.value is None:
        return ''
    return stat.value if ndigits is None else round(stat.value, ndigits)
