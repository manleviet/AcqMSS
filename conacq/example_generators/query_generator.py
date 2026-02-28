"""
Query generation for interactive constraint acquisition.

Implements SAT-based query generation strategy:
Find configuration q that satisfies KB ∪ BG but violates some c ∈ Bias.
"""

import logging
from typing import Optional, Dict, List, Tuple
from pysat.solvers import Solver

from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


class QueryGenerator:
    """SAT-based query generator for interactive learning."""

    def __init__(self, solver_name: str = 'glucose4',
                 profiler_instance: AbstractProfiler = None) -> None:
        self.solver_name = solver_name
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()

    @measure_time('query_generation_runtime')
    @count_calls('query_generation_calls')
    def generate(self,
                 remaining_bias: set,
                 learned_kb: list,
                 kb_clauses: List[List[int]],
                 negated_clauses: Dict[int, List[List[int]]],
                 bg_clauses: List[List[int]],
                 feature_ids: Dict[str, int],
                 id_to_feature: Dict[int, str],
                 n_bg: int = 0,
                 ) -> Tuple[Optional[Dict[str, bool]], int]:
        """Generate a query that tests some constraint in the Bias.

        Args:
            remaining_bias: Current bias set of assumption IDs
            learned_kb: Current learned KB list
            kb_clauses: Raw CNF clauses for learned KB
            negated_clauses: assumption_id -> negated CNF clauses
            bg_clauses: Background CNF clauses
            feature_ids: Feature name -> SAT variable ID
            id_to_feature: SAT variable ID -> feature name
            n_bg: Number of BG constraints (for logging)

        Returns:
            Tuple of (query_config, tested_constraint_id)
        """
        logging.debug('QueryGenerator: KB=%d, Bias=%d, BG=%d',
                      len(learned_kb), len(remaining_bias), n_bg)

        for c_id in remaining_bias:
            neg_c_clauses = negated_clauses.get(c_id)
            if neg_c_clauses is None:
                logging.warning('No negated form for constraint %s, skipping', c_id)
                continue

            query_result = self._try_generate_for_constraint(
                kb_clauses=kb_clauses,
                bg_clauses=bg_clauses,
                neg_c_clauses=neg_c_clauses,
                feature_ids=feature_ids,
                id_to_feature=id_to_feature
            )

            if query_result is not None:
                logging.debug('Generated query testing constraint %s', c_id)
                return query_result, c_id

        logging.debug('No query possible - all constraints in Bias are implied by KB ∪ BG')
        return None, None

    @count_calls('sat_checks_query_gen')
    def _try_generate_for_constraint(
            self,
            kb_clauses: List[List[int]],
            bg_clauses: list,
            neg_c_clauses: List[List[int]],
            feature_ids: Dict[str, int],
            id_to_feature: Dict[int, str]
    ) -> Optional[Dict[str, bool]]:
        """Try to generate a query that violates a specific constraint."""
        all_clauses = []
        all_clauses.extend(kb_clauses)
        all_clauses.extend(bg_clauses)
        all_clauses.extend(neg_c_clauses)

        solver = Solver(name=self.solver_name, bootstrap_with=all_clauses)
        try:
            with self.profiler.timer('sat_solve_time'):
                is_sat = solver.solve()

            if is_sat:
                model = solver.get_model()
                config = self._model_to_config(model, id_to_feature)
                return config
            else:
                return None
        finally:
            solver.delete()

    def _model_to_config(self, model: List[int],
                         id_to_feature: Dict[int, str]) -> Dict[str, bool]:
        """Convert SAT model to configuration dictionary."""
        config = {}
        for lit in model:
            var = abs(lit)
            if var in id_to_feature:
                config[id_to_feature[var]] = lit > 0
        return config

    def generate_with_priority(
            self,
            remaining_bias: set,
            learned_kb: list,
            kb_clauses: List[List[int]],
            negated_clauses: Dict[int, List[List[int]]],
            constraint_clauses: Dict[int, List[List[int]]],
            bg_clauses: List[List[int]],
            feature_ids: Dict[str, int],
            id_to_feature: Dict[int, str],
            priority_fn=None,
            n_bg: int = 0,
    ) -> Tuple[Optional[Dict[str, bool]], int]:
        """Generate query with constraint priority ordering."""
        if priority_fn is None:
            return self.generate(
                remaining_bias, learned_kb, kb_clauses,
                negated_clauses, bg_clauses, feature_ids,
                id_to_feature, n_bg)

        sorted_bias = sorted(
            remaining_bias,
            key=lambda c_id: priority_fn(c_id, constraint_clauses.get(c_id, [])),
            reverse=True
        )

        for c_id in sorted_bias:
            neg_c_clauses = negated_clauses.get(c_id)
            if neg_c_clauses is None:
                continue

            query_result = self._try_generate_for_constraint(
                kb_clauses=kb_clauses,
                bg_clauses=bg_clauses,
                neg_c_clauses=neg_c_clauses,
                feature_ids=feature_ids,
                id_to_feature=id_to_feature
            )

            if query_result is not None:
                return query_result, c_id

        return None, None


def clause_count_priority(c_id, clauses: List[List[int]]) -> int:
    """Priority function based on clause count."""
    return len(clauses)


def literal_count_priority(c_id, clauses: List[List[int]]) -> int:
    """Priority function based on total literal count."""
    return sum(len(c) for c in clauses)
