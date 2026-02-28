"""
Unified query provider for QuAcq constraint acquisition.

Merges pool-based (ExampleProvider) and SAT-based (QueryGenerator) strategies
into single class with paper-aligned pool filtering.

Paper condition for pool: query in sol(C_L + BG) AND violates >=1 c in B.
"""

import logging
import random
from typing import Optional, Dict, List, Tuple

from pysat.solvers import Solver

from conacq.algorithms.quacq.sat_utils import config_to_assumptions, violates_clauses
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


class QueryProvider:
    """Unified query provider: pool-filtered + SAT-based strategies.

    Replaces ExampleProvider (pool) + QueryGenerator (SAT).
    Pool filtering follows paper: query in sol(C_L + BG) AND violates >=1 c in B.

    Args:
        solver_name: PySAT solver name (default: glucose4)
        pool: Optional list of example configs for pool-based generation
        seed: Random seed for pool shuffling
        profiler_instance: Optional profiler for timing/counting
    """

    def __init__(self, solver_name: str = 'glucose4',
                 pool: Optional[List[Dict[str, bool]]] = None,
                 seed: Optional[int] = None,
                 profiler_instance: Optional[AbstractProfiler] = None) -> None:
        self.solver_name = solver_name
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()

        # Pool state
        self._pool: List[Dict[str, bool]] = []
        self._pool_index: int = 0
        # Initializes pool state with optional seeded shuffling
        if pool is not None:
            self._pool = list(pool)
            if seed is not None:
                random.Random(seed).shuffle(self._pool)
            else:
                random.shuffle(self._pool)

    @property
    def pool_exhausted(self) -> bool:
        """Check if pool has been fully consumed."""
        return self._pool_index >= len(self._pool)

    @property
    def pool_remaining(self) -> int:
        """Number of pool examples remaining."""
        return max(0, len(self._pool) - self._pool_index)

    @count_calls('pool_generation_calls')
    def generate_from_pool(
            self,
            remaining_bias: set,
            kb_clauses: List[List[int]],
            bg_clauses: List[List[int]],
            constraint_clauses: Dict[int, List[List[int]]],
            feature_ids: Dict[str, int],
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Generate query from pool with paper filtering.

        Paper condition: query in sol(C_L + BG) AND violates >=1 c in B.

        Returns:
            Tuple of (query_config, violated_constraint_id) or (None, None)
        """
        formula = kb_clauses + bg_clauses

        while self._pool_index < len(self._pool):
            e = self._pool[self._pool_index]
            self._pool_index += 1

            # Condition 1: satisfies C_L + BG
            assumptions = config_to_assumptions(e, feature_ids)
            if not self._satisfies_formula(formula, assumptions):
                continue

            # Condition 2: violates >=1 constraint in remaining_bias
            assignment = {abs(lit): lit > 0 for lit in assumptions}
            for c_id in remaining_bias:
                clauses = constraint_clauses.get(c_id)
                if clauses and violates_clauses(clauses, assignment):
                    logging.debug('Pool query found testing constraint %s', c_id)
                    return e, c_id

        logging.debug('Pool exhausted (%d examples checked)', self._pool_index)
        return None, None

    def _satisfies_formula(self, clauses: List[List[int]],
                           assumptions: List[int]) -> bool:
        """Check if assumptions satisfy the given CNF formula."""
        if not clauses:
            return True
        solver = Solver(name=self.solver_name, bootstrap_with=clauses)
        try:
            return solver.solve(assumptions=assumptions)
        finally:
            solver.delete()

    @measure_time('query_generation_runtime')
    @count_calls('query_generation_calls')
    def generate_from_sat(
            self,
            remaining_bias: set,
            learned_kb: list,
            kb_clauses: List[List[int]],
            negated_clauses: Dict[int, List[List[int]]],
            bg_clauses: List[List[int]],
            feature_ids: Dict[str, int],
            id_to_feature: Dict[int, str],
            n_bg: int = 0,
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Generate query via SAT solving (matches paper Algorithm 1).

        Find config satisfying KB + BG but violating some c in Bias.
        """
        logging.debug('QueryProvider SAT: KB=%d, Bias=%d, BG=%d',
                      len(learned_kb), len(remaining_bias), n_bg)

        for c_id in remaining_bias:
            neg_c_clauses = negated_clauses.get(c_id)
            if neg_c_clauses is None:
                logging.warning('No negated form for constraint %s, skipping', c_id)
                continue

            query_result = self._try_generate_for_constraint(
                kb_clauses=kb_clauses, bg_clauses=bg_clauses,
                neg_c_clauses=neg_c_clauses, feature_ids=feature_ids,
                id_to_feature=id_to_feature)

            if query_result is not None:
                logging.debug('SAT query testing constraint %s', c_id)
                return query_result, c_id

        logging.debug('No SAT query possible - all bias implied by KB + BG')
        return None, None

    def generate(
            self,
            remaining_bias: set,
            learned_kb: list,
            kb_clauses: List[List[int]],
            negated_clauses: Dict[int, List[List[int]]],
            bg_clauses: List[List[int]],
            feature_ids: Dict[str, int],
            id_to_feature: Dict[int, str],
            constraint_clauses: Dict[int, List[List[int]]],
            n_bg: int = 0,
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Pool first, then SAT fallback."""
        if not self.pool_exhausted:
            result = self.generate_from_pool(
                remaining_bias, kb_clauses, bg_clauses,
                constraint_clauses, feature_ids)
            if result[0] is not None:
                return result

        return self.generate_from_sat(
            remaining_bias, learned_kb, kb_clauses,
            negated_clauses, bg_clauses, feature_ids,
            id_to_feature, n_bg)

    @count_calls('sat_checks_query_gen')
    def _try_generate_for_constraint(
            self, kb_clauses, bg_clauses, neg_c_clauses,
            feature_ids, id_to_feature):
        """Try to generate query violating specific constraint."""
        all_clauses = list(kb_clauses) + list(bg_clauses) + list(neg_c_clauses)
        solver = Solver(name=self.solver_name, bootstrap_with=all_clauses)
        try:
            with self.profiler.timer('sat_solve_time'):
                is_sat = solver.solve()
            if is_sat:
                return self._model_to_config(solver.get_model(), id_to_feature)
            return None
        finally:
            solver.delete()

    def _model_to_config(self, model, id_to_feature):
        """Convert SAT model to configuration dictionary."""
        config = {}
        for lit in model:
            var = abs(lit)
            if var in id_to_feature:
                config[id_to_feature[var]] = lit > 0
        return config
