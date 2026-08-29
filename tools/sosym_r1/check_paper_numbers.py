#!/usr/bin/env python3
"""Reproduce, and ASSERT, every number the SoSyM revision notes quote.

Why this file exists
--------------------
The checking layer was the one layer leaving no audit trail. CC's measurements
live in committed scripts; CW's counter-measurements were ad-hoc snippets typed
into a chat, and the numbers they produced went straight into `~SoSyM revision.md`
and the paper drafts. Several of those numbers are load-bearing:

  * |Cτ| = 130 for arcade-game is the hand count that decided the ground-truth
    question. The whole "four of five models were scored against fqa's Cτ"
    disclosure rests on it.
  * 74.62 %, 18/28, 1/84 and the 29-80 % agreement range are quoted in the paper.

A number in a note that nobody can recompute cannot be re-checked, only
re-asserted. This project already adopted the rule ("scratch is local, evidence
is committed"; "you may call something scratch only if you can name what
reconstructs it") and this file is CW complying with it.

It ASSERTS rather than prints, so it doubles as a regression test: if a future
re-run moves a number that reached the paper, this fails loudly instead of
letting the paper and the data drift apart silently.

Run:  PYTHONPATH=. python3 tools/sosym_r1/check_paper_numbers.py
Exit: 0 = every number in the notes still holds. 1 = at least one moved.
"""
from __future__ import annotations

import glob
import json
import os
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
R1 = REPO / 'data' / 'results_sosym_r1' / 'congen'
OLD = REPO / 'data' / 'results' / 'congen'
OLD_INT = REPO / 'data' / 'results' / 'interactive'
FMS = REPO / 'data' / 'fms'

TOL = 5e-3  # numbers are quoted to 3-4 significant figures in the notes

failures: list[str] = []
checks = 0


def check(name: str, got, want, tol: float | None = None) -> None:
    """Assert one quoted number. Records rather than raises, so one run reports all drift."""
    global checks
    checks += 1
    ok = (abs(got - want) <= (TOL if tol is None else tol)) if isinstance(want, float) else (got == want)
    status = 'ok  ' if ok else 'FAIL'
    print(f'  [{status}] {name}: got {got!r}, notes say {want!r}')
    if not ok:
        failures.append(name)


def semantic(fold: dict) -> dict:
    """The semantic metrics block.

    NOTE the nesting: evaluation.semantic.METRICS.recall. Reading one level
    shallower returns a .get() default of 0 on every fold, which is exactly how
    CW came to report "the P/R do not exist anywhere in the repository" on
    2026-08-28. A missing key and a zero value are different facts.
    """
    return ((fold.get('evaluation') or {}).get('semantic') or {}).get('metrics') or {}


def folds_of(pattern: str, root: Path):
    for f in sorted(glob.glob(str(root / pattern))):
        if '/partials/' in f:
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for fo in d.get('folds', []) or []:
            yield os.path.basename(f), d, fo


# ---------------------------------------------------------------------------
# 1. |Cτ| counted from the feature model alone, never from a result file.
#    This is the hand count that settled which value was correct.
# ---------------------------------------------------------------------------
def count_ctau_from_uvl(path: Path) -> int:
    """Standard FM->CNF clause count.

    root unit                     1
    mandatory child   c <-> p     2 each
    optional  child   c  -> p     1 each
    group     child   c  -> p     1 each
    group             p  -> Vci   1 per or/alternative group
    ALTERNATIVE group !ci v !cj   C(n,2) per group  <-- see below
    cross-tree                    1 each

    The pairwise-exclusion term is the one CW's first hand count omitted. It
    settled the ground-truth question on arcade-game and was believed general.
    arcade-game and REAL-FM-4 have ZERO alternative groups, so the missing term
    never fired on either model it was tested against; fqa (23 groups) was short
    by 85 clauses and busybox (8 groups) by 23. With the term restored all five
    models reproduce exactly, with no residual.

    The lesson is the one CW had already written to CC and not applied to
    itself: alternative groups are the encoding path most likely to be wrong,
    and the model used to validate the count could not exercise it.
    """
    lines = path.read_text().split('\n')
    ci = [i for i, l in enumerate(lines) if l.strip() == 'constraints']
    fsec = lines[:ci[0]] if ci else lines
    csec = lines[ci[0] + 1:] if ci else []

    def indent(l: str) -> int:
        return len(l) - len(l.lstrip('\t'))

    edges: list[tuple[str, str | None, str]] = []
    groups: dict[tuple[str | None, str], list[str]] = {}
    cur_parent: list[tuple[int, str]] = []
    pending: list[tuple[int, str, str | None]] = []
    for l in fsec:
        if not l.strip():
            continue
        s, ind = l.strip(), indent(l)
        tok = s.split()[0].rstrip('{')
        if tok in ('namespace', 'features'):
            continue
        while cur_parent and cur_parent[-1][0] >= ind:
            cur_parent.pop()
        while pending and pending[-1][0] >= ind:
            pending.pop()
        if tok in ('mandatory', 'optional', 'or', 'alternative'):
            pending.append((ind, tok, cur_parent[-1][1] if cur_parent else None))
            continue
        if pending:
            gi, kind, par = pending[-1]
            edges.append((tok, par, kind))
            groups.setdefault((par, kind), []).append(tok)
        cur_parent.append((ind, tok))

    n_mand = sum(1 for e in edges if e[2] == 'mandatory')
    n_opt = sum(1 for e in edges if e[2] == 'optional')
    n_grp_child = sum(1 for e in edges if e[2] in ('or', 'alternative'))
    n_groups = sum(1 for k in groups if k[1] in ('or', 'alternative'))
    n_ctc = len([l for l in csec if l.strip()])
    n_pairwise = sum(len(v) * (len(v) - 1) // 2
                     for k, v in groups.items() if k[1] == 'alternative')
    return 1 + 2 * n_mand + n_opt + n_grp_child + n_ctc + n_groups + n_pairwise


