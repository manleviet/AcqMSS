"""CORRECTIONS of the semantic tier, scored through the production comparator path.

Two defects of the submitted semantic tier (description, clause, exact_equiv, accuracy are
unaffected):
1. Premise: every KB was scored with bg = [] (conmin_slice_scorer.py:59 → kb_comparator.py:298),
   so Cτ clauses that need the root axiom (root unit, child → root) counted as missed.
2. Formula: precision = TP_ct / (TP_ct + FP_kb) (kb_comparator.py:350-354 + metrics.py:48-57)
   mixes Cτ-clause and KB-clause populations; standard P_std = TP_kb / (TP_kb + FP_kb).

Per persisted KB, ``KBComparator.compare(SEMANTIC)`` runs under both contracts
(bg = [] as submitted; bg = root as corrected). Its ``metrics`` give the code's P/R/F1 and its
``standard_precision`` gives P_std/F1_std from the same entailment call. The bg = [] code
numbers must equal the shipped sem_p/r/f1 (asserted). Empty KB: P_std/F1_std undefined, the
fold is excluded from that mean (``*_n_defined`` reports how many folds remain).

Writes ``semantic_precision_formulas.csv`` (kb × strategy × contract, Table-5 aggregation),
``semantic_tier_corrected.csv`` (submitted vs corrected, the headline view) and
``semantic_tier_corrected_rows.csv`` (per fold).

usage: python -m apps.conmin_r1.semantic_tier_corrected
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from conacq.bias import BiasIO
from conacq.eval.kb_comparator import ComparationStrategy, KBComparator
from conacq.eval.result_loader import ConGenResultData
from conacq.oracle.ground_truth import GroundTruthData

from . import KBS, R1_DIR, bias_path, fm_path
from .kb_store import iter_records, table5_key
from .reproduction_gate import KEY, committed_rows
from .table5_aggregation import SWEEP, cell, select_sweep, value

CONTRACTS = ('bg_empty', 'bg_root')


@lru_cache(maxsize=None)
def _comparator(kb):
    return KBComparator(GroundTruthData.from_uvl(Path(fm_path(kb))),
                        BiasIO.load_from_json(bias_path(kb)))


def score_record(rec: dict) -> dict:
    comp = _comparator(rec['kb'])
    row = {'kb': rec['kb'], 'example_set': rec['example_set'], 'fold': str(rec['fold']),
           **table5_key(rec)}
    for contract in CONTRACTS:
        bg = rec['root_clauses'] if contract == 'bg_root' else []
        res = comp.compare(ConGenResultData(kb_constraints=rec['names'], n_bias=0,
                                            n_kb=len(rec['names']), bg_clauses=bg),
                           ComparationStrategy.SEMANTIC)
        m, std = res.metrics, res.standard_precision
        row.update({f'P_code_{contract}': m.precision, f'R_{contract}': m.recall,
                    f'F1_code_{contract}': m.f1_score,
                    f'P_std_{contract}': '' if std.precision is None else std.precision,
                    f'F1_std_{contract}': '' if std.f1 is None else std.f1})
        row['n_kb_clauses'], row['n_ct_clauses'] = std.n_kb_checked, std.n_ct_checked
    for m, col in (('p', 'P_code'), ('r', 'R'), ('f1', 'F1_code')):
        assert abs(row[f'{col}_bg_empty'] - rec['shipped'][f'sem_{m}']) < 1e-9, (row, m)
    return row


def _write(name, rows):
    with open(R1_DIR / name, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    committed = committed_rows()
    rows = []
    for rec in iter_records():
        row = score_record(rec)
        row['convergence_reason'] = committed[tuple(row[k] for k in KEY)]['convergence_reason']
        rows.append(row)
    _write('semantic_tier_corrected_rows.csv', rows)

    formulas, headline = [], []
    for kb in KBS:
        kb_rows = [r for r in rows if r['kb'] == kb]
        kb_committed = [c for c in committed.values() if c['kb'] == kb]
        for label in SWEEP:
            sel = select_sweep(kb_rows, label)
            if not sel:
                continue
            flt = SWEEP[label]
            base = {'kb': kb, 'strategy': label, 'condition': flt.condition, 'k': flt.k,
                    'n_folds': len(sel)}
            for contract in CONTRACTS:
                c = {col: cell(sel, f'{col}_{contract}')
                     for col in ('P_code', 'P_std', 'R', 'F1_code', 'F1_std')}
                formulas.append({**base, 'contract': contract,
                                 'nonconverged': int(c['R'].nonconverged),
                                 **{col: value(st) for col, st in c.items()},
                                 'P_std_n_defined': c['P_std'].n,
                                 'n_kb_clauses': value(cell(sel, 'n_kb_clauses'), 1),
                                 'n_ct_clauses': value(cell(sel, 'n_ct_clauses'), 1)})
            sub = select_sweep(kb_committed, label)
            s = {m: cell(sub, f'sem_{m}') for m in ('p', 'r', 'f1')}
            cor = {'p': cell(sel, 'P_code_bg_root'), 'r': cell(sel, 'R_bg_root'),
                   'f1': cell(sel, 'F1_code_bg_root')}
            headline.append({
                'label': 'CORRECTION of the semantic tier: root axiom as background '
                         '(clause tier keeps bg=[] by design; description, clause, '
                         'exact_equiv, accuracy unchanged)',
                **base, 'nonconverged': int(s['p'].nonconverged),
                **{f'submitted_{m}': value(s[m]) for m in s},
                **{f'corrected_{m}': value(cor[m]) for m in cor},
                **{f'delta_{m}': '' if None in (s[m].value, cor[m].value)
                   else round(cor[m].value - s[m].value, 4) for m in s},
                'corrected_P_std': value(cell(sel, 'P_std_bg_root')),
                'corrected_F1_std': value(cell(sel, 'F1_std_bg_root'))})
    _write('semantic_precision_formulas.csv', formulas)
    _write('semantic_tier_corrected.csv', headline)
    for f in formulas:
        print(f"{f['kb']:12s} {f['strategy']:13s} {f['contract']:8s} "
              f"P_code {f['P_code']:<6} P_std {f['P_std']:<6} R {f['R']:<6} "
              f"F1_code {f['F1_code']:<6} F1_std {f['F1_std']:<6} "
              f"n={f['P_std_n_defined']}/{f['n_folds']}{' †' if f['nonconverged'] else ''}")


if __name__ == '__main__':
    main()
