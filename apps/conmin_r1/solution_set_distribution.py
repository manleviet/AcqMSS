"""Per-fold distribution of the solution-set ratios, several summaries side by side.

The ratios span tens of orders of magnitude, so no single summary is chosen here: for every
KB × strategy (Table-5 selection + C∪S k-sweep; non-converged folds excluded unless all are,
as cv_mean) this reports n, mean, median, geometric mean, min, quartiles and max of
sol_precision and sol_recall. Zeros and undefined values are counted, not hidden: an UNSAT
delivered theory has #T = 0, so sol_precision is undefined; the geometric mean runs over the
strictly positive folds only (``n_positive``). A log-scale strip plot shows every fold.

usage: python -m apps.conmin_r1.solution_set_distribution
"""
from __future__ import annotations

import csv
import math
import statistics as st

from apps.make_tables.aggregate import NONCONVERGED_REASONS

from . import KBS, R1_DIR
from .reproduction_gate import KEY, committed_rows
from .solution_set_model_counting import rows_path
from .table5_aggregation import SWEEP, select_sweep

MEASURES = ('sol_precision', 'sol_recall')
FLOOR = 1e-40          # where zeros are drawn on the log axis (marked, never averaged)


def _quartiles(xs):
    if len(xs) < 2:
        return xs[0], xs[0]
    q = st.quantiles(xs, n=4, method='inclusive')
    return q[0], q[2]


def summarise(vals):
    defined = [v for v in vals if v is not None]
    pos = [v for v in defined if v > 0]
    out = {'n': len(vals), 'n_undefined': len(vals) - len(defined),
           'n_zero': len(defined) - len(pos), 'n_positive': len(pos)}
    if defined:
        q1, q3 = _quartiles(sorted(defined))
        out.update(mean=st.mean(defined), median=st.median(defined), min=min(defined),
                   q1=q1, q3=q3, max=max(defined))
    out['geomean_positive'] = math.exp(st.mean(math.log(v) for v in pos)) if pos else ''
    return out


def load(kb, committed):
    with open(rows_path(kb)) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r['convergence_reason'] = committed[tuple(r[k] for k in KEY)]['convergence_reason']
        for m in MEASURES:
            r[m] = None if r[m] == '' else float(r[m])
    return rows


def main():
    committed = committed_rows()
    out, per_kb = [], {}
    for kb in KBS:
        rows = load(kb, committed)
        for label in SWEEP:
            sel = select_sweep(rows, label)
            sel = [r for r in sel if r['convergence_reason'] not in NONCONVERGED_REASONS] or sel
            for m in MEASURES:
                s = summarise([r[m] for r in sel])
                out.append({'kb': kb, 'strategy': label, 'measure': m, **s})
                per_kb.setdefault(kb, {}).setdefault(m, {})[label] = [r[m] for r in sel]
    keys = ['kb', 'strategy', 'measure', 'n', 'n_undefined', 'n_zero', 'n_positive', 'mean',
            'median', 'geomean_positive', 'min', 'q1', 'q3', 'max']
    with open(R1_DIR / 'solution_set_distribution.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out)
    plot(per_kb)
    g = lambda x: '—' if x in ('', None) else f'{x:.3g}'
    for o in out:
        print(f"{o['kb']:12s} {o['strategy']:13s} {o['measure']:13s} mean {g(o.get('mean'))} "
              f"median {g(o.get('median'))} gm+ {g(o['geomean_positive'])} "
              f"[{g(o.get('min'))}, {g(o.get('q1'))}, {g(o.get('q3'))}, {g(o.get('max'))}] "
              f"zero {o['n_zero']} undef {o['n_undefined']}")


def plot(per_kb):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    labels = list(SWEEP)
    fig, axes = plt.subplots(len(MEASURES), len(per_kb), figsize=(4.2 * len(per_kb), 7),
                             sharey=True)
    for j, kb in enumerate(per_kb):
        for i, m in enumerate(MEASURES):
            ax = axes[i][j]
            for x, label in enumerate(labels):
                vals = [v for v in per_kb[kb][m].get(label, []) if v is not None]
                ys = [max(v, FLOOR) for v in vals]
                ax.scatter([x] * len(ys), ys, s=10, alpha=.6,
                           c=['tab:red' if v == 0 else 'tab:blue' for v in vals])
            ax.set_yscale('log')
            ax.set_ylim(FLOOR / 10, 2)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=60, fontsize=7)
            ax.set_title(f'{kb} — {m}', fontsize=9)
    axes[0][0].set_ylabel('per-fold ratio (log)')
    fig.text(.01, .01, f'red = 0 (drawn at {FLOOR:g}); UNSAT theories have undefined '
             'sol_precision and are not drawn', fontsize=7)
    fig.tight_layout()
    path = R1_DIR / 'figures' / 'solution_set_log_scale.png'
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)


if __name__ == '__main__':
    main()
