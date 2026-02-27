"""
QuAcq algorithm for interactive constraint acquisition (IJCAI 2013).

Supports two modes:
- Oracle-based: traditional QuAcq with oracle membership queries + FindScope/FindC
- Example-based: ExampleProvider + oracle.is_valid() + FindScope/FindC

All membership queries go through oracle.is_valid(). Discriminating examples
use DiscriminatingGenerator (C_L[Y] + BG), not FM clauses.

Accepts QuAcqTask (assumption-ID based) as primary task type.
Also contains QuAcqResult (co-located: algorithm produces its own result type).
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Literal

from .task_preparation import QuAcqTask
from conacq.oracle import Oracle
from conacq.example_generators import QueryGenerator, ExampleProvider
from .findscope import find_scope
from .findc import find_c
from .discriminating_generator import DiscriminatingGenerator
from conacq.algorithms.acqmss.reduce import Reduce
from explanation.models.task_preparation import DescriptionProvider
from explanation.operations.algorithms.checker import NonIncrementalPySATChecker
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)
from ._task_compat import get_clause_map


@dataclass
class QuAcqResult:
    """
    Result of QuAcq constraint acquisition.

    Captures all information about the learning outcome:
    - Acquired constraints as both assumption IDs and resolved names
    - Query statistics
    - Performance metrics
    - Convergence information
    - Evaluation metrics (optional)

    Attributes:
        kb_assumption_ids: Learned KB as integer assumption IDs (primary)
        kb_constraints:    Learned KB as resolved constraint names (backward compat)
        n_queries:         Total membership queries asked
        n_kb:              Number of constraints in final KB
        convergence_reason: Why learning stopped
        runtime_ms:        Total learning runtime in milliseconds
        consistency_checks: Number of SAT consistency checks performed
        metadata:          Additional metadata for analysis
        query_history:     List of (config, answer, source) triples
        evaluation:        Optional evaluation results
    """
    # Primary: learned KB as assumption IDs
    kb_assumption_ids: List[int] = field(default_factory=list)

    # Resolved constraint names (for backward compat with eval pipeline)
    kb_constraints: List[str] = field(default_factory=list)

    # Query statistics
    n_queries: int = 0
    n_kb: int = 0
    convergence_reason: str = ""
    runtime_ms: float = 0.0
    consistency_checks: int = 0
    metadata: Dict = field(default_factory=dict)

    # Query history: (config, answer, source) triples
    query_history: List[Tuple[Dict[str, bool], bool, str]] = field(default_factory=list)

    # Evaluation results (populated after evaluate() is called)
    evaluation: Optional[Dict] = None

    def __post_init__(self):
        """Auto-calculate n_kb if not set."""
        if self.n_kb == 0:
            self.n_kb = len(self.kb_assumption_ids) or len(self.kb_constraints)

    def to_dict(self) -> Dict:
        """Convert result to dictionary for JSON serialization."""
        result = {
            'kb_constraints': self.kb_constraints,
            'kb_assumption_ids': self.kb_assumption_ids,
            'n_queries': self.n_queries,
            'n_kb': self.n_kb,
            'convergence_reason': self.convergence_reason,
            'runtime_ms': self.runtime_ms,
            'consistency_checks': self.consistency_checks,
            'metadata': self.metadata,
            'query_history': [
                {'config': config, 'answer': answer, 'source': source}
                for config, answer, source in self.query_history
            ]
        }
        if self.evaluation is not None:
            result['evaluation'] = self.evaluation
        return result

    def save(self, filepath: str) -> None:
        """Save result to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'QuAcqResult':
        """Load result from JSON file. Handles both old and new formats."""
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Handle query_history: support 2-tuple (old) and 3-tuple (new) formats
        query_history = []
        for qh in data.get('query_history', []):
            config = qh['config']
            answer = qh['answer']
            source = qh.get('source', 'main')
            query_history.append((config, answer, source))

        return cls(
            kb_assumption_ids=data.get('kb_assumption_ids', []),
            kb_constraints=data.get('kb_constraints', []),
            n_queries=data.get('n_queries', 0),
            n_kb=data.get('n_kb', 0),
            convergence_reason=data.get('convergence_reason', ''),
            runtime_ms=data.get('runtime_ms', 0.0),
            consistency_checks=data.get('consistency_checks', 0),
            metadata=data.get('metadata', {}),
            query_history=query_history,
            evaluation=data.get('evaluation')
        )

    def __repr__(self):
        return (f"QuAcqResult(n_kb={self.n_kb}, n_queries={self.n_queries}, "
                f"convergence='{self.convergence_reason}')")


