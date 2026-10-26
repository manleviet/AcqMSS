"""Reduce(A) ablation on the persisted KBs — no re-learning.

Reduce preserves the model set, so Reduce(A) behaves like A (same solution set; asserted by
exact model counts) with a smaller constraint set. Comparing A, Reduce(A) and ConMin (C∪S, k=1)
separates what Reduce removes from what Stage 2 (cover + support) removes.

Per (kb, example_set, fold): the task is re-prepared (cheap, no Stage 1), persisted names are
mapped back to assumption ids, and ConMin's own ``Reduce.reduce(ids, [], task.set_b,
task.negation_map)`` runs (BG = task.set_b = ∅, root outside — as in finish_kb). Order (Reduce
keeps the first-examined representative of mutually redundant constraints):
``conmin`` = S_full∖C → C (cover order) → rest of A (pool order), ConMin's F→S→C order extended
to A; ``pool`` = A's pool order (sensitivity only).
A is partitioned into R (rejects ≥ 1 training negative, clause-level SAT check, BG = ∅),
S_full (support⁺ ≥ 1) and V = A ∖ (R ∪ S_full).
UNSAT rule (theory_consistency): an UNSAT delivered theory is flagged and not scored.

usage: python -m apps.conmin_r1.reduce_a_ablation [--kbs ...] [--es ...] [--workers N]
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from pysat.solvers import Solver

import conacq.eval.conmin_cv_evaluator as ev
from conacq.algorithms.acqmss.reduce import Reduce

from . import KBS, R1_DIR, SOLVER, bias_path, examples_path, fm_path, folds_path
from .exact_sdd_model_counter import ExactSddCounter
from .kb_store import delivered_theory, record_path
from .semantic_tier_corrected import score_record
from .theory_consistency import consistent_with_root

OUT_DIR = R1_DIR / 'reduce_a'
ALL_ES = ('ff', 'rs_1n', 'rs_2n', 'rs_3n', 'rs_m', '2cov')


def _rejectors(names, bias, negatives, variables):
    """Names of A that reject ≥ 1 raw negative: clauses(c) ∧ e⁻ is UNSAT (BG = ∅)."""
    lits = [[variables[f] if v else -variables[f] for f, v in e.items()] for e in negatives]
    out = set()
    for n in names:
        with Solver(name=SOLVER, bootstrap_with=bias.get_clauses(n)) as s:
            if any(not s.solve(assumptions=a) for a in lits):
                out.add(n)
    return out


def _score(ctx, cond, names, fallback=()):
    _, bias = ctx['bias_pair']
    clauses = [list(c) for n in names for c in bias.get_clauses(n)]
    rec = {'kb': ctx['kb'], 'example_set': ctx['es'], 'fold': ctx['fold'], 'condition': cond,
           'negatives': 'n/a', 'k': None, 'names': list(names),
           'fallback_clauses': [list(c) for c in fallback], 'root_clauses': ctx['root']}
    flag = consistent_with_root(clauses, fallback)
    out = {'condition': cond, 'n_kb': len(names), 'consistent_with_root': flag}
    counter, ct = ctx['counter']
    theory = counter.compile(delivered_theory(rec, bias))
    both = counter.conjoin(theory, ct)
    out['models_theory'], out['models_both'] = str(counter.count(theory)), str(counter.count(both))
    theory.deref()
    both.deref()
    if not flag:                      # UNSAT: flagged, never scored
        return out
    shipped = ev.score_named_kb(
        names, clauses, comparator=ctx['comparator'], ground_truth=ctx['gt'],
        variables=ctx['variables'], test_pos=ctx['te_pos'], test_neg=ctx['te_neg'],
        bg_clauses=ctx['root'], n_bias=len(bias), solver_name=SOLVER, fallback_clauses=fallback)
    rec['shipped'] = shipped
    sem = score_record(rec)
    n_t, n_both = int(out['models_theory']), int(out['models_both'])
    out.update({k: shipped[k] for k in ('desc_p', 'desc_r', 'desc_f1', 'clause_p', 'clause_r',
                                        'clause_f1', 'exact_equiv', 'accuracy')})
    out.update({k: sem[k] for k in sem if k.startswith(('P_', 'R_', 'F1_'))})
    out['sol_precision'] = n_both / n_t
    out['sol_recall'] = n_both / ctx['n_ct_models']
    return out


def load_fold(kb, es, fold):
    """Everything a per-fold measure needs, without Stage 1: persisted records, the fold's
    train/test split, the re-prepared task (ids, support counts, negation map) and the scoring
    context ``ctx`` used by ``_score`` (comparator, exact counter with Cτ compiled, root)."""
    recs = {(r['condition'], r['k']): r for r in json.loads(record_path(kb, es, fold).read_text())}
    oracle = ev.FMOracle(fm_path(kb), solver_name=SOLVER, use_incremental=True)
    try:
        model = (ev.ConMinModelBuilder.from_bias(bias_path(kb))
                 .with_oracle_data(oracle.oracle_data).build())
        ex = ev.ExampleIO.load_json(examples_path(kb, es))
        tr_pos, tr_neg, te_pos, te_neg = ev.apply_folds(
            ev.load_folds(folds_path(kb, es)), [e.assignments for e in ex.positive],
            [e.assignments for e in ex.negative], fold)
        with ev.profiler_session(ev.ProfilerPreset.BENCHMARK) as prof:
            prepared = model.prepare_task(ev.ConMinTaskInput.from_examples(
                oracle.oracle_data, tr_pos, tr_neg), minimize=False, profiler=prof)
        task, describe = prepared.task, prepared.describe
        gt = ev.GroundTruthData.from_uvl(Path(fm_path(kb)))
        bias = ev.BiasIO.load_from_json(bias_path(kb))
        counter = ExactSddCounter(len(gt.feature_map))
        ct = counter.compile(gt.clauses)
        ctx = dict(kb=kb, es=es, fold=fold, gt=gt, bias_pair=(None, bias),
                   comparator=ev.KBComparator(gt, bias), variables=model.name_to_id,
                   te_pos=te_pos, te_neg=te_neg, counter=(counter, ct),
                   n_ct_models=counter.count(ct),
                   root=[list(c) for c in oracle.oracle_data.get_root_clauses()])
    finally:
        oracle.cleanup()
    return dict(recs=recs, task=task, describe=describe, ctx=ctx, bias=bias, gt=gt,
                variables=model.name_to_id, tr_pos=tr_pos, tr_neg=tr_neg,
                aid={describe.get_description(i): i for i in task.set_c})


def reduce_names(fd, order):
    """ConMin's own Reduce over ``order`` (names) — the ``finish_kb`` call, BG = task.set_b."""
    task, describe = fd['task'], fd['describe']
    with ev.profiler_session(ev.ProfilerPreset.BENCHMARK) as prof:
        checker = ev.build_checker(task, ev.SolverBackend.from_flags(use_incremental=True),
                                   SOLVER, prof)
        try:
            _, kept = Reduce(checker, prof).reduce(
                [fd['aid'][n] for n in order], [], task.set_b, task.negation_map)
        finally:
            checker.cleanup()
    return [describe.get_description(i) for i in kept]


