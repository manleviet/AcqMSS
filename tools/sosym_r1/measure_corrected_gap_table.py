#!/usr/bin/env python
"""The ConGen-minus-iterative gap, per cell, with both trees named.

The gap is what the paper claims, so the gap is what this reports -- not two columns
a reader has to subtract. Every number carries the tree it came from, because the
defect this replaces was not a wrong value but a PAIRING: a corrected ConGen column
set beside an uncorrected iterative one, which matches no tree and cannot be
reproduced from the repo.

    OLD = data/results               -- the tree the published tables were computed from
    NEW = data/results_sosym_r1      -- re-scored ConGen (9162802) + re-scored
                                        interactive, each fold against its own oracle

MODE COLLAPSE. In OLD, many cells carry the identical iterative F1 under example_only
and example_first -- arcade rs_3n is 0.0382 under both. That is the extractor having
lost its method axis (fixed at 2157122), not a finding about the two modes. Those
cells are marked: the published active-vs-passive comparison there was uninformative
rather than merely mis-scored, and the distinction matters when deciding what a
corrected number overturns.

QUERIES. ConGen issues no oracle queries -- it is passive, and its folds record no
n_queries at all. The baseline's count is read per fold and averaged. The query axis
belongs beside the F1s because it is the axis the surviving claim rests on: an equal
F1 bought with 1,000 queries is not an equal result.

    measure_corrected_gap_table.py                 # every cell in both trees
    measure_corrected_gap_table.py --tree new      # the corrected table alone
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TREES = {'old': REPO / 'data' / 'results', 'new': REPO / 'data' / 'results_sosym_r1'}
STEMS = ['REAL-FM-4', 'REAL-FM-7', 'arcade-game', 'busybox-1.18.0', 'fqa']
SAMPLINGS = ['rs_1n', 'rs_2n', 'rs_3n', 'rs_m', '2cov', 'ff']
MODES = ['example_only', 'example_first']


def semantic(fold: dict) -> dict:
    """evaluation.semantic.metrics -- one level up holds the strategy label, not numbers."""
    return ((fold.get('evaluation') or {}).get('semantic') or {}).get('metrics') or {}


def fold_mean(path: Path, key: str = 'f1_score'):
    """A cell is the mean over folds. Never the intersected KB, never a pooled figure."""
    if not path.exists():
        return None
    folds = json.loads(path.read_text())['folds']
    vals = [semantic(f).get(key) for f in folds if semantic(f)]
    return st.mean(vals) if vals else None


def queries_of(path: Path):
    """Mean oracle queries per fold, and the stopping rules observed."""
    if not path.exists():
        return None, set()
    folds = json.loads(path.read_text())['folds']
    n = [f.get('n_queries') for f in folds if f.get('n_queries') is not None]
    return (st.mean(n) if n else None), {f.get('convergence_reason') for f in folds}


def cell(tree: Path, stem: str, samp: str, mode: str) -> dict | None:
    cg = fold_mean(tree / 'congen' / f'{stem}_{samp}_cv_incremental.json')
    it_path = tree / 'interactive' / f'{stem}_{samp}_cv_incremental_{mode}.json'
    it = fold_mean(it_path)
    if cg is None or it is None:
        return None
    nq, stops = queries_of(it_path)
    return {'congen': cg, 'iterative': it, 'gap': cg - it, 'queries': nq, 'stops': stops}


def collapsed(tree: Path, stem: str, samp: str) -> bool:
    """Identical iterative F1 under both modes: the lost-method-axis signature."""
    a = fold_mean(tree / 'interactive' / f'{stem}_{samp}_cv_incremental_example_only.json')
    b = fold_mean(tree / 'interactive' / f'{stem}_{samp}_cv_incremental_example_first.json')
    return a is not None and b is not None and abs(a - b) < 1e-12


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tree', choices=['old', 'new', 'both'], default='both')
    args = ap.parse_args()

    trees = ['old', 'new'] if args.tree == 'both' else [args.tree]
    print(f"semantic F1, mean over folds. gap = ConGen - iterative. "
          f"ConGen issues 0 oracle queries.\n")
    for name in trees:
        print(f"{'='*96}\n{name.upper()} = {TREES[name].relative_to(REPO)}\n{'='*96}")
        print(f"{'cell':26s} {'mode':6s} {'ConGen':>7s} {'iter':>7s} {'gap':>8s} "
              f"{'iter q':>8s}  stop")
        for stem in STEMS:
            for samp in SAMPLINGS:
                mark = '  [mode-collapsed]' if collapsed(TREES[name], stem, samp) else ''
                for mode in MODES:
                    c = cell(TREES[name], stem, samp, mode)
                    if c is None:
                        continue
                    q = f"{c['queries']:8.0f}" if c['queries'] is not None else '       -'
                    stops = ','.join(sorted(s for s in c['stops'] if s)) or '-'
                    print(f"{stem+' '+samp:26s} {mode[8:]:6s} {c['congen']:7.4f} "
                          f"{c['iterative']:7.4f} {c['gap']:+8.4f} {q}  {stops}{mark}")
                    mark = ''
        print()

    # Where does the baseline win, and does it win with a fixed pool or only with an oracle?
    tree = TREES['new']
    both, first_only = [], []
    for stem in STEMS:
        for samp in SAMPLINGS:
            cs = {m: cell(tree, stem, samp, m) for m in MODES}
            if any(v is None for v in cs.values()):
                continue
            wins = [m for m in MODES if cs[m]['gap'] < 0]
            if len(wins) == 2:
                both.append((stem, samp, cs))
            elif wins == ['example_first']:
                first_only.append((stem, samp, cs))

    print(f"{'='*96}\nWHERE THE BASELINE WINS, in NEW\n{'='*96}")
    print(f"both modes: {len(both)} cells")
    for stem, samp, cs in both:
        print(f"  {stem} {samp}: only {cs['example_only']['gap']:+.4f}, "
              f"first {cs['example_first']['gap']:+.4f}")
    print(f"example-first only (needs an oracle to win): {len(first_only)} cells")
    for stem, samp, cs in first_only:
        print(f"  {stem} {samp}: only {cs['example_only']['gap']:+.4f} "
              f"({cs['example_only']['queries']:.0f} q), first "
              f"{cs['example_first']['gap']:+.4f} ({cs['example_first']['queries']:.0f} q)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
