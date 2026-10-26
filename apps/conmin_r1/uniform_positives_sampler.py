"""Exact uniform sampler over sol(Cτ ∪ root) by top-down SDD sampling.

Cτ (which contains the root unit) is compiled with ``ExactSddCounter``. A sample is drawn
recursively over the vtree: at a decision node, element (p, s) is chosen with probability
#models(p over left) · #models(s over right) / #models(node), then p and s are sampled in the
left and right sub-vtrees; variables of a vtree that a node does not constrain (gaps between the
node's vtree and the enclosing one, or a ``true`` node) are set uniformly. Counts are exact big
integers, and choices use ``random.Random.randrange`` on them, so the sampler is exactly uniform.

usage: python -m apps.conmin_r1.uniform_positives_sampler validate   (χ² on REAL-FM-7)
"""
from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

from pysat.solvers import Solver

from conacq.oracle.ground_truth import GroundTruthData

from . import fm_path
from .exact_sdd_model_counter import ExactSddCounter


class UniformSddSampler:
    def __init__(self, kb: str):
        self.gt = GroundTruthData.from_uvl(Path(fm_path(kb)))
        self.n = len(self.gt.feature_map)
        self.counter = ExactSddCounter(self.n)
        self.root_node = self.counter.compile(self.gt.clauses)
        self.counter.mgr.auto_gc_and_minimize_off()      # freeze the SDD while sampling
        self.memo: Dict[int, int] = {}
        self.total = self.counter.count_over(self.root_node, self.counter.mgr.vtree(), self.memo)
        self.names = {v: k for k, v in self.gt.feature_map.items()}
        self._vars: Dict[int, List[int]] = {}

    def _vtree_vars(self, v) -> List[int]:
        if v is None:
            return []
        key = v.position()
        if key not in self._vars:
            self._vars[key] = [v.var()] if v.is_leaf() else \
                self._vtree_vars(v.left()) + self._vtree_vars(v.right())
        return self._vars[key]

    def _fill(self, v, covered, out, rng):
        """Uniform values for the variables of v not in ``covered``."""
        for x in self._vtree_vars(v):
            if x not in covered:
                out[x] = rng.random() < 0.5

    def _sample(self, n, v, out, rng):
        if n.is_true():
            self._fill(v, set(), out, rng)
            return
        w = n.vtree()
        if n.is_literal():
            lit = n.literal
            out[abs(lit)] = lit > 0
        else:
            pick = rng.randrange(self.counter.count_over(n, w, self.memo))
            for p, s in n.elements():
                weight = (self.counter.count_over(p, w.left(), self.memo) *
                          self.counter.count_over(s, w.right(), self.memo))
                if pick < weight:
                    self._sample(p, w.left(), out, rng)
                    self._sample(s, w.right(), out, rng)
                    break
                pick -= weight
        self._fill(v, set(self._vtree_vars(w)), out, rng)    # gap between w and v

    def sample(self, rng: random.Random) -> Dict[str, bool]:
        out: Dict[int, bool] = {}
        self._sample(self.root_node, self.counter.mgr.vtree(), out, rng)
        for x in range(1, self.n + 1):              # variables absent from the vtree (none here)
            out.setdefault(x, rng.random() < 0.5)
        return {self.names[x]: out[x] for x in range(1, self.n + 1)}

    def check(self, sample: Dict[str, bool]) -> bool:
        lits = [self.gt.feature_map[f] if v else -self.gt.feature_map[f] for f, v in sample.items()]
        with Solver(name='glucose4', bootstrap_with=self.gt.clauses) as s:
            return s.solve(assumptions=lits)


def validate(kb='REAL-FM-7', draws=8000, seed=82):
    from scipy.stats import chisquare
    sm = UniformSddSampler(kb)
    rng = random.Random(seed)
    seen = Counter()
    for _ in range(draws):
        x = sm.sample(rng)
        assert sm.check(x), 'sample violates Cτ'
        seen[tuple(sorted(f for f, v in x.items() if v))] += 1
    obs = list(seen.values()) + [0] * (sm.total - len(seen))
    stat, p = chisquare(obs)
    return {'kb': kb, 'solutions': sm.total, 'draws': draws, 'distinct_drawn': len(seen),
            'chi2': float(stat), 'df': sm.total - 1, 'p': float(p),
            'min_count': min(obs), 'max_count': max(obs), 'expected': draws / sm.total}


if __name__ == '__main__' and sys.argv[1:] == ['validate']:
    print(validate())
