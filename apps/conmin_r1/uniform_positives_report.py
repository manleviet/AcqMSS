"""Aggregate Step 5 (uniform positives) into the generated section of uniform_positives.md.

Bins: Table-5 thirds of the ORIGINAL n_train_pos (``thirds_by_positives``) and 2-COV separately.
UNSAT runs (Reduce(A) ∪ root inconsistent) are counted, not scored. Gate: the ``original`` variant
reproduces the persisted Reduce(A) (names, and every compared score column).
ε(n) = (ln|B| + ln 20) / n, n = positives actually used; compared with the D-mass of the region
Reduce(A) rejects, which under the uniform D over sol(Cτ) is 1 − sol R.

usage: python -m apps.conmin_r1.uniform_positives_report
"""
from __future__ import annotations

import json
import math
import statistics as st

from . import KBS
from .dead_features_report import CLASSES, mm, table
from .reduce_a_ablation import OUT_DIR as REDUCE_DIR
from .reduce_a_binned_view import KB_LABEL, thirds_by_positives
from .uniform_positives import OUT_DIR, VARIANTS

BEGIN, END = '<!-- BEGIN generated -->', '<!-- END generated -->'
GATE_KEYS = ('desc_f1', 'P_std_bg_root', 'R_bg_root', 'F1_std_bg_root', 'sol_precision',
             'sol_recall', 'exact_equiv', 'accuracy', 'models_theory', 'models_both')


def load():
    runs = {}
    for kb in KBS:
        for p in (OUT_DIR / kb).glob('*_fold*_*.json'):
            r = json.loads(p.read_text())
            runs[(r['kb'], r['example_set'], r['fold'], r['variant'])] = r
    return runs


def gate(runs):
    n, bad = 0, []
    for (kb, es, f, v), r in runs.items():
        if v != 'original' or 'reduce_a' not in r:
            continue
        n += 1
        ref = json.loads((REDUCE_DIR / kb / f'{es}_fold{f}.json').read_text())
        if r['reduce_a'] != ref['reduce_a']:
            bad.append((kb, es, f, 'names'))
        persisted = {s['condition']: s for s in ref['scores']}
        for s in r['scores']:
            q = persisted[s['condition']]
            bad += [(kb, es, f, s['condition'], k) for k in GATE_KEYS if str(s.get(k)) != str(q.get(k))]
    return n, bad


def score(r, cond):
    return next(s for s in r['scores'] if s['condition'] == cond)


def ok(r):
    return 'scores' in r and score(r, 'Reduce(A)')['consistent_with_root']


def groups(runs):
    out = []
    for kb in KBS:
        folds = {(r['n_train_pos_original'], es, f) for (k, es, f, v), r in runs.items()
                 if k == kb and v == 'original'}
        t5 = [x for x in folds if x[1] != '2cov']
        if len(t5) != 15:              # incomplete KB: thirds undefined until all folds exist
            if t5:
                out.append((kb, f'partial ({len(t5)} of 15 folds)', {(es, f) for _, es, f in t5}))
        else:
            for third, members, (lo, hi) in thirds_by_positives(t5):
                out.append((kb, f'{third} ({lo}–{hi})', members))
        out.append((kb, '2-COV', {(es, f) for _, es, f in folds if es == '2cov'}))
    return out


def sel(runs, kb, members, v):
    rs = [runs.get((kb, es, f, v)) for es, f in sorted(members)]
    return [r for r in rs if r is not None]


def ratio_cells(runs, kb, members, v):
    pairs = []
    for es, f in members:
        o, u = runs.get((kb, es, f, 'original')), runs.get((kb, es, f, v))
        if o and u and ok(o) and ok(u):
            a, b = score(o, 'Reduce(A)')['sol_recall'], score(u, 'Reduce(A)')['sol_recall']
            if a > 0 and b > 0:
                pairs.append(b / a)
    if not pairs:
        return '—', '—'
    return f'{st.median(pairs):.3g}', f'{math.exp(st.mean(math.log(x) for x in pairs)):.3g}'