EXPECTED_CTAU = {
    'REAL-FM-7': 22,
    'arcade-game': 130,
    'fqa': 342,
    'REAL-FM-4': 428,
    'busybox-1.18.0': 994,
}

print('\n1. |Ctau| hand-counted from data/fms/*.uvl (settles the ground-truth question)')
for model, want in EXPECTED_CTAU.items():
    uvl = FMS / f'{model}.uvl'
    if not uvl.exists():
        print(f'  [skip] {model}: {uvl} absent')
        continue
    check(f'|Ctau| {model} from UVL', count_ctau_from_uvl(uvl), want)

print('\n2. the same |Ctau| appears as tp+fn in the corrected results')
seen: dict[str, set[int]] = {}
for base, _d, fo in folds_of('*.json', R1):
    sm = semantic(fo)
    if not sm:
        continue
    seen.setdefault(base.split('_')[0], set()).add(
        sm.get('true_positives', 0) + sm.get('false_negatives', 0))
for model, want in EXPECTED_CTAU.items():
    if model in seen:
        check(f'|Ctau| {model} == tp+fn, single-valued', sorted(seen[model]), [want])

# ---------------------------------------------------------------------------
# 3. The defect's signature: every OLD file reports fqa's |Ctau| = 342.
#    This is the evidence behind the N item, so it must stay reproducible.
# ---------------------------------------------------------------------------
print('\n3. the defect signature in the published run (evidence for the N item)')
old_vals: list[int] = []
for base, _d, fo in folds_of('*.json', OLD):
    sm = semantic(fo)
    if sm:
        old_vals.append(sm.get('true_positives', 0) + sm.get('false_negatives', 0))
if old_vals:
    check('old congen: every fold scored against 342', sorted(set(old_vals)), [342])
old_int = [semantic(fo).get('true_positives', 0) + semantic(fo).get('false_negatives', 0)
           for _b, _d, fo in folds_of('**/*.json', OLD_INT) if semantic(fo)]
if old_int:
    check('old interactive: same', sorted(set(old_int)), [342])
    check('old interactive: fold count', len(old_int), 108)

# ---------------------------------------------------------------------------
# 4. Numbers quoted in A5 / B7 / B20.
# ---------------------------------------------------------------------------
print('\n4. numbers quoted in the drafts')

cells: dict[str, list[float]] = {}
eq_hits: list[tuple[str, int]] = []
eq_scored = 0
pos_frac: list[float] = []
pooled_p = pooled_n = 0
acc_mismatch = 0
acc_folds = 0
for base, _d, fo in folds_of('*.json', R1):
    sm = semantic(fo)
    if sm:
        cells.setdefault(base, []).append(sm.get('recall', 0.0))
    ev = fo.get('evaluation') or {}
    if ev.get('exact_equiv') is not None:
        eq_scored += 1
        if ev['exact_equiv'] in (1, True):
            eq_hits.append((base, fo.get('fold_index')))
    ts = fo.get('test_size') or {}
    if ts:
        tot = ts.get('positive', 0) + ts.get('negative', 0)
        if tot:
            pos_frac.append(ts['positive'] / tot)
            pooled_p += ts['positive']
            pooled_n += ts['negative']
    m = fo.get('metrics') or {}
    if m and ts:
        acc_folds += 1
        n = (m.get('true_positives', 0) + m.get('true_negatives', 0)
             + m.get('false_positives', 0) + m.get('false_negatives', 0))
        if n != (ts.get('positive', 0) + ts.get('negative', 0)):
            acc_mismatch += 1

saturated = sum(1 for v in cells.values() if abs(statistics.mean(v) - 1.0) < 1e-9)
check('cells with semantic recall exactly 1.0', saturated, 18)
check('cells scored', len(cells), 28)

