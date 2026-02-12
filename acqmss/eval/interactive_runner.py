"""
Run interactive (QuAcq) learning and collect performance metrics.

Analogous to CONGENRunner but uses InteractiveLearner.from_examples()
for example-based interactive constraint acquisition.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import random
import time
import tracemalloc
import logging

from explanation.operations.algorithms.profiler import Profiler

from .performance_metrics import PerformanceMetrics


@dataclass
class InteractiveRunResult:
    """
    Result of running interactive learning with metrics.

    Attributes:
        kb_constraints: List of constraint IDs in learned KB
        kb_clauses: CNF clauses of the learned KB
        n_bias: Original number of bias constraints
        n_kb: Final KB size
        n_queries: Number of membership queries asked
        convergence_reason: Why learning stopped
        runtime_ms: Execution time in milliseconds
        consistency_checks: Number of SAT solver calls
        memory_peak_mb: Peak memory usage in MB
    """
    kb_constraints: List[str]
    kb_clauses: List[List[int]]
    n_bias: int
    n_kb: int
    n_queries: int
    convergence_reason: str
    runtime_ms: float
    consistency_checks: int
    memory_peak_mb: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'kb_constraints': self.kb_constraints,
            'n_bias': self.n_bias,
            'n_kb': self.n_kb,
            'n_queries': self.n_queries,
            'convergence_reason': self.convergence_reason,
            'performance': {
                'runtime_ms': self.runtime_ms,
                'consistency_checks': self.consistency_checks,
                'memory_peak_mb': self.memory_peak_mb,
            }
        }

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics as PerformanceMetrics object."""
        return PerformanceMetrics(
            runtime_ms=self.runtime_ms,
            consistency_checks=self.consistency_checks,
            memory_peak_mb=self.memory_peak_mb,
            n_mss=0,  # QuAcq has no MSS step
            n_kb=self.n_kb
        )


class InteractiveRunner:
    """
    Run interactive (QuAcq) learning and collect performance metrics.

    Analogous to CONGENRunner. Uses InteractiveLearner.from_examples()
    to learn from a pool of examples with per-fold bias shuffling support.
    """

    def __init__(
            self,
            bias_clauses: Dict[str, List[List[int]]],
            feature_ids: Dict[str, int],
            fm_path: str,
            bias_path: str,
            solver_name: str = 'glucose4',
            max_queries: int = 1000,
            query_mode: str = 'example_only'
    ):
        """
        Initialize runner.

        Args:
            bias_clauses: {constraint_id: clauses} from bias file
            feature_ids: {feature_name: SAT_variable_id}
            fm_path: Path to feature model (.uvl)
            bias_path: Path to bias file (.json)
            solver_name: SAT solver name
            max_queries: Maximum membership queries per run
            query_mode: 'example_only' or 'example_first'
        """
        self.bias_clauses = bias_clauses
        self.feature_ids = feature_ids
        self.fm_path = fm_path
        self.bias_path = bias_path
        self.solver_name = solver_name
        self.max_queries = max_queries
        self.query_mode = query_mode

    def run(
            self,
            positive_examples: List[Dict[str, bool]],
            negative_examples: List[Dict[str, bool]],
            shuffle_seed: Optional[int] = None
    ) -> InteractiveRunResult:
        """
        Run interactive learning with given examples and collect metrics.

        Args:
            positive_examples: List of E+ ({feature: True/False})
            negative_examples: List of E- ({feature: True/False})
            shuffle_seed: If provided, shuffle bias keys with this seed

        Returns:
            InteractiveRunResult with KB and performance metrics
        """
        logging.debug('>>> InteractiveRunner.run(E+=%d, E-=%d)',
                      len(positive_examples), len(negative_examples))

        # Start memory tracking
        tracemalloc.start()
        start_time = time.perf_counter()

        try:
            # Combine examples as mixed pool for ExampleProvider
            mixed_examples = list(positive_examples) + list(negative_examples)

            # Lazy import to avoid circular dependency
            # (learner.py imports from acqmss.eval)
            from acqmss.algorithms.interactive import InteractiveLearner

            # Create learner; disable profiling to avoid global profiler conflict
            # (caller manages the global profiler lifecycle)
            learner = InteractiveLearner.from_examples(
                fm_path=self.fm_path,
                bias_path=self.bias_path,
                examples=mixed_examples,
                seed=shuffle_seed,
                solver_name=self.solver_name,
                enable_profiling=False
            )

            # Shuffle bias ordering if seed provided
            # Safe to mutate: learner is fold-local, created fresh per run()
            if shuffle_seed is not None:
                keys = list(learner.task.bias)
                random.Random(shuffle_seed).shuffle(keys)
                learner.task.bias = keys
                logging.debug('Shuffled bias with seed=%d', shuffle_seed)

            # Run example-based learning
            result = learner.learn_from_examples(
                query_mode=self.query_mode,
                max_queries=self.max_queries
            )

        finally:
            # Stop timing and memory tracking
            end_time = time.perf_counter()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        runtime_ms = (end_time - start_time) * 1000
        memory_peak_mb = peak / (1024 * 1024)

        # Get KB clauses from result constraint IDs
        kb_clauses = []
        for cid in result.kb_constraints:
            if cid in self.bias_clauses:
                kb_clauses.extend(self.bias_clauses[cid])

        run_result = InteractiveRunResult(
            kb_constraints=result.kb_constraints,
            kb_clauses=kb_clauses,
            n_bias=len(self.bias_clauses),
            n_kb=result.n_kb,
            n_queries=result.n_queries,
            convergence_reason=result.convergence_reason,
            runtime_ms=runtime_ms,
            consistency_checks=result.consistency_checks,
            memory_peak_mb=memory_peak_mb
        )

        logging.debug('<<< InteractiveRunner: KB=%d, queries=%d, runtime=%.2fms',
                      result.n_kb, result.n_queries, runtime_ms)

        return run_result
