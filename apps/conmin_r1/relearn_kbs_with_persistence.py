"""Re-learn the Table-5 KBs and PERSIST them (the submitted sweep never stored learned KBs).

Per (kb, example_set, fold) — same folds, seed and solver as the submitted sweep — it runs
the library steps of ``conmin_cv_evaluator._eval_conmin_fold`` (raw negatives, k ∈ K_VALUES),
QuAcq-ex (example-only, ``shuffle_seed=fold``) and scores the per-KB QuAcq-active theory.
Every KB is scored with the shipped ``score_named_kb`` so ``semantic_tier_corrected`` can gate
the re-run against the committed CSV row by row.

QuAcq-active is fold-independent and learned once per KB: pass ``--learn-quacq-active`` to
learn it (hours on REAL-FM-4), or ``--import-quacq-active KB=PATH`` to import a theory learned
earlier under the same budget (a JSON with ``kb_constraints``/``n_queries``/
``convergence_reason``; clauses are resolved from the bias, which equals the runner's
``kb_clauses``); otherwise it is loaded from ``kbs/<kb>/quacq_active.json``.

usage: python -m apps.conmin_r1.relearn_kbs_with_persistence [--kbs ...] [--es ...]
           [--workers N] [--learn-quacq-active] [--force]
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import conacq.eval.conmin_cv_evaluator as ev
from conacq.runners import QuAcqRunner

from . import (EXAMPLE_SETS, K_VALUES, KB_DIR, KBS, QA_BUDGET, SEED, SOLVER,
               bias_path, examples_path, fm_path, folds_path)
from .kb_store import record_path, save_records

SCORE_KEYS = ('size', 'sem_p', 'sem_r', 'sem_f1', 'clause_f1', 'desc_f1', 'exact_equiv',
              'accuracy')


def _ne_clause(assignment, variables):
    """¬e⁻ of a raw negative: the clause forbidding exactly its assigned literals."""
    return [-variables[f] if v else variables[f] for f, v in sorted(assignment.items())]


def _record(ctx, condition, negatives, k, names, clauses, fallback, extra=None):
    scored = ev.score_named_kb(
        names, clauses, comparator=ctx['comparator'], ground_truth=ctx['gt'],
        variables=ctx['variables'], test_pos=ctx['te_pos'], test_neg=ctx['te_neg'],
        bg_clauses=ctx['root'], n_bias=ctx['n_bias'], solver_name=SOLVER,
        fallback_clauses=fallback)
    return {**ctx['meta'], 'condition': condition, 'negatives': negatives, 'k': k,
            'names': list(names), 'fallback_clauses': [list(c) for c in fallback],
            'root_clauses': ctx['root'], 'ne_clauses_fold': ctx['ne'],
            'shipped': {key: scored.get(key) for key in SCORE_KEYS}, **(extra or {})}


def _conmin_records(ctx, model, oracle):
    """A, C and C∪S per k from ONE Stage-1 — the steps of _eval_conmin_fold, raw negatives."""
    with ev.profiler_session(ev.ProfilerPreset.BENCHMARK) as prof:
        prepared = model.prepare_task(
            ev.ConMinTaskInput.from_examples(oracle.oracle_data, ctx['tr_pos'], ctx['tr_neg']),
            minimize=False, profiler=prof)
        task, describe = prepared.task, prepared.describe
        checker = ev.build_checker(task, ev.SolverBackend.from_flags(use_incremental=True),
                                   SOLVER, prof)
        try:
            cm = ev.ConMin(checker, prof)
            state = cm.acquire_pool_and_cover(task.set_c, task.set_b, task.set_tc,
                                              task.set_neg_tv, task.negation_map,
                                              task.neg_encodings)
            if state is None:
                raise RuntimeError('consistency gate tripped')
            ctx['n_bias'] = state.n_bias
            sc = task.support_count or {}
            _, s_full_names = model.resolve_slice(       # support-only ablation, k=1
                describe, [c for c in state.mss if sc.get(c, 0) >= 1])
            _, cover_names = model.resolve_slice(describe, state.cover_ids)
            recs, u_fallbacks = [], None
            for k in K_VALUES:
                rk = cm.finish_kb(state, task.support_count, k, task.set_b, task.negation_map)
                _, cs_cl, cs_nm, fb_cl, _ = model.resolve_result(
                    rk, describe, ctx['root'], task.set_kb, task.negation_map)
                u_fallbacks = fb_cl if u_fallbacks is None else u_fallbacks
                _, s_names = model.resolve_slice(describe, rk.support_ids)
                recs.append(_record(ctx, 'C∪S', 'raw', k, cs_nm, cs_cl, fb_cl,
                                    {'cover_names': cover_names, 'support_names': s_names}))
            a_cl, a_nm = model.resolve_slice(describe, state.mss)
            recs.append(_record(ctx, 'A', 'n/a', None, a_nm, a_cl, ()))
            c_cl, c_nm = model.resolve_slice(describe, state.cover_ids)
            recs.append(_record(ctx, 'C', 'raw', None, c_nm, c_cl, u_fallbacks,
                                {'support_full_k1_names': s_full_names}))
            return recs
        finally:
            checker.cleanup()


def run_fold(kb: str, es: str, fold: int) -> str:
    t0 = time.time()
    oracle = ev.FMOracle(fm_path(kb), solver_name=SOLVER, use_incremental=True)
    try:
        model = (ev.ConMinModelBuilder.from_bias(bias_path(kb))
                 .with_oracle_data(oracle.oracle_data).build())
        gt = ev.GroundTruthData.from_uvl(Path(fm_path(kb)))
        bias = ev.BiasIO.load_from_json(bias_path(kb))
        ex = ev.ExampleIO.load_json(examples_path(kb, es))
        tr_pos, tr_neg, te_pos, te_neg = ev.apply_folds(
            ev.load_folds(folds_path(kb, es)), [e.assignments for e in ex.positive],
            [e.assignments for e in ex.negative], fold)
        variables = model.name_to_id
        ctx = dict(comparator=ev.KBComparator(gt, bias), gt=gt, variables=variables,
                   tr_pos=tr_pos, tr_neg=tr_neg, te_pos=te_pos, te_neg=te_neg,
                   root=[list(c) for c in oracle.oracle_data.get_root_clauses()],
                   ne=[_ne_clause(a, variables) for a in tr_neg], n_bias=len(bias),
                   meta=dict(kb=kb, example_set=es, fold=fold, seed=SEED, solver=SOLVER,
                             fold_file=folds_path(kb, es), examples_file=examples_path(kb, es)))
        records = _conmin_records(ctx, model, oracle)
    finally:
        oracle.cleanup()
    runner = QuAcqRunner(bias_path(kb), fm_path(kb), SOLVER, query_mode='example_only',
                         use_incremental=True)
    try:
        res = runner.run(tr_pos, tr_neg, shuffle_seed=fold)
    finally:
        runner.cleanup()
    records.append(_record(ctx, 'QuAcq', 'n/a', None, res.kb_constraints, res.kb_clauses, (),
                           {'convergence_reason': res.convergence_reason}))
    qa = json.loads((KB_DIR / kb / 'quacq_active.json').read_text())
    records.append(_record(ctx, 'QuAcq-active', 'n/a', None, qa['kb_constraints'],
                           qa['kb_clauses'], (), {k: qa[k] for k in
                                                  ('convergence_reason', 'n_queries')}))
    save_records(kb, es, fold, records)
    return f'{kb}/{es}/fold{fold}: {len(records)} records ({time.time() - t0:.0f}s)'


def _save_quacq_active(kb, names, clauses, n_queries, reason, source):
    maxq, timeout = QA_BUDGET[kb]
    out = KB_DIR / kb / 'quacq_active.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        'kb': kb, 'kb_constraints': list(names), 'kb_clauses': [list(c) for c in clauses],
        'n_queries': n_queries, 'convergence_reason': reason, 'qa_max_queries': maxq,
        'qa_timeout_s': timeout, 'solver': SOLVER, 'source': source}, indent=1))
    print(f'{kb} QuAcq-active: size={len(names)} queries={n_queries} reason={reason} '
          f'({source})', flush=True)


def learn_quacq_active(kb: str) -> None:
    maxq, timeout = QA_BUDGET[kb]
    res = ev._learn_quacq_active(bias_path(kb), fm_path(kb), SOLVER, True, maxq, timeout)
    _save_quacq_active(kb, res.kb_constraints, res.kb_clauses, res.n_queries,
                       res.convergence_reason, 'learned')


def import_quacq_active(kb: str, path: str) -> None:
    src = json.loads(Path(path).read_text())
    bias = ev.BiasIO.load_from_json(bias_path(kb))
    clauses = [c for cid in src['kb_constraints'] for c in bias.get_clauses(cid)]
    _save_quacq_active(kb, src['kb_constraints'], clauses, src['n_queries'],
                       src['convergence_reason'], f'imported from {path}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kbs', nargs='+', default=list(KBS))
    ap.add_argument('--es', nargs='+', default=list(EXAMPLE_SETS))
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--learn-quacq-active', action='store_true')
    ap.add_argument('--import-quacq-active', nargs='*', default=[], metavar='KB=PATH')
    ap.add_argument('--force', action='store_true', help='re-run folds already persisted')
    a = ap.parse_args()
    logging.basicConfig(level=logging.ERROR)
    for spec in a.import_quacq_active:
        import_quacq_active(*spec.split('=', 1))
    if a.learn_quacq_active:
        for kb in a.kbs:
            learn_quacq_active(kb)
    jobs = [(kb, es, f) for kb in a.kbs for es in a.es for f in range(3)
            if a.force or not record_path(kb, es, f).exists()]
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures = {pool.submit(run_fold, *j): j for j in jobs}
        for fut in as_completed(futures):
            try:
                print(fut.result(), flush=True)
            except Exception as exc:          # one fold must not void the sweep
                print(f'FAILED {futures[fut]}: {exc!r}', flush=True)


if __name__ == '__main__':
    main()
