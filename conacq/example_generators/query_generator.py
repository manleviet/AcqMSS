"""
Query generation for interactive constraint acquisition.

Implements SAT-based query generation strategy:
Find configuration q that satisfies KB ∪ BG but violates some c ∈ Bias.

Supports both QuAcqTask (int assumption IDs) and InteractiveTask (str IDs).
"""

import logging
from typing import Any, Optional, Dict, List, Tuple, Union
from pysat.solvers import Solver

from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)
from conacq.algorithms.quacq._task_compat import get_bg_clauses


def _get_negated_clauses(task, c_id):
    """Get negated clauses for a constraint from either task type.

    Returns None (not []) when no negated form exists, to distinguish
    'no negation available' from 'empty negation'.
    """
    if hasattr(task, 'negated_clauses') and isinstance(c_id, int):
        return task.negated_clauses.get(c_id)
    if hasattr(task, 'negated_constraint_map'):
        return task.negated_constraint_map.get(c_id)
    return None


def _get_clause_map_for_priority(task, c_id):
    """Get clause map for priority function from either task type."""
    if hasattr(task, 'constraint_clauses') and isinstance(c_id, int):
        return task.constraint_clauses.get(c_id, [])
    if hasattr(task, 'constraint_map'):
        return task.constraint_map.get(c_id, [])
    return []


class QueryGenerator:
    """
    SAT-based query generator for interactive learning.

    Accepts both QuAcqTask (int IDs) and InteractiveTask (str IDs).
    """

    def __init__(self, solver_name: str = 'glucose4',
                 profiler_instance: AbstractProfiler = None) -> None:
        self.solver_name = solver_name
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()

    @measure_time('query_generation_runtime')
    @count_calls('query_generation_calls')
    def generate(self, task, remaining_bias: set = None,
                 learned_kb: list = None) -> Tuple[Optional[Dict[str, bool]], Any]:
        """
        Generate a query that tests some constraint in the Bias.

        Args:
            task: QuAcqTask or InteractiveTask state
            remaining_bias: Current bias set (required for QuAcqTask)
            learned_kb: Current learned KB list (required for QuAcqTask)

        Returns:
            Tuple of (query_config, tested_constraint_id)
        """
        # Resolve bias and KB from params or task (backward compat)
        bias = remaining_bias if remaining_bias is not None else getattr(task, 'bias', set())
        kb = learned_kb if learned_kb is not None else getattr(task, 'learned_kb', [])

        logging.debug('QueryGenerator: KB=%d, Bias=%d, BG=%d',
                      len(kb), len(bias), len(task.set_b))

        kb_clauses = task.get_kb_clauses(kb) if learned_kb is not None else task.get_kb_clauses(kb)

        for c_id in bias:
            neg_c_clauses = _get_negated_clauses(task, c_id)
            if neg_c_clauses is None:
                logging.warning('No negated form for constraint %s, skipping', c_id)
                continue

            query_result = self._try_generate_for_constraint(
                kb_clauses=kb_clauses,
                bg_clauses=get_bg_clauses(task),
                neg_c_clauses=neg_c_clauses,
                feature_ids=task.feature_ids,
                id_to_feature=task.id_to_feature
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
            task,
            remaining_bias: set = None,
            learned_kb: list = None,
            priority_fn=None
    ) -> Tuple[Optional[Dict[str, bool]], Any]:
        """Generate query with constraint priority ordering."""
        if priority_fn is None:
            return self.generate(task, remaining_bias, learned_kb)

        bias = remaining_bias if remaining_bias is not None else getattr(task, 'bias', set())
        kb = learned_kb if learned_kb is not None else getattr(task, 'learned_kb', [])

        sorted_bias = sorted(
            bias,
            key=lambda c_id: priority_fn(c_id, _get_clause_map_for_priority(task, c_id)),
            reverse=True
        )

        kb_clauses = task.get_kb_clauses(kb)

        for c_id in sorted_bias:
            neg_c_clauses = _get_negated_clauses(task, c_id)
            if neg_c_clauses is None:
                continue

            query_result = self._try_generate_for_constraint(
                kb_clauses=kb_clauses,
                bg_clauses=get_bg_clauses(task),
                neg_c_clauses=neg_c_clauses,
                feature_ids=task.feature_ids,
                id_to_feature=task.id_to_feature
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
