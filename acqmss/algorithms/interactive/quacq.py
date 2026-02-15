"""
QuAcq algorithm for interactive constraint acquisition.

Supports two modes:
- Oracle-based: traditional QuAcq with oracle membership queries
- Example-based: ExampleProvider + ConsistencyChecker (fair comparison with ConGen)
"""

import logging
import time
from typing import List, Dict, Optional, Set, Literal

from pysat.solvers import Solver

from .task import InteractiveTask
from .result import InteractiveResult
from acqmss.oracle import Oracle
from acqmss.example_generators import QueryGenerator, ExampleProvider
from .findscope import find_scope
from .findc import find_c
from acqmss.algorithms.reduce import Reduce
from acqmss.oracle.fm_oracle_model import OneShotModel
from explanation.operations.algorithms.checker import CheckerFactory, NonIncrementalPySATChecker
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


class QuAcq:
    """
    QuAcq algorithm for interactive constraint acquisition.

    Supports oracle-based mode (learn) and example-based mode (learn_from_examples).
    """

    def __init__(self, solver_name: str = 'glucose4',
                 profiler_instance: AbstractProfiler = None) -> None:
        self.solver_name = solver_name
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()
        self.query_generator = QueryGenerator(solver_name, self.profiler)
        self.result: Optional[InteractiveResult] = None

    @measure_time('quacq_runtime')
    @count_calls('quacq_calls')
    def learn(self, task: InteractiveTask, oracle: Oracle,
              max_queries: int = 1000) -> InteractiveResult:
        """
        Run QuAcq with oracle-based membership queries (original mode).

        Args:
            task: InteractiveTask with initial state
            oracle: Oracle for membership queries
            max_queries: Maximum queries before stopping

        Returns:
            InteractiveResult with learned KB
        """
        start_time = time.perf_counter()
        convergence_reason = ''

        logging.info('QuAcq starting: Bias=%d constraints', len(task.bias))

        while task.bias:
            if task.n_queries >= max_queries:
                convergence_reason = 'max_queries'
                logging.info('Reached max queries limit: %d', max_queries)
                break

            query, tested_c_id = self.query_generator.generate(task)

            if query is None:
                convergence_reason = 'no_query'
                logging.info('No more queries possible - converged')
                break

            answer = oracle.ask(query)
            task.record_query(query, answer)

            logging.debug('Query %d: answer=%s, testing constraint %s',
                          task.n_queries, answer, tested_c_id)

            if answer:
                pruned = self._prune_rejecting_constraints(task, query)
                logging.debug('Pruned %d constraints', len(pruned))
            else:
                conflict = self._find_conflict(task, query)
                if conflict:
                    for c_id in conflict:
                        task.add_to_kb(c_id)
                    task.remove_from_bias(conflict)
                    logging.debug('Added %d constraints to KB: %s', len(conflict), conflict)
                else:
                    logging.warning('No conflict found for negative example')
                    if tested_c_id:
                        task.add_to_kb(tested_c_id)
                        task.remove_from_bias([tested_c_id])

        if not task.bias:
            convergence_reason = 'empty_bias'
            logging.info('Bias exhausted - converged')

        return self._build_result(task, start_time, convergence_reason)

    @measure_time('quacq_example_runtime')
    @count_calls('quacq_example_calls')
    def learn_from_examples(
            self,
            task: InteractiveTask,
            example_provider: ExampleProvider,
            fm_clauses: List[List[int]],
            query_mode: Literal['example_only', 'example_first'] = 'example_only',
            max_queries: int = 10000
    ) -> InteractiveResult:
        """
        Run QuAcq with ExampleProvider + FindScope/FindC.

        Examples drawn from shuffled mixed pool. Validity checked via SAT
        against target FM. Conflict resolution uses FindScope (variable space)
        + FindC (constraint space) per IJCAI13 paper.

        Args:
            task: InteractiveTask with initial state
            example_provider: Shuffled mixed example pool
            fm_clauses: Target FM CNF clauses for consistency checking
            query_mode: 'example_only' or 'example_first'
            max_queries: Maximum queries before stopping

        Returns:
            InteractiveResult with learned KB
        """
        start_time = time.perf_counter()
        convergence_reason = ''
        queries_from_pool = 0
        queries_from_sat = 0

        logging.info('QuAcq (FindScope/FindC) starting: Bias=%d, pool=%d, mode=%s',
                     len(task.bias), example_provider.remaining(), query_mode)

        all_variables = set(task.feature_ids.keys())

        while task.bias:
            if task.n_queries >= max_queries:
                convergence_reason = 'max_queries'
                break

            # Step 1: Get next example
            query = example_provider.next_example()

            if query is not None:
                queries_from_pool += 1
            elif query_mode == 'example_first':
                query, _ = self.query_generator.generate(task)
                if query is not None:
                    queries_from_sat += 1

            if query is None:
                convergence_reason = 'pool_exhausted' if query_mode == 'example_only' else 'no_query'
                logging.info('No more queries: %s', convergence_reason)
                break

            # Step 2: Check validity via ConsistencyChecker against FM
            e_assumptions = task.config_to_assumptions(query)
            is_valid = self._check_consistency_with_fm(fm_clauses, e_assumptions)

            task.record_query(query, is_valid)

            logging.debug('Query %d: valid=%s (pool=%d, sat=%d)',
                          task.n_queries, is_valid, queries_from_pool, queries_from_sat)

            # Step 3-4: Process answer
            if is_valid:
                # Positive: prune constraints that reject this valid config
                pruned = self._prune_rejecting_constraints(task, query)
                logging.debug('Pruned %d constraints', len(pruned))
            else:
                # Negative: use FindScope + FindC to identify constraint
                scope_vars = find_scope(
                    e=query,
                    R=set(),
                    Y=all_variables,
                    ask_query=False,
                    fm_clauses=fm_clauses,
                    task=task,
                    solver_name=self.solver_name,
                    profiler=self.profiler
                )

                scope = set(scope_vars)
                if scope:
                    c_id = find_c(
                        e=query,
                        scope=scope,
                        task=task,
                        fm_clauses=fm_clauses,
                        example_provider=example_provider,
                        solver_name=self.solver_name,
                        query_mode=query_mode,
                        profiler=self.profiler
                    )

                    if c_id is not None:
                        task.add_to_kb(c_id)
                        task.remove_from_bias([c_id])
                        logging.debug('FindScope/FindC added constraint: %s', c_id)
                    else:
                        logging.warning('FindC returned no constraint for scope %s', scope)
                else:
                    # Fallback to QuickXPlain if FindScope returns empty
                    conflict = self._find_conflict(task, query)
                    if conflict:
                        for c_id in conflict:
                            task.add_to_kb(c_id)
                        task.remove_from_bias(conflict)
                        logging.debug('Fallback conflict: %s', conflict)
                    else:
                        logging.warning('No conflict found for negative example')

        if not task.bias:
            convergence_reason = 'empty_bias'

        result = self._build_result(task, start_time, convergence_reason)
        result.metadata['queries_from_pool'] = queries_from_pool
        result.metadata['queries_from_sat'] = queries_from_sat
        result.metadata['query_mode'] = query_mode
        return result

    def _check_consistency_with_fm(self, fm_clauses: List[List[int]],
                                    e_assumptions: List[int]) -> bool:
        """Check if example is consistent with FM via OneShotModel + checker."""
        model = OneShotModel(fm_clauses, e_assumptions)
        checker = CheckerFactory.create_from_model(model, self.solver_name, self.profiler)
        try:
            return checker.is_consistent([])
        finally:
            checker.cleanup()

    def _build_result(self, task: InteractiveTask, start_time: float,
                      convergence_reason: str) -> InteractiveResult:
        """Build InteractiveResult from task state."""
        final_kb = self._reduce_kb(task)
        runtime_ms = (time.perf_counter() - start_time) * 1000

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
        """Remove constraints from Bias that reject the positive example."""
        assumptions = task.config_to_assumptions(positive_example)

        assignment = {abs(lit): lit > 0 for lit in assumptions}

        pruned = []
        for c_id in list(task.bias):
            clauses = task.constraint_map.get(c_id, [])
            if task.violates_clauses(clauses, assignment):
                pruned.append(c_id)

        task.remove_from_bias(pruned)
        return pruned

    @count_calls('find_conflict_calls')
    def _find_conflict(self, task: InteractiveTask,
                       negative_example: Dict[str, bool]) -> List[str]:
        """Find minimal conflict set using QuickXPlain on constraint IDs."""
        example_clauses = []
        for name, value in negative_example.items():
            if name in task.feature_ids:
                fid = task.feature_ids[name]
                example_clauses.append([fid if value else -fid])

        bg_clauses = task.get_kb_clauses()

        if task.background:
            if isinstance(task.background[0], int):
                for lit in task.background:
                    bg_clauses.append([lit])
            else:
                bg_clauses.extend(task.background)

        bg_clauses.extend(example_clauses)

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
        """QuickXPlain adapted for constraint IDs."""
        if constraint_ids and not self._is_consistent(background):
            return []

        if not remaining:
            return []

        if len(remaining) == 1:
            return remaining

        k = len(remaining) // 2
        c1 = remaining[:k]
        c2 = remaining[k:]

        c2_clauses = self._get_clauses_for_constraints(c2, constraint_map)
        cs1 = self._quickxplain_constraints(
            constraint_ids=c2,
            remaining=c1,
            background=background + c2_clauses,
            constraint_map=constraint_map
        )

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
        """Check if clause set is consistent (satisfiable)."""
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
        """Apply REDUCE to remove redundant constraints from learned KB.

        Builds assumption-based data for NonIncrementalPySATChecker,
        runs Reduce with Dict[int, int] neg_map, then maps back to names.
        """
        if not task.learned_kb:
            return []

        neg_map = {}
        id_to_name = {}
        set_kb = []
        assumptions = []
        set_b_prime = []
        assumption_counter = 1

        for c_id in task.learned_kb:
            if c_id not in task.constraint_map:
                continue
            if c_id not in task.negated_constraint_map:
                continue

            clauses = task.constraint_map[c_id]
            neg_clauses = task.negated_constraint_map[c_id]

            # Embed original constraint with assumption
            orig_id = assumption_counter
            assumption_counter += 1
            for clause in clauses:
                set_kb.append(clause + [-orig_id])
            assumptions.append(orig_id)
            set_b_prime.append(orig_id)
            id_to_name[orig_id] = c_id

            # Embed negated constraint with assumption
            neg_id = assumption_counter
            assumption_counter += 1
            for neg_clause in neg_clauses:
                set_kb.append(neg_clause + [-neg_id])
            assumptions.append(neg_id)

            neg_map[orig_id] = neg_id

        # BG as assumptions
        set_bg = []
        if task.background:
            for lit in task.background:
                bg_id = assumption_counter
                assumption_counter += 1
                set_kb.append([lit, -bg_id])
                assumptions.append(bg_id)
                set_bg.append(bg_id)

        checker = NonIncrementalPySATChecker(
            set_kb, assumptions, self.solver_name, self.profiler)

        try:
            reduce = Reduce(checker, self.profiler)
            redundant, non_redundant = reduce.reduce(
                set_b_prime=set_b_prime,
                set_neg_tv=[],
                set_bg=set_bg,
                neg_map=neg_map
            )

            # Map back to constraint names
            return [id_to_name[a] for a in non_redundant if a in id_to_name]

        except Exception as e:
            logging.warning('REDUCE failed: %s, returning learned KB as-is', e)
            return task.learned_kb
