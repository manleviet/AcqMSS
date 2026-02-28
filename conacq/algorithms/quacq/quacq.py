"""
QuAcq algorithm for interactive constraint acquisition (IJCAI 2013).

Supports three modes via single learn() method:
- 'oracle': traditional QuAcq with SAT-based query generation + oracle.ask()
- 'example_only': ExampleProvider supplies queries, oracle.is_valid() classifies
- 'example_first': pool first, SAT fallback when exhausted

All collaborators injected at construction (DI pattern).
Also contains QuAcqResult (co-located: algorithm produces its own result type).
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Literal

from conacq.oracle import Oracle
from conacq.example_generators import QueryGenerator, ExampleProvider
from .findscope import find_scope
from .findc import find_c
from .discriminating_generator import DiscriminatingGenerator
from .sat_utils import (
    config_to_assumptions, violates_clauses, get_kb_clauses
)
from conacq.algorithms.acqmss.reduce import Reduce
from explanation.models.task_preparation import DescriptionProvider
from explanation.operations.algorithms.checker import NonIncrementalPySATChecker
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


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

    Collaborators injected at construction (DI pattern).
    Single learn() method with mode dispatch.

    Args:
        oracle: Oracle for membership queries
        query_generator: SAT-based query generator (required for oracle/example_first modes)
        example_provider: Example pool provider (required for example modes)
        discriminating_generator: For FindC discriminating examples (required for oracle mode)
        profiler_instance: Optional profiler
    """

    def __init__(self, oracle: Oracle,
                 query_generator: QueryGenerator = None,
                 example_provider: ExampleProvider = None,
                 discriminating_generator: DiscriminatingGenerator = None,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.oracle = oracle
        self.query_generator = query_generator
        self.example_provider = example_provider
        self.discriminating_generator = discriminating_generator
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()
        self.result: Optional[QuAcqResult] = None

    @classmethod
    def for_oracle(cls, oracle: Oracle,
                   query_gen: QueryGenerator,
                   discrim_gen: DiscriminatingGenerator,
                   profiler: AbstractProfiler = None) -> 'QuAcq':
        """Factory for oracle-based learning. discrim_gen is required."""
        return cls(oracle, query_generator=query_gen,
                   discriminating_generator=discrim_gen,
                   profiler_instance=profiler)

    @classmethod
    def for_examples(cls, oracle: Oracle,
                     example_provider: ExampleProvider,
                     discrim_gen: DiscriminatingGenerator = None,
                     profiler: AbstractProfiler = None) -> 'QuAcq':
        """Factory for example-based learning."""
        return cls(oracle, example_provider=example_provider,
                   discriminating_generator=discrim_gen,
                   profiler_instance=profiler)

    @measure_time('quacq_runtime')
    @count_calls('quacq_calls')
    def learn(self,
              set_c: List[int],
              set_b: List[int],
              set_kb: List[List],
              negation_map: Dict[int, int],
              assumptions: List[int],
              background_clauses: List[List[int]],
              feature_ids: Dict[str, int],
              id_to_feature: Dict[int, str],
              constraint_clauses: Dict[int, List[List[int]]],
              negated_clauses: Dict[int, List[List[int]]],
              mode: Literal['oracle', 'example_only', 'example_first'] = 'oracle',
              max_queries: int = 1000,
              description_provider: DescriptionProvider = None,
              ) -> QuAcqResult:
        """
        Run QuAcq learning with specified mode.

        Args:
            set_c: Bias constraint assumption IDs
            set_b: BG assumption IDs
            set_kb: Full KB with assumption guards
            negation_map: {assumption_id -> negated_assumption_id}
            assumptions: All assumption IDs
            background_clauses: Raw BG CNF clauses
            feature_ids: Feature name -> SAT variable ID
            id_to_feature: SAT variable ID -> feature name
            constraint_clauses: assumption_id -> raw CNF clauses
            negated_clauses: assumption_id -> negated CNF clauses
            mode: 'oracle', 'example_only', or 'example_first'
            max_queries: Maximum queries before stopping
            description_provider: Maps assumption IDs to constraint names

        Returns:
            QuAcqResult with learned KB
        """
        # Mode validation
        self._validate_mode(mode)

        start_time = time.perf_counter()
        convergence_reason = ''
        queries_from_pool = 0
        queries_from_sat = 0

        # Local mutable state
        remaining_bias = set(set_c)
        learned_kb: List[int] = []
        n_queries = 0
        query_history: List[Tuple[Dict[str, bool], bool, str]] = []

        def record_query(config: Dict[str, bool], answer: bool, source: str = 'main'):
            nonlocal n_queries
            if n_queries < max_queries:
                n_queries += 1
                query_history.append((config.copy(), answer, source))

        all_variables = set(feature_ids.keys())

        logging.info('QuAcq starting: Bias=%d constraints, mode=%s', len(remaining_bias), mode)

        while remaining_bias:
            if n_queries >= max_queries:
                convergence_reason = 'max_queries'
                logging.info('Reached max queries limit: %d', max_queries)
                break

            # Step 1: Get next query (mode-dependent)
            query = None
            tested_c_id = None

            if mode == 'oracle':
                kb_cls = get_kb_clauses(learned_kb, constraint_clauses)
                query, tested_c_id = self.query_generator.generate(
                    remaining_bias=remaining_bias, learned_kb=learned_kb,
                    kb_clauses=kb_cls, negated_clauses=negated_clauses,
                    bg_clauses=background_clauses, feature_ids=feature_ids,
                    id_to_feature=id_to_feature, n_bg=len(set_b))
                if query is not None:
                    queries_from_sat += 1
            else:
                # example_only or example_first: try pool first
                query = self.example_provider.next_example()
                if query is not None:
                    queries_from_pool += 1
                elif mode == 'example_first':
                    # Pool exhausted, fall back to SAT
                    kb_cls = get_kb_clauses(learned_kb, constraint_clauses)
                    query, tested_c_id = self.query_generator.generate(
                        remaining_bias=remaining_bias, learned_kb=learned_kb,
                        kb_clauses=kb_cls, negated_clauses=negated_clauses,
                        bg_clauses=background_clauses, feature_ids=feature_ids,
                        id_to_feature=id_to_feature, n_bg=len(set_b))
                    if query is not None:
                        queries_from_sat += 1

            if query is None:
                if mode == 'oracle':
                    convergence_reason = 'no_query'
                elif mode == 'example_only':
                    convergence_reason = 'pool_exhausted'
                else:
                    convergence_reason = 'no_query'
                logging.info('No more queries: %s', convergence_reason)
                break

            # Step 2: Check with oracle
            if mode == 'oracle':
                answer = self.oracle.ask(query)
            else:
                answer = self.oracle.is_valid(query)

            record_query(query, answer)

            logging.debug('Query %d: answer=%s, mode=%s', n_queries, answer, mode)

            # Step 3: Process answer
            if answer:
                pruned = self._prune_rejecting_constraints(
                    constraint_clauses, feature_ids, remaining_bias, query)
                logging.debug('Pruned %d constraints', len(pruned))
            else:
                if n_queries >= max_queries:
                    convergence_reason = 'max_queries'
                    break

                scope_vars = find_scope(
                    e=query, R=set(), Y=all_variables,
                    ask_query=False, oracle=self.oracle,
                    constraint_clauses=constraint_clauses,
                    feature_ids=feature_ids,
                    id_to_feature=id_to_feature,
                    remaining_bias=remaining_bias,
                    record_query=record_query, profiler=self.profiler
                )

                scope = set(scope_vars)
                if scope:
                    c_id = find_c(
                        e=query, scope=scope,
                        constraint_clauses=constraint_clauses,
                        feature_ids=feature_ids,
                        id_to_feature=id_to_feature,
                        remaining_bias=remaining_bias,
                        record_query=record_query, oracle=self.oracle,
                        learned_kb=learned_kb,
                        generator=self.discriminating_generator,
                        example_provider=self.example_provider if mode != 'oracle' else None,
                        query_mode=mode if mode != 'oracle' else 'example_only',
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
                    if mode == 'oracle' and tested_c_id:
                        if tested_c_id not in learned_kb:
                            learned_kb.append(tested_c_id)
                        remaining_bias.discard(tested_c_id)

        if not remaining_bias:
            convergence_reason = 'empty_bias'
            logging.info('Bias exhausted - converged')

        result = self._build_result(
            constraint_clauses, set_kb, assumptions, set_b, negation_map,
            learned_kb, n_queries, query_history,
            remaining_bias, start_time, convergence_reason, description_provider)
        if mode != 'oracle':
            result.metadata['queries_from_pool'] = queries_from_pool
            result.metadata['queries_from_sat'] = queries_from_sat
            result.metadata['query_mode'] = mode
        return result

    def _validate_mode(self, mode: str) -> None:
        """Validate mode and required dependencies."""
        valid_modes = ('oracle', 'example_only', 'example_first')
        if mode not in valid_modes:
            raise ValueError(f"Unknown mode '{mode}'. Use one of: {valid_modes}")
        if mode == 'oracle':
            if self.query_generator is None:
                raise ValueError("Oracle mode requires query_generator (use for_oracle())")
            if self.discriminating_generator is None:
                raise ValueError("Oracle mode requires discriminating_generator (use for_oracle())")
        if mode in ('example_only', 'example_first') and self.example_provider is None:
            raise ValueError(f"Mode '{mode}' requires example_provider (use for_examples())")
        if mode == 'example_first':
            if self.query_generator is None:
                raise ValueError("example_first mode requires query_generator")
            if self.discriminating_generator is None:
                raise ValueError("example_first mode requires discriminating_generator")

    def _build_result(self,
                      constraint_clauses: Dict[int, List[List[int]]],
                      set_kb: List[List], assumptions: List[int],
                      set_b: List[int], negation_map: Dict[int, int],
                      learned_kb: List[int],
                      n_queries: int, query_history: list,
                      remaining_bias: set,
                      start_time: float, convergence_reason: str,
                      description_provider: DescriptionProvider) -> QuAcqResult:
        """Build QuAcqResult from algorithm state, applying REDUCE."""
        final_kb_ids = self._apply_reduce(
            set_kb, assumptions, set_b, negation_map, learned_kb)
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
                'initial_bias_size': len(constraint_clauses),
                'remaining_bias_size': len(remaining_bias),
                'learned_before_reduce': len(learned_kb)
            },
            query_history=query_history
        )

        logging.info('QuAcq finished: KB=%d, queries=%d, reason=%s',
                     len(final_kb_ids), n_queries, convergence_reason)

        return self.result

    def _apply_reduce(self, set_kb, assumptions, set_b, negation_map,
                      learned_kb: List[int]) -> List[int]:
        """Apply REDUCE directly using assumption IDs."""
        if not learned_kb:
            return []

        checker = NonIncrementalPySATChecker(
            set_kb, assumptions, 'glucose4', self.profiler)

        try:
            reduce = Reduce(checker, self.profiler)
            redundant, non_redundant = reduce.reduce(
                set_b_prime=learned_kb,
                set_neg_tv=[],
                set_bg=set_b,
                negation_map=negation_map
            )
            return non_redundant
        except Exception as e:
            logging.warning('REDUCE failed: %s, returning learned KB as-is', e)
            return list(learned_kb)

    @count_calls('prune_calls')
    def _prune_rejecting_constraints(self,
                                     constraint_clauses: Dict[int, List[List[int]]],
                                     feature_ids: Dict[str, int],
                                     remaining_bias: set,
                                     positive_example: Dict[str, bool]) -> List[int]:
        """Remove constraints from remaining_bias that reject the positive example."""
        assumptions_list = config_to_assumptions(positive_example, feature_ids)
        assignment = {abs(lit): lit > 0 for lit in assumptions_list}

        pruned = []
        for aid in list(remaining_bias):
            clauses = constraint_clauses.get(aid, [])
            if violates_clauses(clauses, assignment):
                pruned.append(aid)

        remaining_bias -= set(pruned)
        return pruned
