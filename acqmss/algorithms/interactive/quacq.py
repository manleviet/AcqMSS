"""
QuAcq algorithm for interactive constraint acquisition.

Implements the QuAcq learning loop:
1. Generate query that tests some constraint in Bias
2. Ask Oracle for membership answer
3. If positive: prune constraints that reject the query
4. If negative: find minimal conflict using QuickXPlain, add to KB
5. Repeat until Bias is empty or no more queries possible
6. Apply REDUCE to remove redundant constraints
"""

import logging
import time
from typing import List, Dict, Optional, Set

from pysat.solvers import Solver

from .task import InteractiveTask
from .result import InteractiveResult
from .user_interface import InteractiveOracle
from .query_generator import QueryGenerator
from acqmss.algorithms.reduce import Reduce
from explanation.operations.algorithms.checker import NonIncrementalPySATChecker
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


class QuAcq:
    """
    QuAcq algorithm for interactive constraint acquisition.

    Algorithm:
    ```
    QuAcq(B, BG, Oracle):
      KB <- empty
      while B is not empty:
        1. q <- GenerateQuery(KB, B, BG)
        2. answer <- Oracle.is_valid(q)
        3. if answer == True:
             B <- B - {c : c rejects q}
           else:
             conflict <- FindConflict(B, KB∪BG∪{q})
             KB <- KB ∪ conflict
             B <- B - conflict
      return REDUCE(KB, BG)
    ```

    Attributes:
        solver_name: SAT solver name
        profiler: Profiler for metrics
        query_generator: Query generation strategy
    """

    def __init__(self, solver_name: str = 'glucose4',
                 profiler_instance: AbstractProfiler = None) -> None:
        """
        Initialize QuAcq algorithm.

        Args:
            solver_name: PySAT solver name
            profiler_instance: Optional profiler for metrics
        """
        self.solver_name = solver_name
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()
        self.query_generator = QueryGenerator(solver_name, self.profiler)
        self.result: Optional[InteractiveResult] = None

    @measure_time('quacq_runtime')
    @count_calls('quacq_calls')
    def learn(self, task: InteractiveTask, oracle: InteractiveOracle,
              max_queries: int = 1000) -> InteractiveResult:
        """
        Run QuAcq learning loop.

        Args:
            task: InteractiveTask with initial state (bias, constraint maps)
            oracle: Oracle for membership queries
            max_queries: Maximum number of queries before stopping

        Returns:
            InteractiveResult with learned KB and statistics
        """
        start_time = time.perf_counter()
        convergence_reason = ''

        logging.info('QuAcq starting: Bias=%d constraints', len(task.bias))

        # Main learning loop
        while task.bias:
            # Check query limit
            if task.n_queries >= max_queries:
                convergence_reason = 'max_queries'
                logging.info('Reached max queries limit: %d', max_queries)
                break

            # Step 1: Generate query
            query, tested_c_id = self.query_generator.generate(task)

            if query is None:
                # No more discriminating queries possible
                convergence_reason = 'no_query'
                logging.info('No more queries possible - converged')
                break

            # Step 2: Ask oracle
            answer = oracle.ask(query)
            task.record_query(query, answer)

            logging.debug('Query %d: answer=%s, testing constraint %s',
                          task.n_queries, answer, tested_c_id)

            # Step 3-4: Process answer
            if answer:
                # Positive example: prune constraints that reject this config
                pruned = self._prune_rejecting_constraints(task, query)
                logging.debug('Pruned %d constraints', len(pruned))
            else:
                # Negative example: find minimal conflict and add to KB
                conflict = self._find_conflict(task, query)
                if conflict:
                    for c_id in conflict:
                        task.add_to_kb(c_id)
                    task.remove_from_bias(conflict)
                    logging.debug('Added %d constraints to KB: %s', len(conflict), conflict)
                else:
                    # No conflict found - shouldn't happen if bias is correct
                    logging.warning('No conflict found for negative example')
                    # At minimum, add the tested constraint
                    if tested_c_id:
                        task.add_to_kb(tested_c_id)
                        task.remove_from_bias([tested_c_id])

        if not task.bias:
            convergence_reason = 'empty_bias'
            logging.info('Bias exhausted - converged')

        # Step 5: Apply REDUCE to remove redundant constraints
        final_kb = self._reduce_kb(task)

        # Calculate runtime
        runtime_ms = (time.perf_counter() - start_time) * 1000

        # Get consistency check count from profiler
        consistency_checks = self.profiler.get_metric('sat_checks_query_gen', 0)
        if isinstance(consistency_checks, list):
            consistency_checks = len(consistency_checks)

        self.result = InteractiveResult(
            kb_constraints=final_kb,
            n_queries=task.n_queries,
            n_kb=len(final_kb),
            convergence_reason=convergence_reason,
            runtime_ms=runtime_ms,
            consistency_checks=consistency_checks,
            metadata={
                'initial_bias_size': len(task.constraint_map),
                'remaining_bias_size': len(task.bias),
                'learned_before_reduce': len(task.learned_kb)
            },
            query_history=task.query_history
        )

        logging.info('QuAcq finished: KB=%d, queries=%d, reason=%s',
                     len(final_kb), task.n_queries, convergence_reason)

        return self.result

    @count_calls('prune_calls')
    def _prune_rejecting_constraints(self, task: InteractiveTask,
                                     positive_example: Dict[str, bool]) -> List[str]:
        """
        Remove constraints from Bias that reject the positive example.

        A constraint c rejects example e if e violates c.

        Args:
            task: Current task state
            positive_example: Configuration that oracle confirmed as valid

        Returns:
            List of pruned constraint IDs
        """
        # Convert example to assumption literals
        assumptions = task.config_to_assumptions(positive_example)

        pruned = []
        for c_id in list(task.bias):  # Iterate over copy
            clauses = task.constraint_map.get(c_id, [])
            if self._violates_constraint(assumptions, clauses):
                pruned.append(c_id)

        task.remove_from_bias(pruned)
        return pruned

    def _violates_constraint(self, assumptions: List[int],
                             constraint_clauses: List[List[int]]) -> bool:
        """
        Check if configuration violates a constraint.

        Args:
            assumptions: Configuration as SAT literals
            constraint_clauses: Constraint CNF clauses

        Returns:
            True if configuration violates the constraint
        """
        # Build assignment from assumptions
        assignment = {abs(lit): lit > 0 for lit in assumptions}

        # Check each clause
        for clause in constraint_clauses:
            # Clause is satisfied if at least one literal is true
            clause_satisfied = False
            for lit in clause:
                var = abs(lit)
                if var in assignment:
                    if (lit > 0 and assignment[var]) or (lit < 0 and not assignment[var]):
                        clause_satisfied = True
                        break
            if not clause_satisfied:
                return True  # At least one clause is violated

        return False  # All clauses satisfied

    @count_calls('find_conflict_calls')
    def _find_conflict(self, task: InteractiveTask,
                       negative_example: Dict[str, bool]) -> List[str]:
        """
        Find minimal conflict set using divide-and-conquer.

        When oracle returns "invalid", we find a minimal subset of Bias
        that explains the rejection.

        This is a simplified version of QuickXPlain adapted for constraint IDs.

        Args:
            task: Current task state
            negative_example: Configuration that oracle rejected

        Returns:
            List of constraint IDs forming minimal conflict
        """
        # Convert example to clauses (unit clauses for each assignment)
        example_clauses = []
        for name, value in negative_example.items():
            if name in task.feature_ids:
                fid = task.feature_ids[name]
                example_clauses.append([fid if value else -fid])

        # Build background: KB ∪ BG ∪ {example}
        bg_clauses = task.get_kb_clauses()

        # Add BG
        if task.background:
            if isinstance(task.background[0], int):
                for lit in task.background:
                    bg_clauses.append([lit])
            else:
                bg_clauses.extend(task.background)

        # Add example
        bg_clauses.extend(example_clauses)

        # Find minimal conflict among Bias constraints
        bias_constraints = list(task.bias)
        conflict = self._quickxplain_constraints(
            constraint_ids=[],
            remaining=bias_constraints,
            background=bg_clauses,
            constraint_map=task.constraint_map
        )

        return conflict

    def _quickxplain_constraints(
            self,
            constraint_ids: List[str],
            remaining: List[str],
            background: List[List[int]],
            constraint_map: Dict[str, List[List[int]]]
    ) -> List[str]:
        """
        QuickXPlain adapted for constraint IDs.

        Finds minimal conflict set C ⊆ remaining such that
        background ∪ C is inconsistent.

        Args:
            constraint_ids: Already confirmed conflict constraints
            remaining: Constraints to search among
            background: Background clauses
            constraint_map: Constraint ID to clauses mapping

        Returns:
            Minimal conflict subset of remaining
        """
        logging.debug('QuickXPlain: delta=%d, remaining=%d',
                      len(constraint_ids), len(remaining))

        # If delta is non-empty and background alone is inconsistent, return empty
        if constraint_ids and not self._is_consistent(background):
            return []

        # If remaining is empty, return empty
        if not remaining:
            return []

        # If remaining has single element, return it (it's the conflict)
        if len(remaining) == 1:
            return remaining

        # Split remaining in half
        k = len(remaining) // 2
        c1 = remaining[:k]
        c2 = remaining[k:]

        # Recursively find conflict in each half
        # cs1 = QX(c2, c1, background ∪ clauses(c2))
        c2_clauses = self._get_clauses_for_constraints(c2, constraint_map)
        cs1 = self._quickxplain_constraints(
            constraint_ids=c2,
            remaining=c1,
            background=background + c2_clauses,
            constraint_map=constraint_map
        )

        # cs2 = QX(cs1, c2, background ∪ clauses(cs1))
        cs1_clauses = self._get_clauses_for_constraints(cs1, constraint_map)
        cs2 = self._quickxplain_constraints(
            constraint_ids=cs1,
            remaining=c2,
            background=background + cs1_clauses,
            constraint_map=constraint_map
        )

        return cs1 + cs2

    def _get_clauses_for_constraints(self, constraint_ids: List[str],
                                     constraint_map: Dict[str, List[List[int]]]) -> List[List[int]]:
        """Get all clauses for a list of constraints."""
        clauses = []
        for c_id in constraint_ids:
            clauses.extend(constraint_map.get(c_id, []))
        return clauses

    @count_calls('is_consistent_calls')
    def _is_consistent(self, clauses: List[List[int]]) -> bool:
        """
        Check if clause set is consistent (satisfiable).

        Args:
            clauses: CNF clauses to check

        Returns:
            True if satisfiable
        """
        if not clauses:
            return True

        solver = Solver(name=self.solver_name, bootstrap_with=clauses)
        try:
            with self.profiler.timer('sat_solve_time'):
                result = solver.solve()
            return result
        finally:
            solver.delete()

    def _reduce_kb(self, task: InteractiveTask) -> List[str]:
        """
        Apply REDUCE to remove redundant constraints from learned KB.

        Args:
            task: Task with learned KB

        Returns:
            Non-redundant constraint IDs
        """
        if not task.learned_kb:
            return []

        # Build checker for non-incremental REDUCE
        checker = NonIncrementalPySATChecker(self.solver_name, self.profiler)

        reduce = Reduce(checker, self.profiler)

        # Prepare inputs for REDUCE
        # set_b_prime = learned constraints as clause lists
        # set_ne = empty (no separate NE in interactive mode)
        # set_bg = background clauses
        # neg_map = negated constraint map

        # For non-incremental mode, we work with clause lists
        set_b_prime = [task.constraint_map[c_id] for c_id in task.learned_kb
                       if c_id in task.constraint_map]

        # Build negation map (tuple -> negated clauses)
        neg_map = {}
        for c_id in task.learned_kb:
            if c_id in task.constraint_map and c_id in task.negated_constraint_map:
                clauses = task.constraint_map[c_id]
                key = tuple(tuple(c) for c in clauses)
                neg_map[key] = task.negated_constraint_map[c_id]

        # BG as clause lists
        set_bg = []
        if task.background:
            if task.background and isinstance(task.background[0], int):
                set_bg = [[[lit]] for lit in task.background]
            else:
                set_bg = [[c] for c in task.background]

        try:
            redundant, non_redundant = reduce.reduce(
                set_b_prime=set_b_prime,
                set_ne=[],
                set_bg=set_bg,
                neg_map=neg_map
            )

            # Map back to constraint IDs
            non_redundant_ids = []
            clause_to_id = {}
            for c_id in task.learned_kb:
                if c_id in task.constraint_map:
                    key = tuple(tuple(c) for c in task.constraint_map[c_id])
                    clause_to_id[key] = c_id

            for clauses in non_redundant:
                key = tuple(tuple(c) for c in clauses)
                if key in clause_to_id:
                    non_redundant_ids.append(clause_to_id[key])

            return non_redundant_ids

        except Exception as e:
            logging.warning('REDUCE failed: %s, returning learned KB as-is', e)
            return task.learned_kb
