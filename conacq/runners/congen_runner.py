"""
Run ConGen and collect performance metrics.

Runs ConGen directly to:
1. Support cross-validation (each fold needs to train a new KB)
2. Collect performance metrics (#checks, runtime, memory, n_mss, n_kb)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import random
import time
import tracemalloc
import logging

from conacq.algorithms.congen import ConGen
from conacq.algorithms.acqmss.congen_model_builder import ConGenModelBuilder
from conacq.oracle import FeatureModelOracle
from explanation.operations.algorithms.checker import CheckerFactory
from explanation.operations.algorithms.profiler import Profiler

from conacq.eval.performance_metrics import PerformanceMetrics


@dataclass
class ConGenRunResult:
    """
    Result of running ConGen with metrics.

    Attributes:
        kb_constraints: List of constraint IDs in learned KB
        kb_clauses: CNF clauses of the learned KB
        redundant_constraints: List of redundant constraint IDs
        n_bias: Original number of bias constraints
        n_mss: Size of MSS before REDUCE
        n_kb: Final KB size
        runtime_ms: Execution time in milliseconds
        consistency_checks: Number of SAT solver calls
        memory_peak_mb: Peak memory usage in MB
    """
    # KB result
    kb_constraints: List[str]
    kb_clauses: List[List[int]]
    redundant_constraints: List[str]
    n_bias: int
    n_mss: int
    n_kb: int

    # Performance metrics
    runtime_ms: float
    consistency_checks: int
    memory_peak_mb: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'kb_constraints': self.kb_constraints,
            'redundant_constraints': self.redundant_constraints,
            'n_bias': self.n_bias,
            'n_mss': self.n_mss,
            'n_kb': self.n_kb,
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
            n_mss=self.n_mss,
            n_kb=self.n_kb
        )


class ConGenRunner:
    """
    Run ConGen and collect performance metrics.

    Builds model once from file paths, reuses via prepare() per fold.

    Metrics collected (Table 7-8 from paper):
    - runtime_ms: Execution time
    - consistency_checks: Number of SAT solver calls
    - memory_peak_mb: Peak memory usage
    - n_mss: MSS size before REDUCE
    - n_kb: Final KB size
    """

    def __init__(
            self,
            bias_path: str,
            fm_path: str,
            solver_name: str = 'glucose4',
            is_incremental: bool = True
    ):
        """
        Initialize runner with file paths. Builds model once (without examples).

        Args:
            bias_path: Path to bias JSON file
            fm_path: Path to feature model (.uvl) file
            solver_name: SAT solver name
            is_incremental: Use incremental solver mode
        """
        self.solver_name = solver_name
        self.is_incremental = is_incremental

        # Build model (bias only)
        self.model = (ConGenModelBuilder
                      .from_bias(bias_path)
                      .use_incremental(is_incremental)
                      .build())

        # Create oracle (reused across folds)
        self.oracle = FeatureModelOracle(fm_path, use_incremental=False)

        # Keep original bias order for shuffle restore
        self._original_constraint_order = list(self.model.constraint_map.keys())

    def run(
            self,
            positive_examples: List[Dict[str, bool]],
            negative_examples: List[Dict[str, bool]],
            shuffle_seed: Optional[int] = None
    ) -> ConGenRunResult:
        """
        Run ConGen with given examples and collect metrics.

        Args:
            positive_examples: List of E+ (each is {feature: True/False})
            negative_examples: List of E- (each is {feature: True/False})
            shuffle_seed: If provided, shuffle bias keys with this seed

        Returns:
            ConGenRunResult with KB and performance metrics
        """
        logging.debug('>>> ConGenRunner.run(E+=%d, E-=%d)',
                      len(positive_examples), len(negative_examples))

        # Create profiler to collect metrics
        profiler = Profiler()
        profiler.start()

        # Start memory tracking
        tracemalloc.start()
        start_time = time.perf_counter()

        checker = None
        try:
            # Shuffle bias ordering if seed provided
            if shuffle_seed is not None:
                keys = list(self._original_constraint_order)
                random.Random(shuffle_seed).shuffle(keys)
                self.model.constraint_map = {k: self.model.constraint_map[k] for k in keys}
                logging.debug('Shuffled bias with seed=%d', shuffle_seed)

            # Prepare for this fold's examples (runs GenerateNE)
            self.model.prepare(
                oracle=self.oracle,
                positive_examples=positive_examples,
                negative_examples=negative_examples
            )
            task = self.model.task

            # Create checker via factory
            checker = CheckerFactory.create_from_model(
                self.model, self.solver_name, profiler
            )

            # Run ConGen
            congen = ConGen(checker, profiler)
            result = congen.acquire(
                set_b=task.set_c,
                set_bg=task.set_b,
                set_tc=task.set_tc,
                set_neg_tv=task.set_neg_tv,
                negation_map=task.negation_map,
            )

        finally:
            # Stop timing and memory tracking
            end_time = time.perf_counter()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Stop profiler
            profiler.stop()

            # Cleanup checker
            if checker is not None:
                checker.cleanup()

        runtime_ms = (end_time - start_time) * 1000
        memory_peak_mb = peak / (1024 * 1024)
        consistency_checks = profiler.get_metric('paper_consistency_checks', 0)

        # Get KB clauses: assumption_id → name → clauses
        provider = self.model.description_provider
        kb_clauses = []
        kb_names = []
        redundant_names = []
        for aid in result.kb_assumption_ids:
            cname = provider.get_description(aid)
            kb_names.append(cname)
            if cname in self.model.constraint_map:
                kb_clauses.extend(self.model.constraint_map[cname])
        for aid in result.redundant_ids:
            redundant_names.append(provider.get_description(aid))

        run_result = ConGenRunResult(
            kb_constraints=kb_names,
            kb_clauses=kb_clauses,
            redundant_constraints=redundant_names,
            n_bias=result.n_bias,
            n_mss=result.n_mss,
            n_kb=result.n_kb,
            runtime_ms=runtime_ms,
            consistency_checks=consistency_checks,
            memory_peak_mb=memory_peak_mb
        )

        logging.debug('<<< ConGenRunner: KB=%d, runtime=%.2fms, checks=%d',
                      result.n_kb, runtime_ms, consistency_checks)

        return run_result

    def cleanup(self):
        """Release oracle resources."""
        if hasattr(self, 'oracle') and self.oracle is not None:
            self.oracle.cleanup()
