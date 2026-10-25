"""SUPERSEDED by semantic_tier_corrected (kept: produced the handoff-1 table). Join re-run rows to the committed conmin_eval_long.csv, check the shipped sem_* reproduce,
and aggregate old vs bg=root semantic P/R/F1 with make_tables' own select + cv_mean (Table 5:
eval-prf, exclude 2cov, ConMin raw k=1, non-converged folds excluded unless all are)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from apps.make_tables import KBS
from apps.make_tables.aggregate import cv_mean
from apps.make_tables.filters import select, STRATEGIES

OUT = Path('data/results_conmin_r1/handoff1/rows')
KEY = ('kb', 'example_set', 'fold', 'condition', 'negatives', 'k')
committed = {tuple(r[k] for k in KEY): r
             for r in csv.DictReader(open('data/results_conmin/conmin_eval_long.csv'))}


def load_rerun(kb):
    rows = []
    for p in sorted(OUT.glob(f'{kb}*_rows.csv')):
        rows += list(csv.DictReader(open(p)))
    return rows


def fmt(c):
    return '--' if c.value is None else f"{c.value:.3f}{'†' if c.nonconverged else ''}"


mismatch = 0
print('| KB | cond | n | old P/R/F1 (committed) | new P/R/F1 (bg=root) | ΔR | FP: Cτ vs Cτ\\root | pure P (KB-side) |')
print('|---|---|---|---|---|---|---|---|')
for kb in KBS:
    rerun = load_rerun(kb)
    if not rerun:
        continue
    for r in rerun:   # direction-pure precision: share of KB clauses entailed by Cτ (bg-independent)
        n = int(r['n_kb_clauses'])
        r['sem_p_pure'] = (n - int(r['sem_fp_root'])) / n if n else ''
    for r in rerun:   # reproduction check of the shipped semantic tier, row by row
        c = committed.get(tuple(r[k] for k in KEY))
        if c is None:
            print('  no committed row for', [r[k] for k in KEY], file=sys.stderr); mismatch += 1; continue
        for m in ('sem_p', 'sem_r', 'sem_f1'):
            if abs(float(c[m]) - float(r[m])) > 1e-9 or abs(float(r[m]) - float(r[m + '_noroot'])) > 1e-9:
                print('  MISMATCH', [r[k] for k in KEY], m, c[m], r[m], r[m + '_noroot'], file=sys.stderr)
                mismatch += 1
        if r.get('size') != c.get('size'):
            print('  SIZE MISMATCH', [r[k] for k in KEY], c['size'], r['size'], file=sys.stderr); mismatch += 1
    for s in STRATEGIES:
        old_rows = select([c for c in committed.values() if c['kb'] == kb], s)
        new_rows = select(rerun, s)
        if not new_rows:
            continue
        old = [cv_mean(old_rows, f'sem_{m}') for m in 'p r f1'.split()]
        new = [cv_mean(new_rows, f'sem_{m}_root') for m in 'p r f1'.split()]
        fp_ct = sum(int(r['sem_fp_root']) for r in new_rows)
        fp_wo = sum(int(r['sem_fp_vs_ct_without_root']) for r in new_rows)
        dr = (new[1].value or 0) - (old[1].value or 0)
        pure = fmt(cv_mean(new_rows, 'sem_p_pure'))
        print(f"| {kb} | {s} | {len(new_rows)}/{len(old_rows)} | {'/'.join(map(fmt, old))} | "
              f"{'/'.join(map(fmt, new))} | {dr:+.3f} | {fp_ct} vs {fp_wo} | {pure} |")
print(f'\nreproduction mismatches: {mismatch}', file=sys.stderr)
