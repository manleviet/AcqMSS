"""Reduce order ablation: Reduce last (O1, shipped) vs Reduce first (O2).

O1  KB  = Reduce(C ∪ S ∪ F),  C = AcqMinCover(A),   S = {c ∈ A ∖ C : supp⁺ ≥ k}
O2  KB' = C' ∪ S' ∪ F',       A' = Reduce(A), C' = AcqMinCover(A'), S' = {c ∈ A' ∖ C' : supp⁺ ≥ k}
         (finish_kb's own Reduce runs again on C' ∪ S' ∪ F' and is asserted to remove nothing
         from the bias part; a subset of an irredundant set is irredundant under BG = ∅).

No re-learning: A (pool order), C and the shipped C∪S are persisted (``kbs/``), A' = Reduce(A)
is persisted (``reduce_a/``, order S_full ∖ C → C → rest). The task is re-prepared (no Stage 1)
and ConMin's own ``_compute_cover`` (AcqMinCover, τ = 15, fixed order) and ``finish_kb``
(support⁺ ≥ k, assemble F → S → C, Reduce with BG = task.set_b) run on one checker. A' is
handed to AcqMinCover in A's pool order. Gate: O1 must reproduce the persisted cover and the
persisted C∪S names and fallbacks for every fold and k.

Target construct = bias constraint whose description is in Cτ's descriptions (the description
tier of kb_comparator). UNSAT theories are counted, not scored (``_score``).

usage: python -m apps.conmin_r1.reduce_order [--kbs ...] [--es ...] [--workers N]
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed

from pysat.solvers import Solver

import conacq.eval.conmin_cv_evaluator as ev

from . import K_VALUES, KBS, R1_DIR, SOLVER
from .reduce_a_ablation import ALL_ES, OUT_DIR as REDUCE_DIR, _score, load_fold

OUT_DIR = R1_DIR / 'reduce_order'


def _entailed(kept_clauses, clauses) -> bool:
    with Solver(name='glucose4', bootstrap_with=kept_clauses) as s:
        return all(not s.solve(assumptions=[-l for l in cl]) for cl in clauses)


def _order_run(fd, cm, state, k, tag):
    task, describe, model = fd['task'], fd['describe'], fd['model']
    rk = cm.finish_kb(state, task.support_count, k, task.set_b, task.negation_map)
    _, _, names, fallback, _ = model.resolve_result(
        rk, describe, fd['ctx']['root'], task.set_kb, task.negation_map)
    nm = lambda ids: model.resolve_slice(describe, ids)[1]
    return {'order': tag, 'k': k, 'kb': list(names), 'fallback': [list(c) for c in fallback],
            'cover': nm(rk.cover_ids), 'support': nm(rk.support_ids),
            'redundant': nm(rk.redundant_ids), 'n_redundant_ids': len(rk.redundant_ids),
            'n_uncoverable': len(rk.uncoverable)}


def run_fold(kb, es, fold):
    fd = load_fold(kb, es, fold)
    recs, bias, gt, task, aid = fd['recs'], fd['bias'], fd['gt'], fd['task'], fd['aid']
    a_names = recs[('A', None)]['names']
    a_prime = set(json.loads((REDUCE_DIR / kb / f'{es}_fold{fold}.json').read_text())['reduce_a'])
    target = gt.descriptions
    desc = bias.get_description
    is_target = lambda n: desc(n) in target
    out = {'kb': kb, 'example_set': es, 'fold': fold, 'n_A': len(a_names), 'n_A_prime': len(a_prime),
           'n_bg': len(task.set_b), 'gate': [], 'runs': []}
    with ev.profiler_session(ev.ProfilerPreset.BENCHMARK) as prof:
        checker = ev.build_checker(task, ev.SolverBackend.from_flags(use_incremental=True),
                                   SOLVER, prof)
        try:
            cm = ev.ConMin(checker, prof)
            cover_args = dict(neg_encodings=task.neg_encodings, set_bg=task.set_b,
                              n_bias=len(task.set_c), n_neg_tv=len(task.set_neg_tv),
                              n_e_pos=len(task.set_tc))
            st1 = cm._compute_cover([aid[n] for n in a_names], **cover_args)
            st2 = cm._compute_cover([aid[n] for n in a_names if n in a_prime], **cover_args)
            if sorted(fd['model'].resolve_slice(fd['describe'], st1.cover_ids)[1]) != \
                    sorted(recs[('C', None)]['names']):
                out['gate'].append('cover')
            for k in K_VALUES:
                o1 = _order_run(fd, cm, st1, k, 'O1')
                o2 = _order_run(fd, cm, st2, k, 'O2')
                shipped = recs[('C∪S', k)]
                if o1['kb'] != shipped['names'] or o1['fallback'] != shipped['fallback_clauses']:
                    out['gate'].append(f'k={k}')
                out['runs'] += [o1, o2]
        finally:
            checker.cleanup()

    clauses = lambda names: [list(c) for n in names for c in bias.get_clauses(n)]
    a_targets = {desc(n) for n in a_names if is_target(n)}
    for run in out['runs']:
        pre = (run['cover'] + run['support']) if run['order'] == 'O1' else a_names
        post = run['kb'] if run['order'] == 'O1' else [n for n in a_names if n in a_prime]
        kept = clauses(post) + (run['fallback'] if run['order'] == 'O1' else [])
        lost = sorted({desc(n) for n in pre if is_target(n)} - {desc(n) for n in post})
        lost_names = [n for n in pre if is_target(n) and desc(n) in set(lost)]
        run['target_lost_to_reduce'] = lost
        run['target_lost_to_reduce_entailed'] = sum(_entailed(kept, bias.get_clauses(n))
                                                   for n in lost_names)
        run['n_target_lost_to_reduce_constraints'] = len(lost_names)
        stage2_pool = a_targets if run['order'] == 'O1' else \
            {desc(n) for n in a_names if n in a_prime and is_target(n)}
        run['target_lost_to_stage2'] = sorted(
            stage2_pool - {desc(n) for n in run['cover'] + run['support']})
        if run['order'] == 'O2':                    # finish_kb's Reduce must be a no-op on C'∪S'
            run['reduce_again_removed_bias'] = [n for n in run['redundant']]
        run['score'] = _score(fd['ctx'], run['order'], run['kb'], run['fallback'])
    by_k = {}
    for run in out['runs']:
        by_k.setdefault(run['k'], {})[run['order']] = run
    for k, pair in by_k.items():
        k1, k2 = set(pair['O1']['kb']), set(pair['O2']['kb'])
        pair['O2']['kb_minus_kb_prime'] = sorted(desc(n) for n in k1 - k2)
        pair['O2']['kb_prime_minus_kb'] = sorted(desc(n) for n in k2 - k1)
        pair['O2']['cover_differs'] = sorted(pair['O1']['cover']) != sorted(pair['O2']['cover'])
    path = OUT_DIR / kb / f'{es}_fold{fold}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    return f"{kb}/{es}/fold{fold}: gate {'OK' if not out['gate'] else out['gate']}"


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
