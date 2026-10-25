"""Consistency of delivered theories with the root axiom (measurement only; no scoring change).

Hypothesis under test: some delivered theories are UNSAT with the root axiom. An UNSAT
theory entails every clause, so it scores semantic recall 1.0 under the root contract while
accepting no configuration at all.

Per fold, four SAT checks (glucose4):
- ``consistent_with_root``   delivered theory ∪ root — SoSyM: learned ∪ NE clauses stored with
  the fold; ConMin: learned ∪ ¬e⁻ fallbacks (the theory exact_equiv/accuracy score);
- ``consistent_without_NE``  learned clauses ∪ root;
- ``consistent_learned_only`` learned clauses alone;
- ``consistent_NE_root``     NE part ∪ root.
ConMin also gets ``consistent_with_fold_NE`` (learned ∪ every negated training negative ∪ root).
Scores (sem R, P_code, P_std) come from the unmodified comparator under the root contract (the
as-submitted contract for SoSyM, the corrected one for ConMin; ConMin's submitted bg = [] recall
is ``sem_R_submitted``). exact_equiv / accuracy are the stored (SoSyM) or gated (ConMin) values.

usage: python -m apps.conmin_r1.consistency_check <extracted feat/sosym-r1 tree>
"""
from __future__ import annotations

import argparse
import csv
import json
from functools import lru_cache
from pathlib import Path

from conacq.bias import BiasIO
from conacq.eval.kb_comparator import ComparationStrategy, KBComparator
from conacq.eval.result_loader import ConGenResultData
from conacq.oracle.ground_truth import GroundTruthData

from . import R1_DIR, bias_path, fm_path
from .kb_store import iter_records, kb_clauses
from .reproduction_gate import KEY, committed_rows
from .sosym_r1_precision_check import KBS, METHODS, NOT_RUN, SAMPLINGS, fold_file
from .theory_consistency import ROOT, sat

OUT = R1_DIR / 'consistency_check.csv'


@lru_cache(maxsize=None)
def _kb(kb):
    bias = BiasIO.load_from_json(bias_path(kb))
    return KBComparator(GroundTruthData.from_uvl(Path(fm_path(kb))), bias), bias


def _scores(kb, names):
    comp, _ = _kb(kb)
    res = comp.compare(ConGenResultData(kb_constraints=list(names), n_bias=0,
                                        n_kb=len(names), bg_clauses=ROOT),
                       ComparationStrategy.SEMANTIC)
    std = res.standard_precision
    return {'sem_R': res.metrics.recall, 'P_code': res.metrics.precision,
            'P_std': '' if std.precision is None else std.precision,
            'n_kb_clauses': std.n_kb_checked}


def _checks(learned, ne):
    return {'consistent_with_root': sat(learned + ne + ROOT),
            'consistent_without_NE': sat(learned + ROOT),
            'consistent_learned_only': sat(learned),
            'consistent_NE_root': sat(ne + ROOT)}


def sosym_rows(tree: Path):
    for kb in KBS:
        _, bias = _kb(kb)
        for samp in SAMPLINGS:
            if (kb, samp) in NOT_RUN:
                continue
            for method in METHODS:
                folds = json.loads(fold_file(tree, kb, samp, method).read_text())['folds']
                for i, f in enumerate(folds):
                    assert [list(c) for c in f['bg_clauses']] == ROOT
                    names = [c['id'] if isinstance(c, dict) else c for c in f['kb_constraints']]
                    learned = [list(c) for n in names for c in bias.get_clauses(n)]
                    m = f['metrics']
                    ee = f['evaluation'].get('exact_equiv')
                    yield {'paper': 'SoSyM-R1', 'kb': kb, 'condition': method,
                           'example_set': samp, 'fold': i, 'k': '',
                           'n_train_pos': f['train_size']['positive'],
                           'n_train_neg': f['train_size']['negative'],
                           **_checks(learned, [list(c) for c in f['ne_clauses']]),
                           'n_kb': len(names), **_scores(kb, names), 'sem_R_submitted': '',
                           'exact_equiv': (ee.get('is_equivalent') if isinstance(ee, dict)
                                           else ee),
                           'accuracy': f['accuracy'],
                           'n_test_pos': m['true_positives'] + m['false_negatives'],
                           'n_test_neg': m['true_negatives'] + m['false_positives'],
                           'consistent_with_fold_NE': ''}


def conmin_rows():
    committed = committed_rows()
    for rec in iter_records():
        _, bias = _kb(rec['kb'])
        learned = kb_clauses(rec, bias)
        key = (rec['kb'], rec['example_set'], str(rec['fold']), rec['condition'],
               rec['negatives'], '' if rec['k'] is None else str(rec['k']))
        c = committed[key]
        yield {'paper': 'AAAI-27', 'kb': rec['kb'], 'condition': rec['condition'],
               'example_set': rec['example_set'], 'fold': rec['fold'],
               'k': '' if rec['k'] is None else rec['k'],
               'n_train_pos': c['n_train_pos'], 'n_train_neg': c['n_train_neg'],
               **_checks(learned, [list(x) for x in rec['fallback_clauses']]),
               'n_kb': len(rec['names']), **_scores(rec['kb'], rec['names']),
               'sem_R_submitted': rec['shipped']['sem_r'],
               'exact_equiv': rec['shipped']['exact_equiv'],
               'accuracy': rec['shipped']['accuracy'],
               'n_test_pos': c['n_test_pos'], 'n_test_neg': c['n_test_neg'],
               'consistent_with_fold_NE': sat(learned + rec['ne_clauses_fold'] + ROOT)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('tree', type=Path)
    rows = list(conmin_rows()) + list(sosym_rows(ap.parse_args().tree))
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    unsat = [r for r in rows if not r['consistent_with_root']]
    print(f'{len(rows)} folds checked -> {OUT}; UNSAT with root: {len(unsat)}')
    groups = {}
    for r in unsat:
        groups.setdefault((r['paper'], r['condition'], r['example_set']), []).append(r)
    for (paper, cond, es), rs in sorted(groups.items()):
        n_all = sum(1 for r in rows if (r['paper'], r['condition'], r['example_set']) ==
                    (paper, cond, es))
        print(f'  {paper:9s} {cond:13s} {es:6s} UNSAT {len(rs)}/{n_all}  kbs='
              f"{sorted({r['kb'] for r in rs})}  without_NE_unsat="
              f"{sum(not r['consistent_without_NE'] for r in rs)}  "
              f"NE_root_unsat={sum(not r['consistent_NE_root'] for r in rs)}")
    print('every UNSAT fold has sem_R = 1.000:', all(abs(r['sem_R'] - 1) < 1e-12 for r in unsat))
    print('UNSAT only when n_train_pos = 0:', all(int(r['n_train_pos']) == 0 for r in unsat),
          '| UNSAT n_train_pos values:', sorted({int(r['n_train_pos']) for r in unsat}))
    print('ConMin folds inconsistent with the full fold NE:',
          sum(1 for r in rows if r['paper'] == 'AAAI-27' and not r['consistent_with_fold_NE']))


if __name__ == '__main__':
    main()
