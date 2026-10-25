"""SoSyM R1 significance tests recomputed on the re-scored semantic F1 (measurement only).

Same procedure as feat/sosym-r1 ``apps/sosym_r1/significance_tests.py``: paired cells
(KB × sampling), Wilcoxon signed-rank with ``method='exact'`` pinned, ties counted, Holm over
the testable members (floor p ≤ α). Tests 1a ConGen vs example-only, 1b ConGen vs
example-first, 3 semantic vs description tier (description F1 from the stored folds — that
tier is unchanged), 5 example-first vs example-only, 2 2-COV vs mean of random samplings.
Run per F1 variant: F1_code (submitted formula) and F1_std (standard precision; empty KB → 0).
Cells are means over CONSISTENT folds; a cell whose folds are all UNSAT has no value, and its
pair is dropped from the test (listed in ``dropped_all_unsat``).

usage: python -m apps.conmin_r1.sosym_r1_significance_rescored <extracted feat/sosym-r1 tree>
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics as st
from pathlib import Path

from scipy.stats import wilcoxon

from .sosym_r1_precision_check import KBS, NOT_RUN, SAMPLINGS, fold_file, score_all

ALPHA = 0.05
OUT = Path('data/results_conmin_r1/sosym_r1_significance_rescored.csv')


def _count_ties(diff):
    nz = [abs(d) for d in diff if d != 0]
    return (len(diff) - len(nz)) + (len(nz) - len(set(nz)))


def _test(name, pairs, units=None):
    keep = [i for i, (x, y) in enumerate(pairs) if x is not None and y is not None]
    dropped = [units[i] for i in range(len(pairs)) if i not in keep] if units else []
    pairs = [pairs[i] for i in keep]
    units = [units[i] for i in keep] if units else None
    diff = [x - y for x, y in pairs]
    stat, p = wilcoxon([x for x, _ in pairs], [y for _, y in pairs], method='exact')
    out = {'test': name, 'n': len(pairs), 'median': round(st.median(diff), 3),
           'wins': sum(d > 0 for d in diff), 'p': p, 'W': stat, 'ties': _count_ties(diff)}
    out['dropped_all_unsat'] = ' '.join(f'{kb}/{s}' for kb, s in dropped)
    if units:
        out['losses'] = ' '.join(f'{kb}/{s}' for (kb, s), d in zip(units, diff) if d <= 0)
    return out


def _desc_f1(tree, kb, samp):
    folds = json.loads(fold_file(tree, kb, samp, 'congen').read_text())['folds']
    return st.mean(f['evaluation']['description']['metrics']['f1_score'] for f in folds)


def run(tree: Path, cells: dict):
    units = [(kb, s) for kb in KBS for s in SAMPLINGS if (kb, s) not in NOT_RUN]
    desc = {u: _desc_f1(tree, *u) for u in units}
    rows = []
    for col in ('F1_code', 'F1_std'):
        f = {(kb, s, m): cells[(kb, s, m, 'bg_root')][col]
             for kb, s in units for m in ('congen', 'example_only', 'example_first')}
        res = [_test(name, [(f[(*u, a)], f[(*u, b)]) for u in units], units)
               for name, a, b in (('1a congen vs example-only', 'congen', 'example_only'),
                                  ('1b congen vs example-first', 'congen', 'example_first'),
                                  ('5 example-first vs example-only', 'example_first',
                                   'example_only'))]
        res.append(_test('3 semantic vs description tier',
                         [(f[(*u, 'congen')], desc[u]) for u in units], units))
        pairs = []
        for kb in KBS:
            rnd = [f[(kb, s, 'congen')] for s in ('rs_1n', 'rs_2n', 'rs_3n', 'rs_m')
                   if (kb, s) in units]
            pairs.append((f[(kb, '2cov', 'congen')], st.mean(rnd)))     # None if all UNSAT
        res.append(_test('2 2-COV vs random', pairs))
        family = sorted([r for r in res if 2.0 / 2 ** r['n'] <= ALPHA], key=lambda r: r['p'])
        running = 0.0
        for i, r in enumerate(family):
            running = max(running, min(1.0, r['p'] * (len(family) - i)))
            r['holm'], r['reject'] = running, running < ALPHA
        rows += [{'variant': col, **r} for r in res]
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('tree', type=Path)
    tree = ap.parse_args().tree
    cells, _ = score_all(tree)
    rows = run(tree, cells)
    keys = sorted({k for r in rows for k in r}, key=lambda k: list(rows[0]).index(k)
                  if k in rows[0] else 99)
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['variant']:7s} {r['test']:34s} n={r['n']:2d} median={r['median']:+.3f} "
              f"wins={r['wins']} p={r['p']:.3e} holm={r.get('holm', '')} ties={r['ties']} "
              f"losses={r.get('losses', '')}")


if __name__ == '__main__':
    main()
