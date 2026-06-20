"""
Unified query provider for QuAcq constraint acquisition.

Merges pool-based (ExampleProvider) and SAT-based (QueryGenerator) strategies
into single class with paper-aligned pool filtering.

Paper condition for pool: query in sol(C_L + BG) AND violates >=1 c in B.
"""

import logging
import random
from typing import Optional, Dict, List, Tuple, TYPE_CHECKING

from explanation.operations.algorithms.profiler import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)

if TYPE_CHECKING:
    from explanation.operations.algorithms.checker import ConsistencyChecker
    from explanation.models.codec import VariableCodec


class QueryProvider:
    """Unified query provider: pool-filtered + SAT-based strategies.

    Replaces ExampleProvider (pool) + QueryGenerator (SAT).
    Pool filtering follows paper: query in sol(C_L + BG) AND violates >=1 c in B.

    Pool iteration advances a persisted cursor (self._pool_start): each
    generate_from_pool call resumes where the previous one stopped, and
    pool_exhausted / pool_remaining report progress against it. The provider is
    used per-run (one instance per learning run), so this cursor is run-local —
    not shared across runs. (Full statelessness, needed only for L1 node
    threading, is deferred with L1.)

    Args:
        pool: Optional list of example configs for pool-based generation
        seed: Random seed for pool shuffling
        checker: ConsistencyChecker for SAT checks
        codec: VariableCodec for config_to_assumptions / model_to_config
        profiler_instance: Optional profiler for timing/counting
    """

    def __init__(self,
                 pool: Optional[List[Dict[str, bool]]] = None,
                 seed: Optional[int] = None,
                 checker: 'ConsistencyChecker' = None,
                 codec: 'VariableCodec' = None,
                 profiler_instance: Optional[AbstractProfiler] = None) -> None:
        self.checker = checker
        self.codec = codec
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()

        # Pool state: immutable list after construction; cursor tracked per-call
        self._pool: List[Dict[str, bool]] = []
        # _pool_start tracks how many examples were consumed across all calls
        # so that pool_exhausted / pool_remaining remain meaningful externally.
        self._pool_start: int = 0

        if pool is not None:
            self._pool = list(pool)
            if seed is not None:
                random.Random(seed).shuffle(self._pool)
            else:
                random.shuffle(self._pool)

    @property
    def pool_exhausted(self) -> bool:
        """Check if pool has been fully consumed."""
        return self._pool_start >= len(self._pool)

    @property
    def pool_remaining(self) -> int:
        """Number of pool examples remaining."""
        return max(0, len(self._pool) - self._pool_start)

    @count_calls('query_generation_calls')
    @measure_time('query_generation_runtime')
    def generate_from_pool(
            self,
            remaining_bias: set,
            learned_kb: List[int],
            set_b: List[int],
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Generate query from pool with paper filtering.

        Paper condition: query in sol(C_L + BG) AND violates >=1 c in B.
        Both conditions checked via checker.is_consistent().

        Iterates the pool from _pool_start using a local cursor; advances
        _pool_start past all consumed entries so pool_exhausted/pool_remaining
        stay accurate after the call returns.

        Returns:
            Tuple of (query_config, violated_constraint_id) or (None, None)
        """
        cursor = self._pool_start
        while cursor < len(self._pool):
            e = self._pool[cursor]
            cursor += 1

            # Condition 1: satisfies C_L + BG (via checker with Part 4 assumptions)
            config_assumptions = self.codec.config_to_assumptions(e)
            set_c = learned_kb + set_b + config_assumptions
            self.profiler.increment("query_generation_consistency_checks")
            if not self.checker.is_consistent(set_c):
                continue

            # Condition 2: violates >=1 constraint in remaining_bias (via checker)
            for c_id in remaining_bias:
                self.profiler.increment("query_generation_consistency_checks")
                if not self.checker.is_consistent([c_id] + config_assumptions):
                    logging.debug('Pool query found testing constraint %s', c_id)
                    self._pool_start = cursor
                    return e, c_id

        # Pool fully iterated without finding a valid query
        self._pool_start = cursor
        logging.debug('Pool exhausted (%d examples checked)', cursor)
        return None, None

    @measure_time('query_generation_runtime')
    @count_calls('query_generation_calls')
    def generate_from_sat(
            self,
            remaining_bias: set,
            learned_kb: List[int],
            set_b: List[int],
            negation_map: Dict[int, int],
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Generate query via SAT solving (matches paper Algorithm 1).

        Find config satisfying KB + BG but violating some c in Bias.
        """
        logging.debug('QueryProvider SAT: KB=%d, Bias=%d, BG=%d',
                      len(learned_kb), len(remaining_bias), len(set_b))

        for c_id in remaining_bias:
            neg_aid = negation_map.get(c_id)
            if neg_aid is None:
                logging.warning('No negation for constraint %s, skipping', c_id)
                continue

            set_c = learned_kb + set_b + [neg_aid]
            self.profiler.increment("query_generation_consistency_checks")
            sat, model_lits = self.checker.solve(set_c)
            if sat:
                if model_lits is None:
                    logging.warning('No model after SAT for constraint %s', c_id)
                    continue
                config = self.codec.model_to_config(model_lits)
                logging.debug('SAT query testing constraint %s', c_id)
                return config, c_id

        logging.debug('No SAT query possible - all bias implied by KB + BG')
        return None, None

    def generate(
            self,
            remaining_bias: set,
            learned_kb: List[int],
            set_b: List[int],
            negation_map: Dict[int, int],
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Pool first, then SAT fallback."""
        if not self.pool_exhausted:
            result = self.generate_from_pool(
                remaining_bias, learned_kb, set_b)
            if result[0] is not None:
                return result

        return self.generate_from_sat(
            remaining_bias, learned_kb, set_b,
            negation_map)
