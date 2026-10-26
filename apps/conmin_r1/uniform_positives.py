"""Step 5 — is Reduce(A)'s solution-recall gap a sampler artefact?

Per (kb, example_set, fold) — same folds, same training negatives, same held-out test set — the
training positives are replaced (or extended) and A, Reduce(A), C ∪ S (k = 1) are re-learned
through the library path (``uniform_positives_learn``):

  original     the fold's own positives (gate: must reproduce the persisted Reduce(A))
  uniform_n    n exact-uniform positives from sol(Cτ ∪ root), n = n_train_pos of the fold
  uniform_2n   2n                (draws nested: the n sample is a prefix of the 2n and 4n samples)
  uniform_4n   4n
  mixed_n      the original positives + the same n uniform positives

Uniform draws: ``UniformSddSampler`` with ``random.Random(82 + fold)``. Per theory: spurious
(Cτ ⊭ c), class (dead_features definitions), support⁺, #dead features of Reduce(A) ∪ root, and
``reduce_a_ablation._score`` (all tiers, root in the premise, P_std, sol P/R by exact counting).

usage: python -m apps.conmin_r1.uniform_positives [--kbs ...] [--es ...] [--variants ...] [--workers N]
"""
from __future__ import annotations

import argparse
import json
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from pysat.solvers import Solver

from . import KBS, R1_DIR
from .dead_features import _class, _spurious
from .dead_features_sat import SelectorTheory, dead_features
from .reduce_a_ablation import ALL_ES, _rejectors, _score, load_fold
from .uniform_positives_learn import learn
from .uniform_positives_sampler import UniformSddSampler

OUT_DIR = R1_DIR / 'uniform_positives'
VARIANTS = ('original', 'uniform_n', 'uniform_2n', 'uniform_4n', 'mixed_n')
SEED = 82
MULT = {'uniform_n': 1, 'uniform_2n': 2, 'uniform_4n': 4, 'mixed_n': 1}


def positives_for(kb, fold, variant, original):
    if variant == 'original':
        return list(original)
    n = len(original)
    rng, sampler = random.Random(SEED + fold), UniformSddSampler(kb)
    draws = [sampler.sample(rng) for _ in range(MULT[variant] * n)]
    return list(original) + draws if variant == 'mixed_n' else draws


def run_job(kb, es, fold, variant):
    t0 = time.time()
    fd = load_fold(kb, es, fold)
    bias, gt, tr_neg = fd['bias'], fd['gt'], fd['tr_neg']
    pos = positives_for(kb, fold, variant, fd['tr_pos'])
    out = {'kb': kb, 'example_set': es, 'fold': fold, 'variant': variant,
           'n_train_pos_original': len(fd['tr_pos']), 'n_pos_used': len(pos),
           'n_train_neg': len(tr_neg), 'n_bias': len(bias), 'seed': SEED + fold}
    learned = learn(kb, pos, tr_neg)
    out['learn_seconds'] = round(time.time() - t0, 1)
    if learned is None:
        out['gate_tripped'] = True
        return _save(out)
    red, var = learned['Reduce(A)'], learned['variables']
    r_group = _rejectors(learned['A'], bias, tr_neg, var)
    selected = {var[f] for e in pos + tr_neg for f, v in e.items() if v}
    with Solver(name='glucose4', bootstrap_with=[list(c) for c in gt.clauses]) as ct:
        out['reduce_a_constraints'] = [{
            'name': c, 'spurious': _spurious(ct, bias.get_clauses(c)),
            'class': _class(c, set(learned['cover']), r_group, learned['support'],
                            bias.get_clauses(c), selected),
            'support': learned['support'].get(c, 0)} for c in red]
    th = SelectorTheory(len(gt.feature_map), {c: bias.get_clauses(c) for c in red})
    dead, _ = dead_features(th, red)
    th.close()
    out.update({'n_A': len(learned['A']), 'n_cover': len(learned['cover']),
                'reduce_a': red, 'conmin': learned['C∪S'], 'n_dead_reduce_a': len(dead),
                'scores': [_score(fd['ctx'], 'Reduce(A)', red),
                           _score(fd['ctx'], 'ConMin k=1', learned['C∪S'],
                                  learned['C∪S_fallback'])]})
    out['seconds'] = round(time.time() - t0, 1)
    return _save(out)


def _save(out):
    path = OUT_DIR / out['kb'] / f"{out['example_set']}_fold{out['fold']}_{out['variant']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1))
    return (f"{out['kb']}/{out['example_set']}/f{out['fold']}/{out['variant']}: "
            f"n_pos={out['n_pos_used']} |Reduce(A)|={len(out.get('reduce_a', []))} "
            f"{out.get('seconds', out['learn_seconds'])}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kbs', nargs='+', default=list(KBS))
    ap.add_argument('--es', nargs='+', default=list(ALL_ES))
    ap.add_argument('--variants', nargs='+', default=list(VARIANTS))
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    jobs = [(kb, es, f, v) for kb in a.kbs for es in a.es for f in range(3) for v in a.variants
            if a.force or not (OUT_DIR / kb / f'{es}_fold{f}_{v}.json').exists()]
    cost = {'rs_3n': 0, 'rs_2n': 1, 'rs_1n': 2, 'ff': 3, 'rs_m': 4, '2cov': 5}   # longest first
    jobs.sort(key=lambda j: (cost.get(j[1], 9), -MULT.get(j[3], 0)))
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futs = {pool.submit(run_job, *j): j for j in jobs}
        for fut in as_completed(futs):
            try:
                print(fut.result(), flush=True)
            except Exception as exc:
                print(f'FAILED {futs[fut]}: {exc!r}', flush=True)


if __name__ == '__main__':
    main()
