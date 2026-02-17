"""
Query generation for interactive constraint acquisition.

Implements SAT-based query generation strategy:
Find configuration q that satisfies KB ∪ BG but violates some c ∈ Bias.
"""

import logging
from typing import Optional, Dict, List, Tuple
from pysat.solvers import Solver

from acqmss.algorithms.interactive.task import InteractiveTask
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


class QueryGenerator:
    """
    SAT-based query generator for interactive learning.

    Strategy:
    For each constraint c in remaining Bias:
        1. Build formula: KB ∪ BG ∪ ¬c
        2. If SAT, the model is a query that "tests" constraint c
        3. Return the query configuration

    The query is a configuration that:
    - Satisfies all constraints in KB (what we've learned)
    - Satisfies background knowledge BG
    - Violates constraint c (the constraint we're testing)

    If Oracle says the query is valid → c is NOT in ground truth → remove c from Bias
    If Oracle says the query is invalid → c IS in ground truth → add c to KB

    Attributes:
        solver_name: Name of PySAT solver to use
        profiler: Profiler for metrics tracking
    """

    def __init__(self, solver_name: str = 'glucose4',
                 profiler_instance: AbstractProfiler = None) -> None:
        """
        Initialize query generator.

        Args:
            solver_name: PySAT solver name (e.g., 'glucose4', 'minisat22')
            profiler_instance: Optional profiler for metrics
        """
        self.solver_name = solver_name
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()

    @measure_time('query_generation_runtime')
    @count_calls('query_generation_calls')
    def generate(self, task: InteractiveTask) -> Tuple[Optional[Dict[str, bool]], Optional[str]]:
        """
        Generate a query that tests some constraint in the Bias.

        Strategy:
        For each c in Bias, try to find SAT(KB ∪ BG ∪ ¬c).
        If SAT, return the configuration as a query.

        Args:
            task: Current InteractiveTask state

        Returns:
            Tuple of (query_config, tested_constraint_id):
            - query_config: Configuration dict {feature: bool} or None if no query possible
            - tested_constraint_id: ID of constraint being tested or None
        """
        logging.debug('QueryGenerator: KB=%d, Bias=%d, BG=%d',
                      len(task.learned_kb), len(task.bias), len(task.background))

        # Get KB clauses
        kb_clauses = task.get_kb_clauses()

        # Try each constraint in the bias
        for c_id in task.bias:
            # Get negated constraint clauses
            if c_id not in task.negated_constraint_map:
                logging.warning('No negated form for constraint %s, skipping', c_id)
                continue

            neg_c_clauses = task.negated_constraint_map[c_id]

            # Build formula: KB ∪ BG ∪ ¬c
            query_result = self._try_generate_for_constraint(
                kb_clauses=kb_clauses,
                bg_clauses=task.background,
                neg_c_clauses=neg_c_clauses,
                feature_ids=task.feature_ids,
                id_to_feature=task.id_to_feature
            )

            if query_result is not None:
                logging.debug('Generated query testing constraint %s', c_id)
                return query_result, c_id

        # No query could be generated
        logging.debug('No query possible - all constraints in Bias are implied by KB ∪ BG')
        return None, None

    @count_calls('sat_checks_query_gen')
    def _try_generate_for_constraint(
            self,
            kb_clauses: List[List[int]],
            bg_clauses: List[int],
            neg_c_clauses: List[List[int]],
            feature_ids: Dict[str, int],
            id_to_feature: Dict[int, str]
    ) -> Optional[Dict[str, bool]]:
        """
        Try to generate a query that violates a specific constraint.

        Checks if SAT(KB ∪ BG ∪ ¬c).

        Args:
            kb_clauses: CNF clauses from learned KB
            bg_clauses: Background knowledge as unit clause assumptions
            neg_c_clauses: Negated constraint clauses
            feature_ids: Feature name to variable ID mapping
            id_to_feature: Variable ID to feature name mapping

        Returns:
            Configuration dict if SAT, None if UNSAT
        """
        # Build the full formula
        all_clauses = []

        # Add KB clauses
        all_clauses.extend(kb_clauses)

        # Add BG as unit clauses (if given as literals)
        # BG might be a list of literals or list of clauses
        if bg_clauses:
            if isinstance(bg_clauses[0], int):
                # BG is list of literals - add as unit clauses
                for lit in bg_clauses:
                    all_clauses.append([lit])
            else:
                # BG is list of clauses
                all_clauses.extend(bg_clauses)

        # Add negated constraint
        all_clauses.extend(neg_c_clauses)

        # Create solver and check SAT
        solver = Solver(name=self.solver_name, bootstrap_with=all_clauses)
        try:
            with self.profiler.timer('sat_solve_time'):
                is_sat = solver.solve()

            if is_sat:
                model = solver.get_model()
                # Convert model to configuration
                config = self._model_to_config(model, id_to_feature)
                return config
            else:
                return None
        finally:
            solver.delete()

    def _model_to_config(self, model: List[int],
                         id_to_feature: Dict[int, str]) -> Dict[str, bool]:
        """
        Convert SAT model to configuration dictionary.

        Args:
            model: List of literals from SAT solver
            id_to_feature: Variable ID to feature name mapping

        Returns:
            Configuration as {feature_name: True/False}
        """
        config = {}
        for lit in model:
            var = abs(lit)
            if var in id_to_feature:
                config[id_to_feature[var]] = lit > 0
        return config

    def generate_with_priority(
            self,
            task: InteractiveTask,
            priority_fn=None
    ) -> Tuple[Optional[Dict[str, bool]], Optional[str]]:
        """
        Generate query with constraint priority ordering.

        Allows custom ordering of constraints to test, which can
        improve learning efficiency.

        Args:
            task: Current InteractiveTask state
            priority_fn: Function(constraint_id, constraint_clauses) -> priority_score
                        Higher scores are tested first. Default: None (original order)

        Returns:
            Tuple of (query_config, tested_constraint_id)
        """
        if priority_fn is None:
            return self.generate(task)

        # Sort bias by priority
        sorted_bias = sorted(
            task.bias,
            key=lambda c_id: priority_fn(c_id, task.constraint_map.get(c_id, [])),
            reverse=True  # Higher priority first
        )

        # Get KB clauses
        kb_clauses = task.get_kb_clauses()

        for c_id in sorted_bias:
            if c_id not in task.negated_constraint_map:
                continue

            neg_c_clauses = task.negated_constraint_map[c_id]
            query_result = self._try_generate_for_constraint(
                kb_clauses=kb_clauses,
                bg_clauses=task.background,
                neg_c_clauses=neg_c_clauses,
                feature_ids=task.feature_ids,
                id_to_feature=task.id_to_feature
            )

            if query_result is not None:
                return query_result, c_id

        return None, None


def clause_count_priority(c_id: str, clauses: List[List[int]]) -> int:
    """
    Priority function based on clause count.

    Constraints with more clauses may be more informative.

    Args:
        c_id: Constraint ID
        clauses: Constraint clauses

    Returns:
        Number of clauses (higher = more priority)
    """
    return len(clauses)


def literal_count_priority(c_id: str, clauses: List[List[int]]) -> int:
    """
    Priority function based on total literal count.

    Larger constraints (more literals) may be more complex.

    Args:
        c_id: Constraint ID
        clauses: Constraint clauses

    Returns:
        Total literal count
    """
    return sum(len(c) for c in clauses)