def build(runs):
    a, b, c, d, e = [], [], [], [], []
    for kb, label, members in groups(runs):
        for v in VARIANTS:
            rs = sel(runs, kb, members, v)
            good = [r for r in rs if ok(r)]
            if len(rs) < len(members):      # absent or partial (e.g. a lone probe): no statistic
                status = 'not measured' if not rs else f'partial ({len(rs)} of {len(members)} folds), not reported'
                for t, width in ((a, 7), (b, len(CLASSES)), (c, 1), (d, 6), (e, 2)):
                    t.append([KB_LABEL[kb], label, v, status] + [''] * width)
                continue
            note = f' ({len(rs) - len(good)} UNSAT)' if len(good) < len(rs) else ''
            ra = [score(r, 'Reduce(A)') for r in good]
            cs = [score(r, 'ConMin k=1') for r in good]
            spur = [[x for x in r['reduce_a_constraints'] if x['spurious']] for r in good]
            lead = [KB_LABEL[kb], label, v + note, mm([r['n_pos_used'] for r in rs], 0)]
            med, geo = ('—', '—') if v == 'original' else ratio_cells(runs, kb, members, v)
            a.append(lead + [mm([len(r['reduce_a']) for r in good], 1), mm([len(s) for s in spur], 1),
                             mm([s['P_std_bg_root'] for s in ra if s['P_std_bg_root'] != '']),
                             mm([s['F1_std_bg_root'] for s in ra]), mm([s['sol_recall'] for s in ra]),
                             med, geo])
            b.append(lead + [mm([sum(x['class'] == k for x in s) for s in spur], 1) for k in CLASSES])
            c.append(lead + [mm([r['n_dead_reduce_a'] for r in good], 1)])
            d.append(lead + [mm([len(r['reduce_a']) for r in good], 1), mm([len(r['conmin']) for r in good], 1),
                             mm([s['sol_precision'] for s in ra]), mm([s['sol_precision'] for s in cs]),
                             mm([s['sol_recall'] for s in ra]), mm([s['sol_recall'] for s in cs])])
            eps = [(math.log(r['n_bias']) + math.log(20)) / r['n_pos_used'] for r in rs if r['n_pos_used']]
            e.append(lead + [mm(eps, 3) if eps else '— (n = 0)',
                             mm([1 - s['sol_recall'] for s in ra], 3)])
    return a, b, c, d, e


def main():
    runs = load()
    n_gate, bad = gate(runs)
    a, b, c, d, e = build(runs)
    lead = ['KB', 'bin (orig. n_train_pos)', 'positives', 'n used']
    val = json.loads((OUT_DIR / 'sampler_validation.json').read_text())
    sec = [BEGIN, '', f'**Gate:** with the original positives the re-learn reproduces the persisted '
           f'Reduce(A) (names and {len(GATE_KEYS)} score columns, Reduce(A) and ConMin k=1) on '
           f'{n_gate} folds, **{len(bad)} mismatches**. Runs: {len(runs)}.', '',
           '## Sampler validation (REAL-FM-7)', '',
           table(['draws', 'seed', 'solutions', 'χ²', 'df', 'p', 'min / max count', 'expected'],
                 [[str(r['draws']), str(r['seed']), str(r['solutions']), f"{r['chi2']:.2f}",
                   str(r['df']), f"{r['p']:.3f}", f"{r['min_count']} / {r['max_count']}",
                   f"{r['expected']:.0f}"] for r in val]), '',
           '## a. Reduce(A): original vs uniform positives', '',
           table(lead + ['\\|Reduce(A)\\|', '#spurious', 'sem P_std', 'sem F1', 'sol R',
                         'sol R ratio vs original: median', 'geo-mean'], a), '',
           '## b. Spurious constraints of Reduce(A) by class (fold means)', '',
           table(lead + list(CLASSES), b), '',
           '## c. Dead features of Reduce(A) ∪ root', '', table(lead + ['#dead'], c), '',
           '## d. Stage 2 (C ∪ S, k = 1) vs Reduce(A)', '',
           table(lead + ['\\|Reduce(A)\\|', '\\|C∪S\\|', 'sol P Reduce(A)', 'sol P C∪S',
                         'sol R Reduce(A)', 'sol R C∪S'], d), '',
           '## e. Bound ε(n) = (ln\\|B\\| + ln 20)/n vs measured rejected mass 1 − sol R of Reduce(A)',
           '', table(lead + ['ε(n)', '1 − sol R'], e), '', END]
    path = OUT_DIR / 'uniform_positives.md'
    text = path.read_text() if path.exists() else ''
    body = '\n'.join(sec)
    text = (text[:text.index(BEGIN)] + body + text[text.index(END) + len(END):]
            if BEGIN in text else text.rstrip('\n') + '\n\n' + body + '\n')
    path.write_text(text)
    print(f'gate: {n_gate} folds, {len(bad)} mismatches', bad[:5])


if __name__ == '__main__':
    main()
