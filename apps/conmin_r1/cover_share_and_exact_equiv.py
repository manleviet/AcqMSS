"""Two cheap measures on the persisted KBs.

(a) Cover share, k = 1. ConMin's S is {c ∈ A ∖ C : support⁺(c) ≥ k} (conmin.py:252-254), so
    C ∩ S = ∅ by construction and "C ⊆ S" is trivially false. The support-only ablation keeps
    S_full = {c ∈ A : support⁺(c) ≥ 1} with no cover step. Since S_full = S ∪ (C ∩ S_full),
    C ⊆ S_full ⇔ S_full = C ∪ S: the ablation then delivers ConMin's pre-Reduce theory.
    Reported per fold: |C|, |C ∖ S_full|, C ⊆ S_full; per KB the fraction of folds with C ⊆ S_full.
(b) Exact-equivalence rate per condition and KB (shipped exact_equiv of the re-run, which the
    reproduction gate equates with the committed one), Table-5 aggregation.

usage: python -m apps.conmin_r1.cover_share_and_exact_equiv
"""
from __future__ import annotations

import csv

from . import KBS, R1_DIR
from .kb_store import iter_records, table5_key
from .reproduction_gate import KEY, committed_rows
from .table5_aggregation import SWEEP, cell, select_sweep, value


def _write(name, rows):
    with open(R1_DIR / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    committed = committed_rows()
    cover_rows, eq_rows = [], []
    for rec in iter_records():
        key = {'kb': rec['kb'], 'example_set': rec['example_set'], 'fold': str(rec['fold'])}
        if rec['condition'] == 'C':
            cover, s_full = set(rec['names']), set(rec['support_full_k1_names'])  # C slice = cover
            cover_rows.append({**key, 'n_cover': len(cover), 'n_support_full_k1': len(s_full),
                               'n_cover_minus_support_full': len(cover - s_full),
                               'cover_subset_of_support_full': int(cover <= s_full)})
        row = {**key, **table5_key(rec), 'exact_equiv': rec['shipped']['exact_equiv']}
        row['convergence_reason'] = committed[tuple(row[k] for k in KEY)]['convergence_reason']
        eq_rows.append(row)
    _write('cover_share_rows.csv', cover_rows)

    summary = []
    for kb in KBS:   # Table-5 samplings only; 2-COV folds stay in cover_share_rows.csv
        rows = [r for r in cover_rows if r['kb'] == kb and r['example_set'] != '2cov']
        if not rows:
            continue
        n = len(rows)
        summary.append({'kb': kb, 'measure': 'C ⊆ S_full (k=1)', 'strategy': 'ConMin',
                        'n_folds': n,
                        'value': round(sum(r['cover_subset_of_support_full'] for r in rows) / n, 4),
                        'mean_cover': round(sum(r['n_cover'] for r in rows) / n, 2),
                        'mean_cover_minus_support_full':
                            round(sum(r['n_cover_minus_support_full'] for r in rows) / n, 2)})
        kb_eq = [r for r in eq_rows if r['kb'] == kb]
        for label in SWEEP:
            sel = select_sweep(kb_eq, label)
            if sel:
                stat = cell(sel, 'exact_equiv')
                summary.append({'kb': kb, 'measure': 'exact_equiv rate', 'strategy': label,
                                'n_folds': len(sel), 'value': value(stat),
                                'mean_cover': '', 'mean_cover_minus_support_full': ''})
    _write('cover_share_and_exact_equiv.csv', summary)
    for s in summary:
        print(f"{s['kb']:12s} {s['measure']:17s} {s['strategy']:13s} n={s['n_folds']:2d} "
              f"{s['value']}  {s['mean_cover']} {s['mean_cover_minus_support_full']}")


if __name__ == '__main__':
    main()