check('exact equivalence: folds scored', eq_scored, 84)
check('exact equivalence: attained', len(eq_hits), 1)
if eq_hits:
    check('exact equivalence: on the smallest model', eq_hits[0][0].startswith('REAL-FM-7_rs_3n'), True)
    check('   ... and |Ctau| there is the smallest of the five',
          min(EXPECTED_CTAU.values()), EXPECTED_CTAU['REAL-FM-7'])

# The trivial-baseline reference. Pooled and per-fold-mean differ by ~15 points,
# and only the per-fold mean is comparable with how the paper computes accuracy.
check('accept-everything baseline, PER-FOLD MEAN (the comparable one)',
      statistics.mean(pos_frac) * 100, 74.62, tol=0.05)
check('accept-everything baseline, pooled (reference only, NOT comparable)',
      pooled_p / (pooled_p + pooled_n) * 100, 89.41, tol=0.05)

# Accuracy was written by the CV run, not by the scoring pass that carried the
# ground-truth defect. If these ever stop matching, that premise is broken.
check('accuracy folds internally consistent with their own test split', acc_mismatch, 0)
check('   ... folds checked', acc_folds > 80, True)

# ---------------------------------------------------------------------------
# 5. Fold agreement, reported as a STABILITY statistic and never as a score.
# ---------------------------------------------------------------------------
print('\n5. fold-agreement range (stability statistic, not a quality score)')
agree: dict[str, float] = {}
for f in sorted(glob.glob(str(R1 / '*.json'))):
    d = json.load(open(f))
    kbs = [set(map(str, fo.get('kb_constraints', []))) for fo in d.get('folds', [])]
    if not kbs or not all(kbs):
        continue
    inter = set.intersection(*kbs)
    mean_size = statistics.mean(len(k) for k in kbs)
    if mean_size:
        agree[os.path.basename(f)] = len(inter) / mean_size * 100
if agree:
    lo_name = min(agree, key=lambda k: agree[k])
    hi_name = max(agree, key=lambda k: agree[k])
    print(f'  lowest  {lo_name}: {agree[lo_name]:.1f}%')
    print(f'  highest {hi_name}: {agree[hi_name]:.1f}%')
    check('arcade rs_1n agreement ~29%', agree.get('arcade-game_rs_1n_cv_incremental.json', -1), 28.9, tol=1.0)
    check('fqa rs_1n agreement ~80%', agree.get('fqa_rs_1n_cv_incremental.json', -1), 79.6, tol=1.0)

# ---------------------------------------------------------------------------
# 6. The aggregation convention. Decided 2026-08-29: per-fold mean, not the
#    intersected KB. The published .525 is the regression target.
# ---------------------------------------------------------------------------
print('\n6. aggregation convention: per-fold mean is what the paper reports')
p = OLD / 'arcade-game_rs_1n_cv_incremental.json'
if p.exists():
    d = json.load(open(p))
    per = [semantic(fo).get('f1_score') for fo in d['folds'] if semantic(fo)]
    inter = (((d.get('intersected_kb') or {}).get('evaluation') or {})
             .get('semantic') or {}).get('metrics', {}).get('f1_score')
    summ = ((d.get('summary') or {}).get('semantic') or {}).get('f1_score', {}).get('mean')
    check('published .525 == per-fold mean', round(statistics.mean(per), 6), 0.524859, tol=1e-6)
    check('published .525 == summary.mean', summ, 0.524859, tol=1e-6)
    check('intersected KB is a DIFFERENT number', round(inter, 6), 0.443966, tol=1e-6)

# ---------------------------------------------------------------------------
# 7. The 2-COV applicability threshold quoted in B20 / A5.
# ---------------------------------------------------------------------------
print('\n7. the 2-COV boundary: passive acquisition has no positive examples to work with')
tr_zero = tr_tot = te_zero = 0
max_pos = 0
for base, _d, fo in folds_of('*2cov*.json', R1):
    tr = fo.get('train_size') or {}
    te = fo.get('test_size') or {}
    if not tr:
        continue
    tr_tot += 1
    max_pos = max(max_pos, tr.get('positive', 0))
    if tr.get('positive', 0) == 0:
        tr_zero += 1
    if te.get('positive', 0) == 0:
        te_zero += 1
check('2-COV folds', tr_tot, 15)
check('2-COV folds with |E+| == 0 in training', tr_zero, 11)
check('2-COV max |E+| over all folds', max_pos, 1)
check('2-COV folds with no positive TEST example', te_zero, 13)

# ---------------------------------------------------------------------------
print(f'\n{"=" * 70}')
if failures:
    print(f'FAIL: {len(failures)} of {checks} numbers no longer match the notes:')
    for f in failures:
        print(f'  - {f}')
    print('\nA number that moved is a finding. Update the notes to the measurement,')
    print('never the assertion to the number you hoped for.')
    sys.exit(1)
print(f'OK: all {checks} numbers quoted in the SoSyM notes reproduce from the data.')
sys.exit(0)
