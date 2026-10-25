"""Re-score the STORED SoSyM R1 KBs with the standard semantic precision (measurement only).

Measurement for the AAAI-27/SoSyM revision: no re-learning. Every stored fold KB of
``data/results_sosym_r1/{congen,interactive}`` (branch feat/sosym-r1, extracted read-only) is
scored through THIS branch's ``KBComparator(SEMANTIC)`` under two background contracts:

* ``bg_empty`` -- bg = [];
* ``bg_root``  -- bg = ``FMOracle(...).oracle_data.get_root_clauses()``. For all five FMs this
  is ``[[1]]``, identical to the ``bg_clauses`` each SoSyM fold stored and that SoSyM's
  ``run_compare`` passed, so ``bg_root`` IS the as-submitted contract (asserted per fold).

Historical precision P_code = TP_ct/(TP_ct+FP_kb); standard P_std = TP_kb/(TP_kb+FP_kb).
Under ``bg_root`` the code P/R/F1 must reproduce the stored per-fold semantic metrics.
Aggregation is the SoSyM tables' one: mean over folds per (KB, sampling, method). Empty KB:
P_std is undefined ("—", excluded from the P_std mean, ``n_std_defined``) and F1_std = 0
(``SemanticStandardPrecision.f1``), so every fold counts in the F1 means and in the tests.
UNSAT delivered theories (learned ∪ NE ∪ root unsatisfiable) are never scored: corrected
values average the consistent folds and carry ``n_unsat`` / a "(n UNSAT)" note; only the
as-submitted reproduction check averages all folds, as the submitted tables did.

usage: python -m apps.conmin_r1.sosym_r1_precision_check <extracted feat/sosym-r1 tree>
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics as st
from pathlib import Path

from conacq.bias import BiasIO
from conacq.eval.kb_comparator import ComparationStrategy, KBComparator
from conacq.eval.result_loader import ConGenResultData
from conacq.oracle import FMOracle
from conacq.oracle.ground_truth import GroundTruthData

from .theory_consistency import consistent_with_root, unsat_note

KBS = ('REAL-FM-7', 'fqa', 'arcade-game', 'REAL-FM-4', 'busybox-1.18.0')   # KB_1..KB_5
SAMPLINGS = ('rs_1n', 'rs_2n', 'rs_3n', 'rs_m', '2cov', 'ff')
NOT_RUN = {('busybox-1.18.0', 'rs_2n'), ('busybox-1.18.0', 'rs_3n')}
METHODS = ('congen', 'example_only', 'example_first')
CONTRACTS = ('bg_empty', 'bg_root')
COLS = ('P_code', 'P_std', 'R', 'F1_code', 'F1_std')
OUT = Path('data/results_conmin_r1/sosym_r1_precision_check.csv')


def fold_file(tree: Path, kb: str, samp: str, method: str) -> Path:
    r1 = tree / 'data' / 'results_sosym_r1'
    if method == 'congen':
        return r1 / 'congen' / f'{kb}_{samp}_cv_incremental.json'
    return r1 / 'interactive' / f'{kb}_{samp}_cv_incremental_{method}.json'


def score_fold(comp: KBComparator, fold: dict, root: list, mismatches: list, tag: str) -> dict:
    """Both contracts on one stored fold; checks bg_root against the stored metrics."""
    assert [list(c) for c in fold['bg_clauses']] == root, (tag, fold['bg_clauses'], root)
    data = ConGenResultData.from_dict(fold)
    learned = [c for n in data.kb_constraints if comp.bias.has_constraint(n)
               for c in comp.bias.get_clauses(n)]
    out = {'consistent': consistent_with_root(learned, fold['ne_clauses'])}
    for contract in CONTRACTS:
        data.bg_clauses = root if contract == 'bg_root' else []
        res = comp.compare(data, ComparationStrategy.SEMANTIC)
        m, s = res.metrics, res.standard_precision
        out[contract] = {'P_code': m.precision, 'R': m.recall, 'F1_code': m.f1_score,
                         'P_std': s.precision, 'F1_std': s.f1,
                         'n_kb': s.n_kb_checked, 'n_ct': s.n_ct_checked}
    stored = fold['evaluation']['semantic']['metrics']
    for key, col in (('precision', 'P_code'), ('recall', 'R'), ('f1_score', 'F1_code')):
        if abs(stored[key] - out['bg_root'][col]) > 1e-9:
            mismatches.append(f'{tag} {col}: stored {stored[key]:.6f} '
                              f'rescored {out["bg_root"][col]:.6f}')
    return out


def mean(vals):
    vals = [v for v in vals if v is not None]
    return (st.mean(vals) if vals else None), len(vals)


def score_all(tree: Path) -> tuple[dict, list]:
    cells, mismatches = {}, []
    for kb in KBS:
        comp = KBComparator(GroundTruthData.from_uvl(Path(f'data/fms/{kb}.uvl')),
                            BiasIO.load_from_json(f'data/bias/{kb}-bias.json'))
        oracle = FMOracle(f'data/fms/{kb}.uvl', solver_name='glucose4')
        root = [list(c) for c in oracle.oracle_data.get_root_clauses()]
        oracle.cleanup()
        for samp in SAMPLINGS:
            if (kb, samp) in NOT_RUN:
                continue
            for method in METHODS:
                folds = json.loads(fold_file(tree, kb, samp, method).read_text())['folds']
                per = [score_fold(comp, f, root, mismatches, f'{kb}/{samp}/{method}/f{i}')
                       for i, f in enumerate(folds)]
                for contract in CONTRACTS:
                    rows = [p[contract] for p in per]
                    cons = [r for r, p in zip(rows, per) if p['consistent']]
                    agg = {c: mean([r[c] for r in cons])[0] for c in COLS}
                    agg['code_all'] = {c: mean([r[c] for r in rows])[0]
                                       for c in ('P_code', 'R', 'F1_code')}
                    agg['n_unsat'] = len(rows) - len(cons)
                    agg['n_std_defined'] = mean([r['P_std'] for r in cons])[1]
                    agg['n_folds'] = len(rows)
                    agg['n_kb_clauses'] = mean([r['n_kb'] for r in cons])[0]
                    agg['n_ct_clauses'] = st.mean(r['n_ct'] for r in rows)
                    cells[(kb, samp, method, contract)] = agg
                print(kb, samp, method, 'P_code/P_std (bg_root) =',
                      fmt(cells[(kb, samp, method, 'bg_root')]['P_code']),
                      fmt(cells[(kb, samp, method, 'bg_root')]['P_std']), flush=True)
    return cells, mismatches


def _cells(line: str) -> list[str]:
    line = re.sub(r'\\textbf\{([^}]*)\}', r'\1', line.rstrip().rstrip('\\').strip())
    return [c.strip() for c in line.split('&')]


def submitted_values(tree: Path) -> dict:
    """Printed cells of the two semantic fragments, keyed (table, kb, samp, method, qty)."""
    paper = tree / 'data' / 'results_sosym_r1' / 'tables' / 'paper'
    sub = {}
    body = [ln for ln in (paper / 'tab_comparison_strategies.tex').read_text().splitlines()
            if '&' in ln and ln.rstrip().endswith('\\\\')
            and 'F1 by strategy' not in ln and 'Strategy &' not in ln]
    pairs = [(kb, s) for kb in KBS for s in SAMPLINGS]
    for (kb, samp), ln in zip(pairs, body):
        c = _cells(ln)
        if 'n/a' not in ln:
            for qty, v in zip(('F1', 'P', 'R'), c[4:7]):
                sub[('tab_comparison_strategies', kb, samp, 'congen', qty)] = float(v)
    body = [ln for ln in (paper / 'tab_iterative_semantic.tex').read_text().splitlines()
            if ('ConGen' in ln or 'example-' in ln) and '&' in ln]
    keys = [(s, m) for s in SAMPLINGS for m in METHODS]
    for (samp, method), ln in zip(keys, body):
        c, i = _cells(ln), 2
        for kb in KBS:
            if c[i].startswith('\\multicolumn'):
                i += 1
                continue
            sub[('tab_iterative_semantic', kb, samp, method, 'F1')] = float(c[i])
            i += 2
    return sub


def fmt(v, nd=4):
    return '' if v is None else round(v, nd)


def table_rows(cells: dict, sub: dict) -> list[dict]:
    corrected = {'P': 'P_std', 'R': 'R', 'F1': 'F1_std'}
    code = {'P': 'P_code', 'R': 'R', 'F1': 'F1_code'}
    rows = []
    for (table, kb, samp, method, qty), printed in sub.items():
        for contract in CONTRACTS:
            a = cells[(kb, samp, method, contract)]
            new = a[corrected[qty]]
            rows.append({'table': table, 'kb': kb, 'method': method, 'setting': samp,
                         'quantity': qty, 'contract': contract,
                         **{c: fmt(a[c]) for c in COLS},
                         'n_std_defined': f"{a['n_std_defined']}/{a['n_folds']}",
                         'n_unsat': a['n_unsat'], 'note': unsat_note(a['n_unsat']),
                         'n_kb_clauses': fmt(a['n_kb_clauses'], 1),
                         'n_ct_clauses': round(a['n_ct_clauses'], 1),
                         'submitted': printed,
                         'code_reproduces_3dp': round(a['code_all'][code[qty]], 3) == printed,
                         'corrected_3dp': '—' if new is None else round(new, 3),
                         'delta': '' if new is None else round(round(new, 3) - printed, 3)})
    return rows


def significance_medians(cells: dict) -> list[dict]:
    """Median paired differences quoted in the prose, recomputed per F1 variant."""
    out = []
    units = [(kb, s) for kb in KBS for s in SAMPLINGS if (kb, s) not in NOT_RUN]
    for contract in CONTRACTS:
        for col in ('F1_code', 'F1_std'):
            f = {(kb, s, m): cells[(kb, s, m, contract)][col]
                 for kb, s in units for m in METHODS}
            for name, a, b in (('1a congen-eo', 'congen', 'example_only'),
                               ('1b congen-ef', 'congen', 'example_first'),
                               ('5 ef-eo', 'example_first', 'example_only')):
                d = [f[(kb, s, a)] - f[(kb, s, b)] for kb, s in units
                     if f[(kb, s, a)] is not None and f[(kb, s, b)] is not None]
                out.append({'contract': contract, 'variant': col, 'test': name, 'n': len(d),
                            'median': round(st.median(d), 3),
                            'wins': sum(x > 0 for x in d)})
            d2 = []
            for kb in KBS:
                rnd = [f[(kb, s, 'congen')] for s in ('rs_1n', 'rs_2n', 'rs_3n', 'rs_m')
                       if (kb, s) in units]
                if f[(kb, '2cov', 'congen')] is not None:      # all-UNSAT cell: no pair
                    d2.append(f[(kb, '2cov', 'congen')] - st.mean(rnd))
            out.append({'contract': contract, 'variant': col, 'test': '2 2cov-random',
                        'n': len(d2), 'median': round(st.median(d2), 3),
                        'wins': sum(x > 0 for x in d2)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('tree', type=Path, help='root of the extracted feat/sosym-r1 tree')
    args = ap.parse_args()
    cells, mismatches = score_all(args.tree)
    rows = table_rows(cells, submitted_values(args.tree))
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} rows -> {OUT}; per-fold reproduction mismatches: {len(mismatches)}')
    for m in mismatches:
        print('  MISMATCH', m)
    for r in significance_medians(cells):
        print('  median', r)


if __name__ == '__main__':
    main()
