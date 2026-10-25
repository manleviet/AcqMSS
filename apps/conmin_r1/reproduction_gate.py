"""Reproduction gate: every persisted KB's shipped scores (computed by the unmodified
``score_named_kb`` at persist time) must equal the committed ``conmin_eval_long.csv`` row.
C∪S k>1 rows are gated too (the committed sweep has raw k ∈ {1,2,3,5}).

usage: python -m apps.conmin_r1.reproduction_gate [KB]   (exit 1 on any mismatch)
"""
from __future__ import annotations

import csv
import sys
from typing import List, Optional, Tuple

from . import COMMITTED_LONG_CSV
from .kb_store import iter_records, table5_key

KEY = ('kb', 'example_set', 'fold', 'condition', 'negatives', 'k')


def committed_rows() -> dict:
    with open(COMMITTED_LONG_CSV) as f:
        return {tuple(r[k] for k in KEY): r for r in csv.DictReader(f)}


def check(kb: Optional[str] = None) -> Tuple[int, List[str]]:
    committed, problems, n = committed_rows(), [], 0
    for rec in iter_records(kb):
        key = (rec['kb'], rec['example_set'], str(rec['fold']), *table5_key(rec).values())
        row = committed.get(key)
        if row is None:
            problems.append(f'no committed row for {key}')
            continue
        n += 1
        for metric, value in rec['shipped'].items():
            if abs(float(row[metric]) - float(value)) > 1e-9:
                problems.append(f'{key} {metric}: committed {row[metric]} vs re-run {value}')
    return n, problems


def main():
    n, problems = check(sys.argv[1] if len(sys.argv) > 1 else None)
    for p in problems:
        print('MISMATCH', p)
    print(f'reproduction gate: {n} records, {len(problems)} mismatches')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
