"""Analytic bounds on the corrected semantic tier from the committed rows only, for KBs whose
learned KBs are not persisted (busybox: re-runs deferred, see busybox_rerun.md).

Per committed row (N = |Cτ clauses|, R+ = Cτ clauses containing +root — all entailed by root
alone; MAXCL = max clauses per bias constraint; |KB| = size in constraints):
- TP_ct = sem_r·N. FP_kb (bg-independent) = TP_ct(1−P)/P when TP_ct > 0; else unknown.
- bg = []  : code P/R/F1 exact (as submitted).
- bg = root: TP_ct ∈ [max(TP_ct, |R+|), N] → R, code P, F1 non-decreasing.
- P_std = (n − FP_kb)/n with n = |KB clauses| ∈ [max(|KB|, FP_kb), |KB|·MAXCL]; P_std ∈ [0, 1]
  when FP_kb is unknown; undefined on an empty KB. Identical under both contracts.
Means: make_tables' select, non-converged folds excluded unless all are (cv_mean semantics).

usage: python -m apps.conmin_r1.semantic_root_bounds_from_committed [KB]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from apps.make_tables.aggregate import NONCONVERGED_REASONS
from apps.make_tables.filters import STRATEGIES, select
from conacq.bias import BiasIO
from conacq.oracle.ground_truth import GroundTruthData

from . import COMMITTED_LONG_CSV, R1_DIR, bias_path, fm_path


def _f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0


def _code(tp, fp, n_ct):
    p = tp / (tp + fp) if tp + fp else 0.0
    return p, tp / n_ct, _f1(p, tp / n_ct)


def row_bounds(r, n_ct, rplus, maxcl):
    p, rc, size = float(r['sem_p']), float(r['sem_r']), int(float(r['size']))
    tp = round(rc * n_ct)
    fp = round(tp * (1 - p) / p) if tp > 0 else None
    fp_lo, fp_hi = (fp, fp) if fp is not None else (0, size * maxcl)
    if size == 0:
        std = (None, None)
    elif fp is None:
        std = (0.0, 1.0)
    else:
        n_lo, n_hi = max(size, fp), size * maxcl
        std = ((n_lo - fp) / n_lo, (n_hi - fp) / n_hi)
    lo, hi = _code(max(tp, rplus), fp_hi, n_ct), _code(n_ct, fp_lo, n_ct)
    return {'old': (p, rc, float(r['sem_f1'])), 'root_lo': lo, 'root_hi': hi, 'std': std,
            'f1_std_empty': (None if std[0] is None else (_f1(std[0], rc), _f1(std[1], rc))),
            'f1_std_root': (None if std[0] is None else (_f1(std[0], lo[1]), _f1(std[1], 1.0)))}


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else ''


def main():
    kb = sys.argv[1] if len(sys.argv) > 1 else 'busybox-1.18.0'
    gt = GroundTruthData.from_uvl(Path(fm_path(kb)))
    n_ct = len(gt.clauses)
    rplus = sum(1 for c in gt.clauses if 1 in c)                 # root variable = 1
    maxcl = max(len(v) for v in BiasIO.load_from_json(bias_path(kb)).to_constraint_map().values())
    with open(COMMITTED_LONG_CSV) as f:
        rows = [r for r in csv.DictReader(f) if r['kb'] == kb]
    out = []
    for s in STRATEGIES:
        sel = select(rows, s)
        conv = [r for r in sel if r['convergence_reason'] not in NONCONVERGED_REASONS] or sel
        b = [row_bounds(r, n_ct, rplus, maxcl) for r in conv]
        get = lambda key, i: _mean([x[key][i] for x in b])
        for contract, lo_key, hi_key, f1s in (('bg_empty', 'old', 'old', 'f1_std_empty'),
                                              ('bg_root', 'root_lo', 'root_hi', 'f1_std_root')):
            out.append({
                'kb': kb, 'strategy': s, 'contract': contract, 'n_folds': len(conv),
                'nonconverged': int(len(conv) == len(sel) and
                                    sel[0]['convergence_reason'] in NONCONVERGED_REASONS),
                'P_code_lo': get(lo_key, 0), 'P_code_hi': get(hi_key, 0),
                'R_lo': get(lo_key, 1), 'R_hi': get(hi_key, 1),
                'F1_code_lo': get(lo_key, 2), 'F1_code_hi': get(hi_key, 2),
                'P_std_lo': _mean([x['std'][0] for x in b]),
                'P_std_hi': _mean([x['std'][1] for x in b]),
                'F1_std_lo': _mean([None if x[f1s] is None else x[f1s][0] for x in b]),
                'F1_std_hi': _mean([None if x[f1s] is None else x[f1s][1] for x in b]),
                'n_ct_clauses': n_ct, 'r_plus': rplus, 'max_clauses_per_constraint': maxcl})
    path = R1_DIR / f'semantic_bounds_{kb}.csv'
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for o in out:
        print(f"{o['strategy']:13s} {o['contract']:8s} P_code [{o['P_code_lo']}, {o['P_code_hi']}] "
              f"R [{o['R_lo']}, {o['R_hi']}] F1_code [{o['F1_code_lo']}, {o['F1_code_hi']}] "
              f"P_std [{o['P_std_lo']}, {o['P_std_hi']}] F1_std [{o['F1_std_lo']}, {o['F1_std_hi']}]")


if __name__ == '__main__':
    main()
