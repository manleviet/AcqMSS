"""
Run ConGen and collect performance metrics.

Runs ConGen directly to:
1. Support cross-validation (each fold needs to train a new KB)
2. Collect performance metrics (#checks, runtime, memory, n_mss, n_kb)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
import random
import tracemalloc
import logging

from conacq.algorithms.acqmss.congen import ConGen
from conacq.algorithms.acqmss.congen_model_builder import ConGenModelBuilder
from explanation.operations.algorithms.checker import CheckerFactory
from explanation.operations.algorithms.profiler import profiler_session, ProfilerPreset

from conacq.eval.performance_metrics import PerformanceMetrics
from .base_runner import BaseRunResult, BaseRunner


@dataclass
class ConGenRunResult(BaseRunResult):
    """
    Result of running ConGen with metrics.

    Inherits 9 shared fields from BaseRunResult.
    Adds ConGen-specific: redundant_constraints, n_mss, extended profiler metrics.
    """
    redundant_constraints: List[str] = field(default_factory=list)
    n_mss: int = 0

    # Extended profiler metrics
    congen_runtime_ms: float = 0.0
    acqmss_runtime_ms: float = 0.0
    acqmss_calls: int = 0
    reduce_runtime_ms: float = 0.0
    solver_time_ms: float = 0.0
    is_consistent_calls: int = 0
    is_consistent_test_cases_calls: int = 0
    redundancy_consistency_checks: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = self._base_to_dict()
        d['redundant_constraints'] = self.redundant_constraints
        d['n_mss'] = self.n_mss
        d['performance'].update({
            'congen_runtime_ms': self.congen_runtime_ms,
            'acqmss_runtime_ms': self.acqmss_runtime_ms,
            'acqmss_calls': self.acqmss_calls,
            'reduce_runtime_ms': self.reduce_runtime_ms,
            'solver_time_ms': self.solver_time_ms,
            'is_consistent_calls': self.is_consistent_calls,
            'is_consistent_test_cases_calls': self.is_consistent_test_cases_calls,
            'redundancy_consistency_checks': self.redundancy_consistency_checks,
        })
        return d

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics including ConGen-specific n_mss."""
        return PerformanceMetrics(
            runtime_ms=self.runtime_ms,
            consistency_checks=self.consistency_checks,
            memory_peak_mb=self.memory_peak_mb,
            n_mss=self.n_mss,
            n_kb=self.n_kb,
            congen_runtime_ms=self.congen_runtime_ms,
            acqmss_runtime_ms=self.acqmss_runtime_ms,
            acqmss_calls=self.acqmss_calls,
            reduce_runtime_ms=self.reduce_runtime_ms,
            solver_time_ms=self.solver_time_ms,
            is_consistent_calls=self.is_consistent_calls,
            is_consistent_test_cases_calls=self.is_consistent_test_cases_calls,
            redundancy_consistency_checks=self.redundancy_consistency_checks,
        )


class ConGenRunner(BaseRunner):
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
            use_incremental: bool = True
    ):
        """
        Initialize runner with file paths. Builds model once (without examples).

        Args:
            bias_path: Path to bias JSON file
            fm_path: Path to feature model (.uvl) file
            solver_name: SAT solver name
            use_incremental: Use incremental solver mode
        """
        super().__init__(bias_path, fm_path, solver_name, use_incremental=use_incremental)

        # Build model (bias + negation, no examples yet)
        self.model = (ConGenModelBuilder
                      .from_bias(bias_path)
                      .with_oracle(self.oracle)
                      .use_incremental(use_incremental)
                      .build())

        # Keep original bias order for shuffle restore
        self._original_bias_constraint_order = list(self.model.constraint_map.keys())

    @property
    def feature_ids(self) -> Dict[str, int]:
        """Feature name -> SAT variable ID mapping."""
        return self.model.variables

    def run(
            self,
            positive_examples: Optional[List[Dict[str, bool]]] = None,
            negative_examples: Optional[List[Dict[str, bool]]] = None,
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
        with profiler_session(ProfilerPreset.BENCHMARK) as profiler:
            # Start memory tracking
            tracemalloc.start()
            with profiler.timer("congen_total_time"):
                checker = None
                try:
                    # Shuffle bias ordering if seed provided
                    if shuffle_seed is not None:
                        keys = list(self._original_bias_constraint_order)
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
                    # Stop memory tracking
                    current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()

                    # Cleanup checker
                    if checker is not None:
                        checker.cleanup()

            # Extract core metrics
            timer_values = profiler.get_metric('congen_total_time', [0])
            runtime_ms = timer_values[0] * 1000 if timer_values else 0
            memory_peak_mb = peak / (1024 * 1024)
            consistency_checks = profiler.get_metric('paper_consistency_checks', 0)

            # Extract extended profiler metrics (timers are lists, sum all calls)
            congen_runtime_ms = sum(profiler.get_metric('congen_runtime', [0])) * 1000
            acqmss_runtime_ms = sum(profiler.get_metric('acqmss_runtime', [0])) * 1000
            reduce_runtime_ms = sum(profiler.get_metric('reduce_runtime', [0])) * 1000
            solver_time_ms = sum(profiler.get_metric('solver_time', [0])) * 1000
            acqmss_calls = profiler.get_metric('acqmss_calls', 0)
            is_consistent_calls = profiler.get_metric('is_consistent_calls', 0)
            is_consistent_test_cases_calls = profiler.get_metric('is_consistent_test_cases_calls', 0)
            redundancy_consistency_checks = profiler.get_metric('redundancy_consistency_checks', 0)

            profiler_snapshot = profiler.to_dict()

            # Resolve assumption IDs -> clauses/names via model
            bg_clauses, kb_clauses, kb_names, redundant_names = \
                self.model.resolve_result(result)

            run_result = ConGenRunResult(
                kb_constraints=kb_names,
                kb_clauses=kb_clauses,
                bg_clauses=bg_clauses,
                redundant_constraints=redundant_names,
                n_bias=result.n_bias,
                n_mss=result.n_mss,
                n_kb=result.n_kb,
                runtime_ms=runtime_ms,
                consistency_checks=consistency_checks,
                memory_peak_mb=memory_peak_mb,
                congen_runtime_ms=congen_runtime_ms,
                acqmss_runtime_ms=acqmss_runtime_ms,
                acqmss_calls=acqmss_calls,
                reduce_runtime_ms=reduce_runtime_ms,
                solver_time_ms=solver_time_ms,
                is_consistent_calls=is_consistent_calls,
                is_consistent_test_cases_calls=is_consistent_test_cases_calls,
                redundancy_consistency_checks=redundancy_consistency_checks,
                profiler_data=profiler_snapshot
            )

            logging.debug('<<< ConGenRunner: KB=%d, runtime=%.2fms, checks=%d',
                          result.n_kb, runtime_ms, consistency_checks)

        return run_result
