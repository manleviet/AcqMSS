"""Solution-set precision / recall of the delivered theory by exact model counting.

Delivered theory T = learned bias clauses ∪ ¬e⁻ fallbacks ∪ root, exactly as
conmin_slice_scorer.py:67-68 builds it for exact_equiv. Counting is over the FM's feature
variables (every Cτ and bias variable is a feature variable — no auxiliaries, so no
projection is needed):

    sol_precision = #(T ∧ Cτ) / #T        sol_recall = #(T ∧ Cτ) / #Cτ

Consistency check per row: sol_precision = sol_recall = 1 ⇔ T ≡ Cτ ⇔ shipped exact_equiv = 1.

usage: python -m apps.conmin_r1.solution_set_model_counting count KB   (per-KB rows CSV)
       python -m apps.conmin_r1.solution_set_model_counting aggregate  (Table-5 means)
"""
from __future__ import annotations

import csv
import sys
import time
from fractions import Fraction
from pathlib import Path

from conacq.bias import BiasIO
from conacq.oracle.ground_truth import GroundTruthData

from . import KBS, R1_DIR, bias_path, fm_path
from .exact_sdd_model_counter import ExactSddCounter
from .kb_store import delivered_theory, iter_records, table5_key
from .reproduction_gate import KEY, committed_rows
from .table5_aggregation import SWEEP, cell, select_sweep, value


def rows_path(kb: str) -> Path:
    return R1_DIR / 'solution_set' / f'{kb}_rows.csv'


def count_kb(kb: str) -> None:
    gt = GroundTruthData.from_uvl(Path(fm_path(kb)))
    bias = BiasIO.load_from_json(bias_path(kb))
    n = len(gt.feature_map)
    counter = ExactSddCounter(n)
    ct = counter.compile(gt.clauses)
    n_ct = counter.count(ct)
    rows = []
    for rec in iter_records(kb):
        t0 = time.time()
        theory = counter.compile(delivered_theory(rec, bias))
        both = counter.conjoin(theory, ct)
        n_t, n_both = counter.count(theory), counter.count(both)
        theory.deref()
        both.deref()
        p = Fraction(n_both, n_t) if n_t else None
        r = Fraction(n_both, n_ct)
        equiv = int(p == 1 and r == 1)
        assert equiv == int(rec['shipped']['exact_equiv']), (kb, table5_key(rec), p, r)
        rows.append({'kb': kb, 'example_set': rec['example_set'], 'fold': str(rec['fold']),
                     **table5_key(rec), 'n_vars': n, 'models_theory': n_t,
                     'models_target': n_ct, 'models_both': n_both,
                     'sol_precision': '' if p is None else float(p), 'sol_recall': float(r),
                     'exact_equiv': equiv, 'seconds': round(time.time() - t0, 3)})
    path = rows_path(kb)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'{kb}: {len(rows)} theories counted, #Cτ = {n_ct} over {n} vars, '
          f'{sum(r["seconds"] for r in rows):.1f}s')


def aggregate() -> None:
    committed = committed_rows()
    out = []
    for kb in KBS:
        path = rows_path(kb)
        if not path.exists():
            continue
        with open(path) as f:
            rows = list(csv.DictReader(f))
        for r in rows:                      # submitted convergence (dagger) semantics
            r['convergence_reason'] = committed[tuple(r[k] for k in KEY)]['convergence_reason']
        for label in SWEEP:
            sel = select_sweep(rows, label)
            if not sel:
                continue
            p, rc, eq = (cell(sel, c) for c in ('sol_precision', 'sol_recall', 'exact_equiv'))
            out.append({'kb': kb, 'strategy': label, 'n_folds': len(sel),
                        'nonconverged': int(p.nonconverged), 'sol_precision': value(p, None),
                        'sol_recall': value(rc, None), 'exact_equiv_rate': value(eq),
                        'sol_precision_n_defined': p.n,
                        'seconds_total': round(sum(float(r['seconds']) for r in sel), 1)})
    with open(R1_DIR / 'solution_set_pr.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    for o in out:
        g = lambda x: '--' if x == '' else f'{x:.3g}'
        print(f"{o['kb']:12s} {o['strategy']:13s} solP {g(o['sol_precision']):<9} "
              f"solR {g(o['sol_recall']):<9} eq {o['exact_equiv_rate']}"
              f"{' †' if o['nonconverged'] else ''}")


if __name__ == '__main__':
    if sys.argv[1] == 'count':
        count_kb(sys.argv[2])
    else:
        aggregate()
