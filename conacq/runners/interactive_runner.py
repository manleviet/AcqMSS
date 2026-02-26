"""
Run interactive (QuAcq) learning and collect performance metrics.

Supports two modes:
- Oracle mode ('automated'/'interactive'): via InteractiveLearner.from_files()
- Example mode ('example_only'/'example_first'): via InteractiveLearner.from_examples()

Analogous to ConGenRunner — file-path-based constructor, dual-mode run().
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import random
import time
import tracemalloc
import logging

from conacq.eval.performance_metrics import PerformanceMetrics


@dataclass
class InteractiveRunResult:
    """
    Result of running interactive learning with metrics.

    Attributes:
        kb_constraints: List of constraint IDs in learned KB
        kb_clauses: CNF clauses of the learned KB
        bg_clauses: Background knowledge clauses (root constraint)
        n_bias: Original number of bias constraints
        n_kb: Final KB size
        n_queries: Number of membership queries asked
        convergence_reason: Why learning stopped
        runtime_ms: Execution time in milliseconds
        consistency_checks: Number of SAT solver calls
        memory_peak_mb: Peak memory usage in MB
        profiler_data: Full profiler snapshot (counters, timers, gauges)
    """
    # KB result
    kb_constraints: List[str]
    kb_clauses: List[List[int]]
    bg_clauses: List[List[int]]
    n_bias: int
    n_kb: int
    n_queries: int
    convergence_reason: str

    # Core performance metrics
    runtime_ms: float
    consistency_checks: int
    memory_peak_mb: float

    # Extended profiler metrics
    profiler_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'kb_constraints': self.kb_constraints,
            'bg_clauses': self.bg_clauses,
            'n_bias': self.n_bias,
            'n_kb': self.n_kb,
            'n_queries': self.n_queries,
            'convergence_reason': self.convergence_reason,
            'performance': {
                'runtime_ms': self.runtime_ms,
                'consistency_checks': self.consistency_checks,
                'memory_peak_mb': self.memory_peak_mb,
                'profiler': self.profiler_data,
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

    File-path-based constructor, dual-mode run():
    - Oracle mode: run(mode='automated') or run(mode='interactive')
    - Example mode: run(pos, neg, mode='example_only') or run(pos, neg, mode='example_first')
    """

    ORACLE_MODES = ('automated', 'interactive')
    EXAMPLE_MODES = ('example_only', 'example_first')

    def __init__(
            self,
            bias_path: str,
            fm_path: str,
            solver_name: str = 'glucose4',
            max_queries: int = 1000,
            query_mode: str = 'example_only'
    ):
        """
        Initialize runner with file paths. Loads bias for clause resolution.

        Args:
            bias_path: Path to bias file (.json)
            fm_path: Path to feature model (.uvl)
            solver_name: SAT solver name
            max_queries: Maximum membership queries per run
            query_mode: Default query mode for example-based learning
        """
        self.bias_path = bias_path
        self.fm_path = fm_path
        self.solver_name = solver_name
        self.max_queries = max_queries
        self.query_mode = query_mode

        # Load bias for clause resolution + feature_ids (exposed for CV loop)
        from conacq.bias import BiasIO
        bias = BiasIO.load_from_json(bias_path)
        self.bias_clauses = {c.id: c.clauses for c in bias.constraints}
        self.feature_ids = bias.feature_ids

    def run(
            self,
            positive_examples: Optional[List[Dict[str, bool]]] = None,
            negative_examples: Optional[List[Dict[str, bool]]] = None,
            mode: Optional[str] = None,
            shuffle_seed: Optional[int] = None
    ) -> InteractiveRunResult:
        """
        Run interactive learning and collect metrics.

        Mode dispatch:
        - 'automated'/'interactive' -> oracle path via from_files()
        - 'example_only'/'example_first' -> example path via from_examples()

        Args:
            positive_examples: List of E+ (required for example modes)
            negative_examples: List of E- (required for example modes)
            mode: Learning mode. Defaults to self.query_mode for example modes.
            shuffle_seed: If provided, shuffle bias keys with this seed

        Returns:
            InteractiveRunResult with KB and performance metrics
        """
        # Default mode: use query_mode (for CV backward compat)
        if mode is None:
            mode = self.query_mode

        is_oracle_mode = mode in self.ORACLE_MODES
        is_example_mode = mode in self.EXAMPLE_MODES

        if not is_oracle_mode and not is_example_mode:
            raise ValueError(
                f"Unknown mode '{mode}'. Use one of: "
                f"{self.ORACLE_MODES + self.EXAMPLE_MODES}"
            )

        if is_example_mode and (positive_examples is None or negative_examples is None):
            raise ValueError(
                f"Mode '{mode}' requires positive_examples and negative_examples"
            )

        logging.debug('>>> InteractiveRunner.run(mode=%s)', mode)

        # Start memory tracking
        tracemalloc.start()
        start_time = time.perf_counter()

        try:
            # Lazy import to avoid circular dependency
            from conacq.algorithms.interactive import InteractiveLearner
            from explanation.operations.algorithms.profiler import (
                profiler_session, ProfilerPreset
            )

            with profiler_session(ProfilerPreset.BENCHMARK) as profiler:
                if is_oracle_mode:
                    result, learner = self._run_oracle_mode(
                        InteractiveLearner, mode, shuffle_seed
                    )
                else:
                    result, learner = self._run_example_mode(
                        InteractiveLearner, positive_examples,
                        negative_examples, mode, shuffle_seed
                    )

                profiler_snapshot = profiler.to_dict()
                consistency_checks = profiler.get_metric(
                    'paper_consistency_checks',
                    result.consistency_checks
                )

        finally:
            end_time = time.perf_counter()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        runtime_ms = (end_time - start_time) * 1000
        memory_peak_mb = peak / (1024 * 1024)

        # Extract bg_clauses from learner task background
        bg_clauses = (
            [[lit] for lit in learner.task.background]
            if learner.task.background else []
        )

        # Resolve KB constraint IDs → clauses
        kb_clauses = []
        for cid in result.kb_constraints:
            if cid in self.bias_clauses:
                kb_clauses.extend(self.bias_clauses[cid])

        run_result = InteractiveRunResult(
            kb_constraints=result.kb_constraints,
            kb_clauses=kb_clauses,
            bg_clauses=bg_clauses,
            n_bias=len(self.bias_clauses),
            n_kb=result.n_kb,
            n_queries=result.n_queries,
            convergence_reason=result.convergence_reason,
            runtime_ms=runtime_ms,
            consistency_checks=consistency_checks,
            memory_peak_mb=memory_peak_mb,
            profiler_data=profiler_snapshot
        )

        logging.debug('<<< InteractiveRunner: KB=%d, queries=%d, runtime=%.2fms',
                      result.n_kb, result.n_queries, runtime_ms)

        return run_result

    def _run_oracle_mode(self, learner_cls, mode, shuffle_seed):
        """Run oracle-based learning via from_files()."""
        learner = learner_cls.from_files(
            fm_path=self.fm_path,
            bias_path=self.bias_path,
            solver_name=self.solver_name,
            enable_profiling=False
        )

        if shuffle_seed is not None:
            keys = list(learner.task.bias)
            random.Random(shuffle_seed).shuffle(keys)
            learner.task.bias = keys
            logging.debug('Shuffled bias with seed=%d', shuffle_seed)

        result = learner.learn(mode=mode, max_queries=self.max_queries)
        return result, learner

    def _run_example_mode(self, learner_cls, positive_examples,
                          negative_examples, mode, shuffle_seed):
        """Run example-based learning via from_examples()."""
        mixed_examples = list(positive_examples) + list(negative_examples)

        learner = learner_cls.from_examples(
            fm_path=self.fm_path,
            bias_path=self.bias_path,
            examples=mixed_examples,
            seed=shuffle_seed,
            solver_name=self.solver_name,
            enable_profiling=False
        )

        if shuffle_seed is not None:
            keys = list(learner.task.bias)
            random.Random(shuffle_seed).shuffle(keys)
            learner.task.bias = keys
            logging.debug('Shuffled bias with seed=%d', shuffle_seed)

        result = learner.learn_from_examples(
            query_mode=mode,
            max_queries=self.max_queries
        )
        return result, learner

    def cleanup(self):
        """Release resources. No-op — oracle is per-learner, not shared."""
        pass
