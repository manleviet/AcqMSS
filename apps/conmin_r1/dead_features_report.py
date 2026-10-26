"""Aggregate Step 4 (dead features): fold CSV + per-constraint CSV + summary CSV + the generated
part of dead_features.md. Bins: the Table-5 thirds of n_train_pos (``thirds_by_positives``,
same as reduce_a_ablation.md) and 2-COV separately. UNSAT folds counted, never scored. Gate:
A and ConMin re-scored through the Step-4 path equal the persisted shipped scores.

Sol R gap closed by repair (per fold, Reduce(A) sol R = r0 < 1, repaired r1):
linear (r1 − r0)/(1 − r0) and log-scale log(r1/r0)/log(1/r0); reported as mean and median.

usage: python -m apps.conmin_r1.dead_features_report
"""
from __future__ import annotations

import csv
import json
import math
import statistics as st

from . import KBS
from .dead_features import OUT_DIR
from .reduce_a_ablation_report import gate
from .reduce_a_binned_view import KB_LABEL, thirds_by_positives

THEORIES = ('Reduce(A)', 'ConMin k=1', 'UB', 'EST', 'UB_A')
CLASSES = ('R∩C', 'C∖R', 'R∖C', 'S', 'V_obs', 'V_unseen')
BEGIN, END = '<!-- BEGIN generated -->', '<!-- END generated -->'


def load():
    return [json.loads(p.read_text()) for kb in KBS for p in sorted((OUT_DIR / kb).glob('*.json'))]


def bins(folds):
    """[(kb, bin label, folds)] — Table-5 thirds, then 2-COV."""
    out = []
    for kb in KBS:
        mine = [f for f in folds if f['kb'] == kb]
        t5 = [f for f in mine if f['example_set'] != '2cov']
        for third, members, (lo, hi) in thirds_by_positives(
                (f['n_train_pos'], f['example_set'], f['fold']) for f in t5):
            out.append((kb, f'{third} ({lo}–{hi})',
                        [f for f in t5 if (f['example_set'], f['fold']) in members]))
        out.append((kb, '2-COV', [f for f in mine if f['example_set'] == '2cov']))
    return out


def mm(vals, d=2):
    """'mean (median)' over defined values; tiny values in 2 significant digits."""
    v = [x for x in vals if x is not None]
    if not v:
        return '—'
    g = lambda x: f'{x:.2g}' if 0 < abs(x) < 0.01 else f'{x:.{d}f}'
    return f'{g(st.mean(v))} ({g(st.median(v))})'


def gap_closed(r0, r1):
    if r0 is None or r1 is None or r0 >= 1:
        return None, None
    lin = (r1 - r0) / (1 - r0)
    log = math.log(r1 / r0) / math.log(1 / r0) if r0 > 0 and r1 > 0 else None
    return lin, log


def score(f, cond):
    return next((s for s in f['scores'] if s['condition'] == cond), None)


def part1_rows(groups):
    rows = []
    for kb, label, fs in groups:
        ok = [f for f in fs if f['consistent']]
        rows.append([KB_LABEL[kb], label, f'{len(fs)} ({len(fs) - len(ok)} UNSAT)',
                     str(len(fs[0]['dead_ct'])), mm([len(f['dead_t']) for f in ok], 1),
                     mm([f['calls_dead_t'] for f in ok], 1), str(fs[0]['n_features']),
                     mm([len(f['false_optionals']) for f in ok], 1)])
    return rows


def part2_rows(groups):
    rows, flags = [], []
    for kb, label, fs in groups:
        ok = [f for f in fs if f['consistent']]
        cs = [c for f in ok for c in f['conflicts'].values()]
        single = f'{sum(len(c) == 1 for c in cs)}/{len(cs)}' if cs else '—'
        cells = []
        for cls in CLASSES:
            per = [[c for c in f['constraints'] if c['spurious'] and c['class'] == cls]
                   for f in ok]
            tot = [len(p) for p in per]
            if not any(tot):
                cells.append('0')
                continue
            cells.append(f"{st.mean(tot):.1f}/{st.mean(sum(c['in_conflict'] for c in p) for p in per):.1f}"
                         f"/{st.mean(sum(c['in_certain'] for c in p) for p in per):.1f}"
                         f"/{st.mean(sum(not c['in_conflict'] for c in p) for p in per):.1f}")
        for f in ok:
            flags += [(kb, f['example_set'], f['fold'], c['name']) for c in f['constraints']
                      if c['in_certain'] and not c['spurious']]
        rows.append([KB_LABEL[kb], label, mm([len(f['dead_t']) for f in ok], 1), single,
                     mm([len(f['certain']) for f in ok], 1),
                     mm([sum(c['spurious'] for c in f['constraints']) for f in ok], 1)] + cells)
    return rows, flags