class QuAcq:
    """
    QuAcq algorithm for interactive constraint acquisition.

    Supports oracle-based mode (learn) and example-based mode (learn_from_examples).
    Uses QuAcqTask with integer assumption IDs.
    """

    def __init__(self, solver_name: str = 'glucose4',
                 profiler_instance: AbstractProfiler = None) -> None:
        self.solver_name = solver_name
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()
        self.query_generator = QueryGenerator(solver_name, self.profiler)
        self.result: Optional[QuAcqResult] = None

    @measure_time('quacq_runtime')
    @count_calls('quacq_calls')
    def learn(self, task: QuAcqTask, oracle: Oracle,
              description_provider: DescriptionProvider = None,
              max_queries: int = 1000) -> QuAcqResult:
        """
        Run QuAcq with oracle-based membership queries (original mode).

        Args:
            task: QuAcqTask (immutable)
            oracle: Oracle for membership queries
            description_provider: Maps assumption IDs to constraint names
            max_queries: Maximum queries before stopping

        Returns:
            QuAcqResult with learned KB (both assumption IDs and names)
        """
        start_time = time.perf_counter()
        convergence_reason = ''

        # Local mutable state (not on task)
        remaining_bias = set(task.set_c)
        learned_kb: List[int] = []
        n_queries = 0
        query_history: List[Tuple[Dict[str, bool], bool, str]] = []

        def record_query(config: Dict[str, bool], answer: bool, source: str = 'main'):
            nonlocal n_queries
            if n_queries < max_queries:
                n_queries += 1
                query_history.append((config.copy(), answer, source))

        all_variables = set(task.feature_ids.keys())
        generator = DiscriminatingGenerator(task, self.solver_name)

        logging.info('QuAcq starting: Bias=%d constraints', len(remaining_bias))

        while remaining_bias:
            if n_queries >= max_queries:
                convergence_reason = 'max_queries'
                logging.info('Reached max queries limit: %d', max_queries)
                break

            query, tested_c_id = self.query_generator.generate(
                task, remaining_bias, learned_kb)

            if query is None:
                convergence_reason = 'no_query'
                logging.info('No more queries possible - converged')
                break

            answer = oracle.ask(query)
            record_query(query, answer)

            logging.debug('Query %d: answer=%s, testing constraint %s',
                          n_queries, answer, tested_c_id)

            if answer:
                pruned = self._prune_rejecting_constraints(
                    task, remaining_bias, query)
                logging.debug('Pruned %d constraints', len(pruned))
            else:
                # Check limit BEFORE find_scope/find_c (which may ask additional queries)
                if n_queries >= max_queries:
                    convergence_reason = 'max_queries'
                    logging.info('Reached max queries limit: %d', max_queries)
                    break

                scope_vars = find_scope(
                    e=query, R=set(), Y=all_variables,
                    ask_query=False, oracle=oracle, task=task,
                    remaining_bias=remaining_bias,
                    record_query=record_query, profiler=self.profiler
                )

                scope = set(scope_vars)
                if scope:
                    c_id = find_c(
                        e=query, scope=scope, task=task,
                        remaining_bias=remaining_bias,
                        record_query=record_query, oracle=oracle,
                        learned_kb=learned_kb, generator=generator,
                        profiler=self.profiler
                    )

                    if c_id is not None:
                        if c_id not in learned_kb:
                            learned_kb.append(c_id)
                        remaining_bias.discard(c_id)
                        logging.debug('FindScope/FindC added constraint: %s', c_id)
                    else:
                        logging.warning('FindC returned no constraint for scope %s', scope)
                else:
                    logging.warning('FindScope returned empty scope for negative example')
                    if tested_c_id:
                        if tested_c_id not in learned_kb:
                            learned_kb.append(tested_c_id)
                        remaining_bias.discard(tested_c_id)

        if not remaining_bias:
            convergence_reason = 'empty_bias'
            logging.info('Bias exhausted - converged')

        return self._build_result(
            task, learned_kb, n_queries, query_history,
            remaining_bias, start_time, convergence_reason, description_provider)

    @measure_time('quacq_example_runtime')
    @count_calls('quacq_example_calls')
    def learn_from_examples(
            self,
            task: QuAcqTask,
            example_provider: ExampleProvider,
            oracle,
            description_provider: DescriptionProvider,
            query_mode: Literal['example_only', 'example_first'] = 'example_only',
            max_queries: int = 10000
    ) -> QuAcqResult:
        """
        Run QuAcq with ExampleProvider + FindScope/FindC.

        Args:
            task: QuAcqTask (immutable)
            example_provider: Shuffled mixed example pool
            oracle: Oracle with is_valid(Dict[str, bool]) -> bool
            description_provider: Maps assumption IDs to constraint names
            query_mode: 'example_only' or 'example_first'
            max_queries: Maximum queries before stopping

        Returns:
            QuAcqResult with learned KB
        """
        start_time = time.perf_counter()
        convergence_reason = ''
        queries_from_pool = 0
        queries_from_sat = 0

        # Local mutable state (not on task)
        remaining_bias = set(task.set_c)
        learned_kb: List[int] = []
        n_queries = 0
        query_history: List[Tuple[Dict[str, bool], bool, str]] = []

        def record_query(config: Dict[str, bool], answer: bool, source: str = 'main'):
            nonlocal n_queries
            if n_queries < max_queries:
                n_queries += 1
                query_history.append((config.copy(), answer, source))

        logging.info('QuAcq (FindScope/FindC) starting: Bias=%d, pool=%d, mode=%s',
                     len(remaining_bias), example_provider.remaining(), query_mode)

        all_variables = set(task.feature_ids.keys())
        generator = DiscriminatingGenerator(task, self.solver_name)

        while remaining_bias:
            if n_queries >= max_queries:
                convergence_reason = 'max_queries'
                break

            # Step 1: Get next example
            query = example_provider.next_example()

            if query is not None:
                queries_from_pool += 1
            elif query_mode == 'example_first':
                query, _ = self.query_generator.generate(
                    task, remaining_bias, learned_kb)
                if query is not None:
                    queries_from_sat += 1

            if query is None:
                convergence_reason = 'pool_exhausted' if query_mode == 'example_only' else 'no_query'
                logging.info('No more queries: %s', convergence_reason)
                break

            # Step 2: Check validity via oracle
            is_valid = oracle.is_valid(query)

            record_query(query, is_valid)

            logging.debug('Query %d: valid=%s (pool=%d, sat=%d)',
                          n_queries, is_valid, queries_from_pool, queries_from_sat)

            # Step 3-4: Process answer
            if is_valid:
                # Positive: prune constraints that reject this valid config
                pruned = self._prune_rejecting_constraints(
                    task, remaining_bias, query)
                logging.debug('Pruned %d constraints', len(pruned))
            else:
                # Negative: use FindScope + FindC to identify constraint
                scope_vars = find_scope(
                    e=query, R=set(), Y=all_variables,
                    ask_query=False, oracle=oracle, task=task,
                    remaining_bias=remaining_bias,
                    record_query=record_query, profiler=self.profiler
                )

                scope = set(scope_vars)
                if scope:
                    c_id = find_c(
                        e=query, scope=scope, task=task,
                        remaining_bias=remaining_bias,
                        record_query=record_query, oracle=oracle,
                        learned_kb=learned_kb, generator=generator,
                        example_provider=example_provider,
                        query_mode=query_mode,
                        profiler=self.profiler
                    )

                    if c_id is not None:
                        if c_id not in learned_kb:
                            learned_kb.append(c_id)
                        remaining_bias.discard(c_id)
                        logging.debug('FindScope/FindC added constraint: %s', c_id)
                    else:
                        logging.warning('FindC returned no constraint for scope %s', scope)
                else:
                    logging.warning('FindScope returned empty scope for negative example')

        if not remaining_bias:
            convergence_reason = 'empty_bias'

        result = self._build_result(
            task, learned_kb, n_queries, query_history,
            remaining_bias, start_time, convergence_reason, description_provider)
        result.metadata['queries_from_pool'] = queries_from_pool
        result.metadata['queries_from_sat'] = queries_from_sat
        result.metadata['query_mode'] = query_mode
        return result

    def _build_result(self, task: QuAcqTask, learned_kb: List[int],
                      n_queries: int, query_history: list,
                      remaining_bias: set,
                      start_time: float, convergence_reason: str,
                      description_provider: DescriptionProvider) -> QuAcqResult:
        """Build QuAcqResult from algorithm state, applying REDUCE."""
        final_kb_ids = self._apply_reduce(task, learned_kb)
        runtime_ms = (time.perf_counter() - start_time) * 1000

        # Resolve assumption IDs to constraint names (if provider available)
        if description_provider is not None:
            kb_names = [description_provider.get_description(aid) for aid in final_kb_ids]
        else:
            kb_names = [str(aid) for aid in final_kb_ids]

        consistency_checks = self.profiler.get_metric('sat_checks_query_gen', 0)
        if isinstance(consistency_checks, list):
            consistency_checks = len(consistency_checks)

        self.result = QuAcqResult(
            kb_assumption_ids=final_kb_ids,
            kb_constraints=kb_names,
            n_queries=n_queries,
            n_kb=len(final_kb_ids),
            convergence_reason=convergence_reason,
            runtime_ms=runtime_ms,
            consistency_checks=consistency_checks,
            metadata={
                'initial_bias_size': len(get_clause_map(task)),
                'remaining_bias_size': len(remaining_bias),
                'learned_before_reduce': len(learned_kb)
            },
            query_history=query_history
        )

        logging.info('QuAcq finished: KB=%d, queries=%d, reason=%s',
                     len(final_kb_ids), n_queries, convergence_reason)

        return self.result

    def _apply_reduce(self, task, learned_kb: List[int]) -> List[int]:
        """Apply REDUCE directly using assumption IDs."""
        if not learned_kb:
            return []

        checker = NonIncrementalPySATChecker(
            task.set_kb, task.assumptions, self.solver_name, self.profiler)

        try:
            reduce = Reduce(checker, self.profiler)
            redundant, non_redundant = reduce.reduce(
                set_b_prime=learned_kb,
                set_neg_tv=[],
                set_bg=task.set_b,
                negation_map=task.negation_map
            )
            return non_redundant
        except Exception as e:
            logging.warning('REDUCE failed: %s, returning learned KB as-is', e)
            return list(learned_kb)

    @count_calls('prune_calls')
    def _prune_rejecting_constraints(self, task: QuAcqTask,
                                     remaining_bias: set,
                                     positive_example: Dict[str, bool]) -> List[int]:
        """Remove constraints from remaining_bias that reject the positive example."""
        assumptions = task.config_to_assumptions(positive_example)
        assignment = {abs(lit): lit > 0 for lit in assumptions}

        pruned = []
        clause_map = get_clause_map(task)
        for aid in list(remaining_bias):
            clauses = clause_map.get(aid, [])
            if task.violates_clauses(clauses, assignment):
                pruned.append(aid)

        remaining_bias -= set(pruned)
        return pruned

