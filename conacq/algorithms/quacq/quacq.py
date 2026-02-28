"""
QuAcq algorithm for interactive constraint acquisition (IJCAI 2013).

Supports three modes via single learn() method:
- 'oracle': QueryProvider.generate_from_sat() + oracle.ask()
- 'example_only': QueryProvider.generate_from_pool() (paper-filtered)
- 'example_first': QueryProvider.generate() (pool first, SAT fallback)

All collaborators injected at construction (DI pattern).
Also contains QuAcqResult (co-located: algorithm produces its own result type).
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Literal

from conacq.oracle import Oracle
from conacq.example_generators import QueryProvider
from .findscope import find_scope
from .findc import find_c
from .discriminating_generator import DiscriminatingGenerator
from .sat_utils import (
    config_to_assumptions, violates_clauses, get_kb_clauses
)
from conacq.algorithms.acqmss.reduce import Reduce
from explanation.operations.algorithms.checker import NonIncrementalPySATChecker, ConsistencyChecker
from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)


@dataclass
class QuAcqResult:
    """Result of QuAcq constraint acquisition."""
    kb_assumption_ids: List[int] = field(default_factory=list)
    n_queries: int = 0
    convergence_reason: str = ""
    query_history: List[Tuple[Dict[str, bool], bool, str]] = field(default_factory=list)

    def __repr__(self) -> str:
        return (f"QuAcqResult(n_kb={len(self.kb_assumption_ids)}, "
                f"n_queries={self.n_queries}, "
                f"convergence_reason='{self.convergence_reason}')")


class QuAcq:
    """
    QuAcq algorithm for interactive constraint acquisition.

    Collaborators injected at construction (DI pattern).
    Single learn() method with mode dispatch.

    Args:
        oracle: Oracle for membership queries
        query_provider: Unified query provider (pool + SAT strategies)
        discriminating_generator: For FindC discriminating examples (required for oracle mode)
        profiler_instance: Optional profiler
    """

    def __init__(self, checker: ConsistencyChecker,
                 oracle: Oracle,
                 model=None,
                 query_provider: QueryProvider = None,
                 discriminating_generator: DiscriminatingGenerator = None,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.checker = checker
        self.oracle = oracle
        self.model = model  # QuAcqModel (optional, enables SAT-based pruning)
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()
        self.result: Optional[QuAcqResult] = None

        self.query_provider = query_provider
        self.discriminating_generator = discriminating_generator

    @classmethod
    def for_oracle(cls, checker: ConsistencyChecker,
                   oracle: Oracle,
                   query_provider: QueryProvider,
                   discrim_gen: DiscriminatingGenerator,
                   model=None,
                   profiler: AbstractProfiler = None) -> 'QuAcq':
        """Factory for oracle-based learning. discrim_gen required."""
        return cls(checker, oracle, model=model,
                   query_provider=query_provider,
                   discriminating_generator=discrim_gen,
                   profiler_instance=profiler)

    @classmethod
    def for_examples(cls, checker: ConsistencyChecker,
                     oracle: Oracle,
                     query_provider: QueryProvider,
                     discrim_gen: DiscriminatingGenerator = None,
                     model=None,
                     profiler: AbstractProfiler = None) -> 'QuAcq':
        """Factory for example-based learning."""
        return cls(checker, oracle, model=model,
                   query_provider=query_provider,
                   discriminating_generator=discrim_gen,
                   profiler_instance=profiler)

    @measure_time('quacq_runtime')
    @count_calls('quacq_calls')
    def learn(self,
              set_c: List[int],
              set_b: List[int],
              negation_map: Dict[int, int],
              background_clauses: List[List[int]],
              feature_ids: Dict[str, int],
              id_to_feature: Dict[int, str],
              constraint_clauses: Dict[int, List[List[int]]],
              negated_clauses: Dict[int, List[List[int]]],
              root_assumption: int = None,
              mode: Literal['oracle', 'example_only', 'example_first'] = 'oracle',
              max_queries: int = 1000,
              ) -> QuAcqResult:
        """
        Run QuAcq learning with specified mode.

        Args:
            set_c: Bias constraint assumption IDs
            set_b: BG assumption IDs
            negation_map: {assumption_id -> negated_assumption_id}
            background_clauses: Raw BG CNF clauses
            feature_ids: Feature name -> SAT variable ID
            id_to_feature: SAT variable ID -> feature name
            constraint_clauses: assumption_id -> raw CNF clauses
            negated_clauses: assumption_id -> negated CNF clauses
            root_assumption: Root BG assumption ID (enables root constraint)
            mode: 'oracle', 'example_only', or 'example_first'
            max_queries: Maximum queries before stopping

        Returns:
            QuAcqResult with learned KB
        """
        # Mode validation
        self._validate_mode(mode)

        convergence_reason = ''

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
            kb_cls = get_kb_clauses(learned_kb, constraint_clauses)

            if mode == 'oracle':
                query, tested_c_id = self.query_provider.generate_from_sat(
                    remaining_bias=remaining_bias, learned_kb=learned_kb,
                    kb_clauses=kb_cls, negated_clauses=negated_clauses,
                    bg_clauses=background_clauses, feature_ids=feature_ids,
                    id_to_feature=id_to_feature, n_bg=len(set_b))
            elif mode == 'example_only':
                query, tested_c_id = self.query_provider.generate_from_pool(
                    remaining_bias=remaining_bias, kb_clauses=kb_cls,
                    bg_clauses=background_clauses,
                    constraint_clauses=constraint_clauses,
                    feature_ids=feature_ids)
            else:  # example_first
                query, tested_c_id = self.query_provider.generate(
                    remaining_bias=remaining_bias, learned_kb=learned_kb,
                    kb_clauses=kb_cls, negated_clauses=negated_clauses,
                    bg_clauses=background_clauses, feature_ids=feature_ids,
                    id_to_feature=id_to_feature,
                    constraint_clauses=constraint_clauses,
                    n_bg=len(set_b))

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
            answer = self.oracle.is_valid(query)

            record_query(query, answer)
            logging.debug('Query %d: answer=%s, mode=%s', n_queries, answer, mode)

            # Step 3: Process answer
            if answer:
                if self.model and root_assumption is not None:
                    pruned = self._prune_rejecting_constraints(
                        remaining_bias, query, root_assumption)
                else:
                    pruned = self._prune_rejecting_constraints_legacy(
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

        reduce = Reduce(self.checker, self.profiler)
        redundant, kb = reduce.reduce(
            set_b_prime=learned_kb,
            set_neg_tv=[],
            set_bg=set_b,
            negation_map=negation_map
        )

        self.result = QuAcqResult(
            kb_assumption_ids=kb,
            n_queries=n_queries,
            convergence_reason=convergence_reason,
            query_history=query_history
        )

        logging.info('QuAcq finished: KB=%d, queries=%d, reason=%s',
                     len(kb), n_queries, convergence_reason)
        return self.result

    def _validate_mode(self, mode: str) -> None:
        """Validate mode and required dependencies."""
        valid_modes = ('oracle', 'example_only', 'example_first')
        if mode not in valid_modes:
            raise ValueError(f"Unknown mode '{mode}'. Use one of: {valid_modes}")
        if self.query_provider is None:
            raise ValueError("query_provider is required (use for_oracle() or for_examples())")
        if mode == 'oracle' and self.discriminating_generator is None:
            raise ValueError("Oracle mode requires discriminating_generator (use for_oracle())")
        if mode == 'example_first' and self.discriminating_generator is None:
            raise ValueError("example_first mode requires discriminating_generator")

    @count_calls('prune_calls')
    def _prune_rejecting_constraints(self,
                                     remaining_bias: set,
                                     positive_example: Dict[str, bool],
                                     root_assumption: int) -> List[int]:
        """Remove constraints from remaining_bias that reject the positive example.

        Uses SAT-based consistency checking with Part 4 feature assignment
        assumptions, catching implied violations beyond pure Boolean evaluation.
        """
        config_assumptions = self.model.config_to_assumptions(positive_example)
        base = [root_assumption] + config_assumptions
        pruned = []
        for aid in list(remaining_bias):
            if not self.checker.is_consistent(base + [aid]):
                pruned.append(aid)
        remaining_bias -= set(pruned)
        return pruned

    @count_calls('prune_calls')
    def _prune_rejecting_constraints_legacy(self,
                                            constraint_clauses: Dict[int, List[List[int]]],
                                            feature_ids: Dict[str, int],
                                            remaining_bias: set,
                                            positive_example: Dict[str, bool]) -> List[int]:
        """Legacy: pure Boolean eval fallback (when Part 4 data unavailable)."""
        assumptions_list = config_to_assumptions(positive_example, feature_ids)
        assignment = {abs(lit): lit > 0 for lit in assumptions_list}

        pruned = []
        for aid in list(remaining_bias):
            clauses = constraint_clauses.get(aid, [])
            if violates_clauses(clauses, assignment):
                pruned.append(aid)

        remaining_bias -= set(pruned)
        return pruned
