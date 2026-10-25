"""Exact model counting over a FIXED variable set with pysdd (SDD knowledge compilation).

pysdd's ``model_count()`` counts only over the variables a node mentions, and its
``global_model_count()`` / WMC return C integers / doubles. Ratios such as
#models(KB ∧ Cτ) / #models(KB) need counts over ALL feature variables, exactly, so the
count is computed here with Python big integers by a smoothed traversal of the SDD over
its vtree; the double-precision WMC is kept as a cross-check.
"""
from __future__ import annotations

from typing import Dict, Iterable, Sequence

from pysdd.sdd import SddManager, Vtree


class ExactSddCounter:
    def __init__(self, n_vars: int, var_order: Sequence[int] | None = None):
        order = list(var_order) if var_order else list(range(1, n_vars + 1))
        self.n_vars = n_vars
        self.mgr = SddManager.from_vtree(
            Vtree(var_count=n_vars, var_order=order, vtree_type='balanced'))
        self.mgr.auto_gc_and_minimize_on()

    def compile(self, clauses: Iterable[Sequence[int]]):
        """CNF → SDD. The result is referenced; release it with ``node.deref()``."""
        f = self.mgr.true()
        f.ref()
        for clause in clauses:
            c = self.mgr.false()
            for lit in clause:
                c = c | self.mgr.literal(lit)
            g = f & c
            g.ref()
            f.deref()
            f = g
        return f

    def conjoin(self, a, b):
        g = a & b
        g.ref()
        return g

    def count(self, node) -> int:
        """#models of ``node`` over all ``n_vars`` variables (exact)."""
        memo: Dict[int, int] = {}

        def vars_of(v) -> int:
            return 0 if v is None else v.var_count()

        def over(n, v) -> int:              # models of n over vars(v); vtree(n) ⊆ v
            if n.is_false():
                return 0
            if n.is_true():
                return 1 << vars_of(v)
            w = n.vtree()
            if n.is_literal():
                base = 1
            else:
                base = memo.get(n.id)
                if base is None:
                    base = sum(over(p, w.left()) * over(s, w.right()) for p, s in n.elements())
                    memo[n.id] = base
            return base << (vars_of(v) - vars_of(w))

        exact = over(node, self.mgr.vtree()) if not (node.is_true() or node.is_false()) \
            else (0 if node.is_false() else 1 << self.n_vars)
        wmc = node.wmc(log_mode=False)    # its WmcManager freezes the vtree while alive
        approx = wmc.propagate()
        del wmc
        self.mgr.set_prevent_transformation(prevent=False)
        assert exact == 0 and approx == 0 or abs(exact - approx) <= 1e-9 * max(exact, approx), \
            (exact, approx)
        return exact
