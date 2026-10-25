"""Re-run the Table-5 cells (exclude 2cov; ConMin raw k=1) and score the semantic tier twice:

- ``sem_*``       : the shipped path (bias clauses only, bg = []), recomputed — must equal the
                    committed CSV row-for-row (reproduction check);
- ``sem_*_root``  : same KB clauses, bg = root (the delivered-theory axiom exact_equiv uses).

Also records, for the precision side, unentailed_kb against Cτ as shipped (gt.clauses, which
already contains the root unit) and against Cτ minus the root unit.

SUPERSEDED by relearn_kbs_with_persistence + semantic_tier_corrected (kept: it produced the
handoff-1 numbers in data/results_conmin_r1/handoff1/). Writes only to that directory.

usage: python -m apps.conmin_r1.handoff1_rerun_semantic_with_root KB [--es ff rs_1n ...] [--conditions A,C,C∪S,QuAcq,QuAcq-active]
                                              [--qa-max-queries N] [--qa-timeout S] [--tag name]
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import conacq.eval.conmin_cv_evaluator as ev
from conacq.eval.conmin_slice_scorer import score_named_kb as _orig_score
from conacq.eval.semantic_equivalence import SemanticEquivalenceChecker

OUT = Path('data/results_conmin_r1/handoff1/rows')
ES_ALL = ['ff', 'rs_1n', 'rs_2n', 'rs_3n', 'rs_m']   # Table 5 excludes 2cov


def _prf(tp, fn, fp):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def score_with_root(names, clauses, *, comparator, ground_truth, bg_clauses, **kw):
    """Shipped scorer + extra columns: semantic tier with bg = root, precision vs Cτ\\root."""
    out = _orig_score(names, clauses, comparator=comparator, ground_truth=ground_truth,
                      bg_clauses=bg_clauses, **kw)
    bias = comparator.bias
    kb = [list(c) for cid in names if bias.has_constraint(cid) for c in bias.get_clauses(cid)]
    ct = [list(c) for c in ground_truth.clauses]          # same Cτ as _compare_by_semantic
    root = [list(c) for c in bg_clauses]
    for tag, bg in (('noroot', []), ('root', root)):
        r = SemanticEquivalenceChecker(kb, ct, bg).check_equivalence()
        tp = r.n_ct_checked - len(r.unentailed_ct)
        p, rc, f1 = _prf(tp, len(r.unentailed_ct), len(r.unentailed_kb))
        out[f'sem_p_{tag}'], out[f'sem_r_{tag}'], out[f'sem_f1_{tag}'] = p, rc, f1
        out[f'sem_fn_{tag}'], out[f'sem_fp_{tag}'] = len(r.unentailed_ct), len(r.unentailed_kb)
    root_units = {tuple(c) for c in root}
    ct_wo_root = [c for c in ct if tuple(c) not in root_units]
    r = SemanticEquivalenceChecker(kb, ct_wo_root, []).check_ct_entails_kb()
    out['sem_fp_vs_ct_without_root'] = len(r[1])
    out['n_ct'], out['n_kb_clauses'] = len(ct), len(kb)
    return out


ev.score_named_kb = score_with_root   # _score_row resolves the name from the module globals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kb')
    ap.add_argument('--es', nargs='+', default=ES_ALL)
    ap.add_argument('--conditions', default='A,C,C∪S,QuAcq,QuAcq-active')
    ap.add_argument('--qa-max-queries', type=int, default=5000)
    ap.add_argument('--qa-timeout', type=float, default=400.0)
    ap.add_argument('--tag', default='')
    ap.add_argument('--fold', type=int, default=None,
                    help='ConMin (A/C/C∪S) only: run ONE fold of each --es (parallelise big KBs)')
    a = ap.parse_args()
    conds = set(a.conditions.split(','))
    fm, bias = f'data/fms/{a.kb}.uvl', f'data/bias/{a.kb}-bias.json'
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f'{a.kb}{"_" + a.tag if a.tag else ""}'

    active_res = None
    if 'QuAcq-active' in conds:
        t0 = time.time()
        active_res = ev._learn_quacq_active(bias, fm, 'glucose4', True, a.qa_max_queries, a.qa_timeout)
        print(f'[{stem}] QuAcq-active learned: size={active_res.n_kb} '
              f'queries={active_res.n_queries} reason={active_res.convergence_reason} '
              f'({time.time() - t0:.0f}s)', flush=True)

    rows = []
    for es in a.es:
        t0 = time.time()
        if a.fold is not None:
            rows += _conmin_one_fold(a.kb, es, fm, bias, a.fold, conds)
            print(f'[{stem}] {es} fold {a.fold} done ({time.time() - t0:.0f}s, {len(rows)} rows)', flush=True)
            _dump(rows, OUT / f'{stem}_rows.csv')
            continue
        rows += ev.evaluate_kb_example(
            a.kb, es, fm, bias, f'data/examples/{a.kb}_{es}.json', f'data/folds/{a.kb}_{es}_folds.json',
            k_values=(1,), negatives=('raw',), solver_name='glucose4', use_incremental=True,
            active_res=active_res, qa_max_queries=a.qa_max_queries, qa_timeout_s=a.qa_timeout,
            conditions=conds)
        print(f'[{stem}] {es} done ({time.time() - t0:.0f}s, {len(rows)} rows)', flush=True)
        _dump(rows, OUT / f'{stem}_rows.csv')       # checkpoint after each example set
    if active_res is not None:
        (OUT / f'{stem}_quacq_active_kb.json').write_text(json.dumps(
            {'kb_constraints': list(active_res.kb_constraints), 'n_queries': active_res.n_queries,
             'convergence_reason': active_res.convergence_reason}, indent=1))


def _conmin_one_fold(kb, es, fm, bias_p, fold_idx, conds):
    """evaluate_kb_example's ConMin branch (same setup, same _eval_conmin_fold) for one fold,
    raw negatives, k=1. A is emitted on this (only) pass; it is negatives-independent."""
    assert conds <= ev.CONMIN_CONDITIONS, '--fold supports A/C/C∪S only'
    oracle = ev.FMOracle(fm, solver_name='glucose4', use_incremental=True)
    try:
        model = (ev.ConMinModelBuilder.from_bias(bias_p)
                 .with_oracle_data(oracle.oracle_data).build())
        gt = ev.GroundTruthData.from_uvl(Path(fm))
        comparator = ev.KBComparator(gt, ev.BiasIO.load_from_json(bias_p))
        ex = ev.ExampleIO.load_json(f'data/examples/{kb}_{es}.json')
        pos = [e.assignments for e in ex.positive]
        neg = [e.assignments for e in ex.negative]
        tr_pos, tr_neg, te_pos, te_neg = ev.apply_folds(
            ev.load_folds(f'data/folds/{kb}_{es}_folds.json'), pos, neg, fold_idx)
        meta = dict(kb=kb, example_set=es, fold=fold_idx, zero_neg_train=int(len(tr_neg) == 0),
                    n_train_pos=len(tr_pos), n_train_neg=len(tr_neg),
                    n_test_pos=len(te_pos), n_test_neg=len(te_neg),
                    n_test_total=len(te_pos) + len(te_neg))
        rows = ev._eval_conmin_fold(
            model, oracle, comparator, gt, model.name_to_id, oracle.oracle_data.get_root_clauses(),
            tr_pos, tr_neg, te_pos, te_neg, (1,), 'raw', meta, 'glucose4', True, emit_a=True)
    finally:
        oracle.cleanup()
    return [r for r in rows if r.get('condition') in conds]


def _dump(rows, path):
    keys = sorted({k for r in rows for k in r})
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


if __name__ == '__main__':
    main()
