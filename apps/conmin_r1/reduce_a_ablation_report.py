"""Aggregate the Reduce(A) ablation: per-fold CSV, Table-5 means and medians, 2-COV apart.

Gate first: the A and ConMin rows re-scored here must equal the persisted shipped scores
(desc F1, sem P/R/F1 with bg = [], exact_equiv, accuracy) — so Reduce(A) is compared through
the same scoring path. UNSAT rule: UNSAT folds are counted per cell ("n UNSAT"), never scored.

usage: python -m apps.conmin_r1.reduce_a_ablation_report
"""
from __future__ import annotations

import csv
import json
import statistics as st

from . import KBS, R1_DIR
from .kb_store import record_path
from .reduce_a_ablation import OUT_DIR

CONDS = ('A', 'Reduce(A)', 'ConMin k=1')
FOLD_COLS = ('n_train_pos', 'n_A', 'n_R', 'n_S_full', 'n_V', 'n_V_kept', 'n_V_in_conmin',
             'n_reduce_a', 'n_reduce_a_pool_order', 'n_reduce_a_minus_conmin',
             'n_conmin_minus_reduce_a')
SUMMARY = (('n_kb', '|KB|'), ('desc_p', 'desc P'), ('desc_f1', 'desc F1'),
           ('P_std_bg_root', 'sem P_std'), ('F1_std_bg_root', 'sem F1_std'),
           ('F1_code_bg_root', 'sem F1_code'), ('sol_precision', 'sol P'),
           ('sol_recall', 'sol R'), ('V_kept', '|V kept|'))


def load():
    folds = []
    for kb in KBS:
        for path in sorted((OUT_DIR / kb).glob('*_fold*.json')):
            folds.append(json.loads(path.read_text()))
    return folds


def gate(folds):
    bad = []
    for f in folds:
        recs = {(r['condition'], r['k']): r['shipped'] for r in
                json.loads(record_path(f['kb'], f['example_set'], f['fold']).read_text())}
        for row, key in ((f['scores'][0], ('A', None)), (f['scores'][2], ('C∪S', 1))):
            if not row['consistent_with_root']:
                continue
            ship = recs[key]
            for mine, theirs in (('desc_f1', 'desc_f1'), ('P_code_bg_empty', 'sem_p'),
                                 ('R_bg_empty', 'sem_r'), ('exact_equiv', 'exact_equiv'),
                                 ('accuracy', 'accuracy')):
                if abs(float(row[mine]) - float(ship[theirs])) > 1e-9:
                    bad.append((f['kb'], f['example_set'], f['fold'], key, mine))
    return bad


def flatten(folds):
    rows = []
    for f in folds:
        v_kept = {'A': f['n_V'], 'Reduce(A)': f['n_V_kept'],
                  'ConMin k=1': f.get('n_V_in_conmin', '')}
        for s in f['scores']:
            rows.append({'kb': f['kb'], 'example_set': f['example_set'], 'fold': f['fold'],
                         **{c: f.get(c, '') for c in FOLD_COLS}, **s,
                         'V_kept': v_kept[s['condition']]})
    return rows


def summary_entry(sel, kb, cond, sampling):
    """Mean and median of every SUMMARY column over ``sel`` (one KB × condition × sampling).
    UNSAT folds are counted, not scored: sizes use every fold, scores the consistent ones."""
    ok = [r for r in sel if r['consistent_with_root']]
    n_unsat = len(sel) - len(ok)
    pos = sorted(int(r['n_train_pos']) for r in sel)
    entry = {'kb': kb, 'sampling': sampling, 'condition': cond, 'n_folds': len(sel),
             'n_train_pos_range': str(pos[0]) if pos[0] == pos[-1] else f'{pos[0]}–{pos[-1]}',
             'n_unsat': n_unsat, 'note': f'({n_unsat} UNSAT)' if n_unsat else ''}
    for col, _ in SUMMARY:
        src = sel if col in ('n_kb', 'V_kept') else ok   # sizes defined even if UNSAT
        vals = [float(r[col]) for r in src if r.get(col) not in (None, '')]
        nd = None if col.startswith('sol_') else 4    # ratios span orders of magnitude
        rnd = (lambda x: x) if nd is None else (lambda x: round(x, nd))
        entry[f'{col}_mean'] = rnd(st.mean(vals)) if vals else ''
        entry[f'{col}_median'] = rnd(st.median(vals)) if vals else ''
    return entry


def summarise(rows, two_cov):
    out = []
    for kb in KBS:
        for cond in CONDS:
            sel = [r for r in rows if r['kb'] == kb and r['condition'] == cond
                   and (r['example_set'] == '2cov') == two_cov]
            if sel:
                out.append(summary_entry(sel, kb, cond,
                                         '2-COV' if two_cov else 'Table 5 (excl. 2-COV)'))
    return out


def _write(name, rows):
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(R1_DIR / name, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main():
    folds = load()
    bad = gate(folds)
    print(f'gate: {len(folds)} folds, {len(bad)} mismatches', *bad[:5], sep='\n  ')
    rows = flatten(folds)
    for r in rows:
        r.pop('removed', None)
    _write('reduce_a_ablation.csv', rows)
    from .reduce_a_binned_view import binned_entries, write_markdown_section
    binned = binned_entries(rows)
    summary = summarise(rows, False) + summarise(rows, True) + binned
    _write('reduce_a_ablation_summary.csv', summary)
    write_markdown_section(summary)
    for s in summary:
        cells = '  '.join(f"{lab} {s[f'{c}_mean']}/{s[f'{c}_median']}" for c, lab in SUMMARY)
        print(f"{s['kb']:12s} {s['sampling'][:6]:6s} {s['condition']:10s} {cells} {s['note']}")


if __name__ == '__main__':
    main()
