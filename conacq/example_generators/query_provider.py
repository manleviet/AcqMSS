"""
Unified query provider for QuAcq constraint acquisition.

Merges pool-based (ExampleProvider) and SAT-based (QueryGenerator) strategies
into single class with paper-aligned pool filtering.

Paper condition for pool: query in sol(C_L + BG) AND violates >=1 c in B.
"""

import logging
import random
from typing import Optional, Dict, List, Mapping, Sequence, Tuple, TYPE_CHECKING

from explanation.api import config_to_assignment_assumptions
from profiling import (
    get_global_profiler, measure_time, count_calls, AbstractProfiler
)

if TYPE_CHECKING:
    from explanation.api import ConsistencyChecker
    from conacq.algorithms.quacq.quacq_model import QuAcqModel


class QueryProvider:
    """Unified query provider: pool-filtered + SAT-based strategies.

    Replaces ExampleProvider (pool) + QueryGenerator (SAT).
    Pool filtering follows paper: query in sol(C_L + BG) AND violates >=1 c in B.

    Args:
        pool: Optional list of example configs for pool-based generation
        seed: Random seed for pool shuffling
        checker: ConsistencyChecker for SAT checks
        model: QuAcqModel for model_to_config (KB catalog)
        assignment_map: feature-assignment → assumption map (from the prepared task)
        profiler_instance: Optional profiler for timing/counting
    """

    def __init__(self,
                 pool: Optional[List[Dict[str, bool]]] = None,
                 seed: Optional[int] = None,
                 checker: 'ConsistencyChecker' = None,
                 model: 'QuAcqModel' = None,
                 assignment_map=None,
                 profiler_instance: Optional[AbstractProfiler] = None) -> None:
        self.checker = checker
        self.model = model
        self.assignment_map = assignment_map
        self.profiler = profiler_instance if profiler_instance else get_global_profiler()

        # Pool state
        self._pool: List[Dict[str, bool]] = []
        self._pool_index: int = 0
        # Initializes pool state with optional seeded shuffling
        if pool is not None:
            self._pool = list(pool)
            # Per-call RNG instance keeps the shuffle off the process-global
            # ``random`` stream. seed=None still isolates: Random(None) seeds
            # from OS entropy without touching the shared generator.
            random.Random(seed).shuffle(self._pool)

    @property
    def pool_exhausted(self) -> bool:
        """Check if pool has been fully consumed."""
        return self._pool_index >= len(self._pool)

    @property
    def pool_remaining(self) -> int:
        """Number of pool examples remaining."""
        return max(0, len(self._pool) - self._pool_index)

    @count_calls('query_generation_calls')
    @measure_time('query_generation_runtime')
    def generate_from_pool(
            self,
            remaining_bias: set,
            learned_kb: List[int],
            set_b: Sequence[int],
    ) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
        """Generate query from pool with paper filtering.

        Paper condition: query in sol(C_L + BG) AND violates >=1 c in B.
        Both conditions checked via checker.is_consistent().

        Returns:
            Tuple of (query_config, violated_constraint_id) or (None, None)
        """
        while self._pool_index < len(self._pool):
            e = self._pool[self._pool_index]
            self._pool_index += 1

            # Condition 1: satisfies C_L + BG (via checker with Part 4 assumptions)
            config_assumptions = config_to_assignment_assumptions(e, self.assignment_map)
            set_c = learned_kb + list(set_b) + config_assumptions
            self.profiler.increment("query_generation_consistency_checks")
            if not self.checker.is_consistent(set_c):
                continue

            # Condition 2: violates >=1 constraint in remaining_bias (via checker)
            for c_id in remaining_bias:
                self.profiler.increment("query_generation_consistency_checks")
                if not self.checker.is_consistent([c_id] + config_assumptions):
                    logging.debug('Pool query found testing constraint %s', c_id)
                    return e, c_id

        logging.debug('Pool exhausted (%d examples checked)', self._pool_index)
        return None, None

    @measure_time('query_generation_runtime')
    @count_calls('query_generation_calls')
    def generate_from_sat(
            self,
            remaining_bias: set,
            learned_kb: List[int],
            set_b: Sequence[int],
            negation_map: Mapping[int, int],
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

            set_c = learned_kb + list(set_b) + [neg_aid]
            self.profiler.increment("query_generation_consistency_checks")
            if self.checker.is_consistent(set_c):
                model_lits = self.checker.get_model()
                if model_lits is None:
                    logging.warning('No model after SAT for constraint %s', c_id)
                    continue
                config = self.model.model_to_config(model_lits)
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