def part3_rows(groups):
    rows, ratio_rows = [], []
    for kb, label, fs in groups:
        ok = [f for f in fs if f['consistent']]
        for cond in THEORIES:
            ss = [score(f, cond) for f in ok]
            ss = [s for s in ss if s]
            rows.append([KB_LABEL[kb], label, cond, mm([s['n_kb'] for s in ss], 1),
                         mm([s['desc_p'] for s in ss]), mm([s['desc_f1'] for s in ss]),
                         mm([s['P_std_bg_root'] for s in ss if s['P_std_bg_root'] != '']),
                         mm([s['F1_std_bg_root'] for s in ss]),
                         mm([s['sol_precision'] for s in ss]), mm([s['sol_recall'] for s in ss]),
                         mm([f['dead_remaining'][cond] for f in ok if 'dead_remaining' in f], 1)])
        d = [f['diagnosis'] for f in ok if 'diagnosis' in f]
        for cond in ('UB', 'UB_A'):
            r = [(score(f, 'Reduce(A)')['sol_recall'], score(f, cond)['sol_recall']) for f in ok
                 if score(f, cond)]
            ratios = [b / a for a, b in r if a > 0]
            gc = [gap_closed(a, b) for a, b in r]
            ratio_rows.append([KB_LABEL[kb], label, cond, str(len(r)),
                               f'{st.median(ratios):.3g}' if ratios else '—',
                               f'{math.exp(st.mean(math.log(x) for x in ratios)):.3g}'
                               if ratios else '—',
                               mm([g[0] for g in gc]), mm([g[1] for g in gc])])
        if d:
            rows.append([KB_LABEL[kb], label, 'EST diagnosis', '|D| ' + mm([x['n_D'] for x in d], 1),
                         'spurious in D ' + mm([x['n_D_spurious'] for x in d], 1),
                         'checks ' + mm([x['checks'] for x in d], 0),
                         'status ' + ', '.join(sorted({x['status'] for x in d})),
                         'e⁻ broken by Certain ' + mm([x['negatives_broken_by_certain'] for x in d], 1),
                         '', '', ''])
    return rows, ratio_rows


def table(head, rows):
    return '\n'.join(['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] +
                     ['| ' + ' | '.join(r) + ' |' for r in rows])


def main():
    folds = load()
    bad = gate(folds)
    groups = bins(folds)
    p2, flags = part2_rows(groups)
    p3, ratios = part3_rows(groups)
    sec = [BEGIN, '', f'**Gate:** A and ConMin k=1 re-scored through the Step-4 path equal the '
           f'persisted shipped scores on {len(folds)} folds, **{len(bad)} mismatches**.', '',
           '## Part 1 — detection', '',
           table(['KB', 'bin (n_train_pos)', 'folds', '#dead(Cτ)', '#dead(T)', 'SAT calls',
                  '#features', '#false optionals'], part1_rows(groups)), '',
           '## Part 2 — anatomy', '',
           'Spurious constraints by class: total / in a conflict / in Certain / in no conflict '
           '(= residual), fold means.', '',
           table(['KB', 'bin', '#dead(T)', 'singleton CS', '\\|Certain\\|', '#spurious']
                 + list(CLASSES), p2), '',
           f'Target (non-spurious) constraints in Certain: **{len(flags)}**'
           + (' — ' + ', '.join(f'{KB_LABEL[k]} {e} f{f} {c}' for k, e, f, c in flags[:20])
              if flags else '') + '.', '',
           '## Part 3 — what repair recovers', '',
           table(['KB', 'bin', 'theory', '\\|KB\\|', 'desc P', 'desc F1', 'sem P_std', 'sem F1',
                  'sol P', 'sol R', '#dead remaining'], p3), '',
           'sol R of the repaired theory relative to Reduce(A), per fold: median and geometric '
           'mean of the ratio; share of the sol R gap (to 1) closed, linear and log scale.', '',
           table(['KB', 'bin', 'theory', 'folds', 'ratio median', 'ratio geo-mean',
                  'gap closed (linear)', 'gap closed (log)'], ratios), '', END]
    path = OUT_DIR / 'dead_features.md'
    text = path.read_text() if path.exists() else ''
    body = '\n'.join(sec)
    text = (text[:text.index(BEGIN)] + body + text[text.index(END) + len(END):]
            if BEGIN in text else text.rstrip('\n') + '\n\n' + body + '\n')
    path.write_text(text)
    with open(OUT_DIR / 'dead_features_constraints.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['kb', 'example_set', 'fold', 'n_train_pos', 'name', 'class', 'support',
                    'spurious', 'in_conflict', 'in_certain'])
        for f in folds:
            for c in f.get('constraints', []):
                w.writerow([f['kb'], f['example_set'], f['fold'], f['n_train_pos'], c['name'],
                            c['class'], c['support'], int(c['spurious']), int(c['in_conflict']),
                            int(c['in_certain'])])
    print(f'gate mismatches: {len(bad)}; target constraints in Certain: {len(flags)}')


if __name__ == '__main__':
    main()
