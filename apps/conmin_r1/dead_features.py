"""Step 4 — dead features of T = Reduce(A) ∪ root, their anatomy, and what repairing them recovers.

Per (kb, example_set, fold), on the persisted Reduce(A) (``reduce_a/``), no re-learning:
Part 1  Dead(Cτ ∪ root) (excluded from every test-case set), Dead(T) with aggregated SAT calls,
        false optionals (T ⊨ f, Cτ ∪ root ⊭ f; diagnostic).
Part 2  for each f ∈ Dead(T) ∖ Dead(Cτ): one minimal conflict CS(f) ⊆ Reduce(A) (QuickXPlain
        against root ∪ {f}); Certain = {c : ∃ such f, root ∪ {c} ∪ {f} UNSAT} (only c mentioning
        f is checked); per constraint: spurious (Cτ ⊭ c — Cτ contains the root unit, the
        semantic tier's precision-side check), in a CS, in Certain, class, support⁺.
Part 3  UB = Reduce(A) ∖ {spurious c in some CS}; EST = (Reduce(A) ∖ Certain) ∖ D, D a
        minimum-cardinality diagnosis (HS-tree; FastDiag's precondition fails here, see
        dead_features_sat) with positives = still-dead features, negatives = training e⁻
        rejected before D. Removal preference: support⁺ ascending, then constraints outside the
        cover first. Scored with ``reduce_a_ablation._score`` (all tiers, root in the premise,
        P_std; sol P/R by exact counting — scoring only, the method counts nothing).
        Added: UB_A = Reduce(A ∖ X), X = every spurious constraint of A in some conflict of a
        dead feature (QuickXPlain repeated until f is alive or a conflict has no spurious
        member). Repair BEFORE Reduce: Reduce(A) has already dropped target constraints that
        the spurious killers entail, so removing killers from Reduce(A) (UB) can lose soundness.
Classes (precedence in this order): R∩C = in the cover and in R; C∖R = cover element rejecting
no negative alone; R∖C = rejects a negative, not in the cover; S = support⁺ ≥ 1, not in R;
V = the rest; V_unseen = V whose trigger features (variables occurring negatively in one of
its clauses) are never selected in any training example; V_obs = the rest of V.
UNSAT folds (A ∪ root UNSAT) are counted, not analysed or scored.

usage: python -m apps.conmin_r1.dead_features [--kbs ...] [--es ...] [--workers N]
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed

from pysat.solvers import Solver

from . import KBS, R1_DIR
from .dead_features_sat import (ROOT_LIT, SelectorTheory, core_features, dead_features,
                                hs_diagnosis, quickxplain)
from .reduce_a_ablation import ALL_ES, OUT_DIR as REDUCE_DIR, _score, load_fold, reduce_names

OUT_DIR = R1_DIR / 'dead_features'
FALLBACK = '__fallback__'      # ConMin's ¬e⁻ fallback clauses as one pseudo-constraint


def _lits(example, variables):
    return [variables[f] if v else -variables[f] for f, v in example.items()]


def _spurious(ct_solver, clauses) -> bool:
    """Cτ ⊭ c: some clause of c is not entailed (Cτ ∧ ¬clause SAT)."""
    return any(ct_solver.solve(assumptions=[-l for l in cl]) for cl in clauses)


def _class(c, cover, r_group, support, clauses, selected):
    if c in cover:
        return 'R∩C' if c in r_group else 'C∖R'
    if c in r_group:
        return 'R∖C'
    if support.get(c, 0) >= 1:
        return 'S'
    triggers = {abs(l) for cl in clauses for l in cl if l < 0}
    return 'V_obs' if triggers & selected else 'V_unseen'


def run_fold(kb, es, fold):
    red_fold = json.loads((REDUCE_DIR / kb / f'{es}_fold{fold}.json').read_text())
    fd = load_fold(kb, es, fold)
    recs, bias, gt, var = fd['recs'], fd['bias'], fd['gt'], fd['variables']
    n = len(gt.feature_map)
    red, a_names = red_fold['reduce_a'], recs[('A', None)]['names']
    cover, r_group = set(recs[('C', None)]['names']), set(red_fold['R'])
    conmin = recs[('C∪S', 1)]
    support = {c: fd['task'].support_count.get(fd['aid'][c], 0) for c in a_names}
    out = {'kb': kb, 'example_set': es, 'fold': fold, 'n_train_pos': len(fd['tr_pos']),
           'n_train_neg': len(fd['tr_neg']), 'n_features': n,
           'consistent': red_fold['scores'][0]['consistent_with_root']}
    ct_th = SelectorTheory(n, {}, base=gt.clauses)            # Cτ includes the root unit
    out['dead_ct'], out['calls_dead_ct'] = dead_features(ct_th, [])
    core_ct = set(core_features(ct_th, [], out['dead_ct']))
    ct_th.close()
    scores = [_score(fd['ctx'], 'A', a_names), _score(fd['ctx'], 'Reduce(A)', red),
              _score(fd['ctx'], 'ConMin k=1', conmin['names'], conmin['fallback_clauses'])]
    if not out['consistent']:
        out['scores'] = scores
        return _save(out)
    th = SelectorTheory(n, {**{c: bias.get_clauses(c) for c in
                               set(a_names) | set(red) | set(conmin['names'])},
                            FALLBACK: conmin['fallback_clauses']})
    dead_ct = set(out['dead_ct'])
    dead_t, out['calls_dead_t'] = dead_features(th, red)
    out['dead_t'] = dead_t
    out['false_optionals'] = sorted(set(core_features(th, red, dead_t)) - core_ct)
    targets = [f for f in dead_t if f not in dead_ct]

    # Part 2 — anatomy
    start = th.calls
    cs = {f: quickxplain(th, [ROOT_LIT, f], red) for f in targets}
    out['checks_qx'] = th.calls - start
    certain = {c for f in targets for c in red
               if f in {abs(l) for cl in bias.get_clauses(c) for l in cl}
               and not th.sat([c], [ROOT_LIT, f])}
    with Solver(name='glucose4', bootstrap_with=[list(c) for c in gt.clauses]) as ct_solver:
        spurious = {c: _spurious(ct_solver, bias.get_clauses(c)) for c in a_names}
    selected = {var[f] for e in fd['tr_pos'] + fd['tr_neg'] for f, v in e.items() if v}
    in_cs = {c for s in cs.values() for c in s}
    out['conflicts'] = {str(f): cs[f] for f in targets}
    out['certain'] = sorted(certain)
    out['constraints'] = [{
        'name': c, 'spurious': spurious[c], 'in_conflict': c in in_cs, 'in_certain': c in certain,
        'class': _class(c, cover, r_group, support, bias.get_clauses(c), selected),
        'support': support.get(c, 0)} for c in red]

    # Part 3 — UB and EST
    ub = [c for c in red if not (spurious[c] and c in in_cs)]
    rem = [c for c in red if c not in certain]
    dead_rem = [f for f in dead_features(th, rem)[0] if f not in dead_ct]
    negs = [_lits(e, var) for e in fd['tr_neg']]
    required = [e for e in negs if not th.sat(rem, [ROOT_LIT] + e)]
    order = sorted(rem, key=lambda c: (support.get(c, 0), c in cover, red.index(c)))
    d, status, checks, nodes = hs_diagnosis(th, order, dead_rem, required)
    est = [c for c in rem if c not in set(d or [])]
    out['ub'], out['est'] = ub, est
    out['diagnosis'] = {'D': d, 'status': status, 'checks': checks, 'nodes': nodes,
                        'n_D': len(d) if d is not None else None,
                        'n_D_spurious': sum(spurious.get(c, False) for c in d or []),
                        'dead_before_D': len(dead_rem),
                        'negatives_broken_by_certain': len(negs) - len(required)}
    out['dead_remaining'] = {
        'Reduce(A)': len(targets),
        'ConMin k=1': sum(f not in dead_ct for f in dead_features(
            th, conmin['names'] + [FALLBACK])[0]),
        'UB': sum(f not in dead_ct for f in dead_features(th, ub)[0]),
        'EST': sum(f not in dead_ct for f in dead_features(th, est)[0])}
    # UB_A — repair before Reduce
    x, unrecoverable = set(), []
    for f in targets:
        while True:
            conflict = quickxplain(th, [ROOT_LIT, f], [c for c in a_names if c not in x])
            if conflict is None:
                break
            killers = [c for c in conflict if spurious[c]]
            if not killers:
                unrecoverable.append(f)
                break
            x |= set(killers)
    s_full = set(recs[('C', None)]['support_full_k1_names'])
    keep = [c for c in a_names if c not in x]
    ub_a = reduce_names(fd, [c for c in keep if c in s_full and c not in cover]
                        + [c for c in recs[('C', None)]['names'] if c in keep]
                        + [c for c in keep if c not in s_full and c not in cover])
    out['ub_a'] = ub_a
    out['ub_a_removed_from_A'] = sorted(x)
    out['ub_a_unrecoverable'] = unrecoverable
    out['dead_remaining']['UB_A'] = sum(f not in dead_ct for f in dead_features(th, ub_a)[0])
    th.close()
    scores += [_score(fd['ctx'], 'UB', ub), _score(fd['ctx'], 'EST', est),
               _score(fd['ctx'], 'UB_A', ub_a)]
    assert (scores[0]['models_theory'], scores[0]['models_both']) == \
        (scores[1]['models_theory'], scores[1]['models_both']), 'Reduce changed the model set'
    out['scores'] = scores
    return _save(out)


def _save(out):
    path = OUT_DIR / out['kb'] / f"{out['example_set']}_fold{out['fold']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    return (f"{out['kb']}/{out['example_set']}/fold{out['fold']}: consistent={out['consistent']} "
            f"dead_T={len(out.get('dead_t', []))} certain={len(out.get('certain', []))}")


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