def run_fold(kb, es, fold):
    fd = load_fold(kb, es, fold)
    recs, ctx, bias, tr_pos, tr_neg = fd['recs'], fd['ctx'], fd['bias'], fd['tr_pos'], fd['tr_neg']
    a_names, c_rec = recs[('A', None)]['names'], recs[('C', None)]
    cover, s_full = c_rec['names'], set(c_rec['support_full_k1_names'])
    conmin = recs[('C∪S', 1)]
    cover_set = set(cover)
    orders = {
        'conmin': ([n for n in a_names if n in s_full and n not in cover_set] + cover +
                   [n for n in a_names if n not in s_full and n not in cover_set]),
        'pool': list(a_names)}
    reduced = {}
    for tag, order in orders.items():
        assert sorted(order) == sorted(a_names)
        reduced[tag] = reduce_names(fd, order)
    r_group = _rejectors(a_names, bias, tr_neg, fd['variables'])
    v_group = set(a_names) - r_group - s_full
    red = reduced['conmin']
    rows = [_score(ctx, 'A', a_names), _score(ctx, 'Reduce(A)', red),
            _score(ctx, 'ConMin k=1', conmin['names'], conmin['fallback_clauses'])]
    assert (rows[0]['models_theory'], rows[0]['models_both']) == \
        (rows[1]['models_theory'], rows[1]['models_both']), 'Reduce changed the model set'
    out = {'kb': kb, 'example_set': es, 'fold': fold, 'n_train_pos': len(tr_pos),
           'n_A': len(a_names), 'n_R': len(r_group), 'n_S_full': len(s_full & set(a_names)),
           'n_V': len(v_group), 'n_reduce_a': len(red), 'n_reduce_a_pool_order':
           len(reduced['pool']), 'n_V_kept': len(v_group & set(red)),
           'n_V_in_conmin': len(v_group & set(conmin['names'])),
           'n_reduce_a_minus_conmin': len(set(red) - set(conmin['names'])),
           'n_conmin_minus_reduce_a': len(set(conmin['names']) - set(red)),
           'removed_by_reduce': sorted(set(a_names) - set(red)), 'reduce_a': red,
           'V': sorted(v_group), 'R': sorted(r_group),
           'reduce_a_pool_order': reduced['pool'], 'scores': rows}
    path = OUT_DIR / kb / f'{es}_fold{fold}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    return f"{kb}/{es}/fold{fold}: |A|={len(a_names)} |Reduce(A)|={len(red)} V={len(v_group)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kbs', nargs='+', default=list(KBS))
    ap.add_argument('--es', nargs='+', default=list(ALL_ES))
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    jobs = [(kb, es, f) for kb in a.kbs for es in a.es for f in range(3)]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futs = {pool.submit(run_fold, *j): j for j in jobs}
        for fut in as_completed(futs):
            try:
                print(fut.result(), flush=True)
            except Exception as exc:
                print(f'FAILED {futs[fut]}: {exc!r}', flush=True)


if __name__ == '__main__':
    main()
