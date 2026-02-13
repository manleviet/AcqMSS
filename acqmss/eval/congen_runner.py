"""
Run CONGEN and collect performance metrics.

Runs CONGEN directly to:
1. Support cross-validation (each fold needs to train a new KB)
2. Collect performance metrics (#checks, runtime, memory, n_mss, n_kb)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
import random
import time
import tracemalloc
import logging

from acqmss.algorithms.congen import CONGEN
from acqmss.algorithms.congen_model import CONGENModel
from acqmss.algorithms.generate_ne import GenerateNE, merge_ne_into_task
from explanation.operations.algorithms.checker import (
    IncrementalPySATChecker,
    NonIncrementalPySATChecker
)
from explanation.operations.algorithms.profiler import Profiler, get_global_profiler

from .performance_metrics import PerformanceMetrics


@dataclass
class CONGENRunResult:
    """
    Result of running CONGEN with metrics.

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


class CONGENRunner:
    """
    Run CONGEN and collect performance metrics.

    Metrics collected (Table 7-8 from paper):
    - runtime_ms: Execution time
    - consistency_checks: Number of SAT solver calls
    - memory_peak_mb: Peak memory usage
    - n_mss: MSS size before REDUCE
    - n_kb: Final KB size
    """

    def __init__(
            self,
            bias_clauses: Dict[str, List[List[int]]],
            feature_ids: Dict[str, int],
            solver_name: str = 'glucose4',
            is_incremental: bool = True,
            background_knowledge: Optional[List[int]] = None
    ):
        """
        Initialize runner with bias and feature mapping.

        Args:
            bias_clauses: {constraint_id: clauses} from bias file
            feature_ids: {feature_name: SAT_variable_id}
            solver_name: SAT solver name
            is_incremental: Use incremental solver mode
            background_knowledge: BG literals (e.g., [root_feature_id])
        """
        self.bias_clauses = bias_clauses
        self.feature_ids = feature_ids
        self.solver_name = solver_name
        self.is_incremental = is_incremental
        self.background_knowledge = background_knowledge or []

    def run(
            self,
            positive_examples: List[Dict[str, bool]],
            negative_examples: List[Dict[str, bool]],
            background_clauses: List[List[int]] = None,
            shuffle_seed: Optional[int] = None
    ) -> CONGENRunResult:
        """
        Run CONGEN with given examples and collect metrics.

        Args:
            positive_examples: List of E+ (each is {feature: True/False})
            negative_examples: List of E- (each is {feature: True/False})
            background_clauses: Optional BG clauses (not used currently)
            shuffle_seed: If provided, shuffle bias keys with this seed

        Returns:
            CONGENRunResult with KB and performance metrics
        """
        logging.debug('>>> CONGENRunner.run(E+=%d, E-=%d)',
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
            bias_clauses = self.bias_clauses
            if shuffle_seed is not None:
                keys = list(bias_clauses.keys())
                random.Random(shuffle_seed).shuffle(keys)
                bias_clauses = {k: bias_clauses[k] for k in keys}
                logging.debug('Shuffled bias with seed=%d', shuffle_seed)

            # Create model from bias and examples
            model = CONGENModel.from_bias_and_examples(
                bias_constraints=bias_clauses,
                positive_examples=positive_examples,
                negative_examples=negative_examples,
                feature_ids=self.feature_ids,
                background_knowledge=self.background_knowledge
            )

            # Prepare task based on mode
            mode = "incremental-congen" if self.is_incremental else "non-incremental-congen"
            model.prepare(mode)
            task = model.task

            # Run GenerateNE with temp non-incremental checker
            temp_checker = NonIncrementalPySATChecker(
                task.set_kb, task.assumptions, self.solver_name, profiler
            )
            generate_ne = GenerateNE(temp_checker, profiler)
            ne_result = generate_ne.generate(
                set_e_neg=task.e_neg_literals,
                set_bg=task.set_b,
                start_assumption_id=task.next_assumption_id
            )
            merge_ne_into_task(task, ne_result)

            # Create final checker with complete data (including NE)
            if self.is_incremental:
                checker = IncrementalPySATChecker(
                    task.set_kb, task.assumptions, self.solver_name, profiler
                )
            else:
                checker = NonIncrementalPySATChecker(
                    task.set_kb, task.assumptions, self.solver_name, profiler
                )

            # Run CONGEN
            congen = CONGEN(checker, profiler)
            result = congen.acquire(task)

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

        # Get KB clauses from result constraint IDs
        kb_clauses = []
        for cid in result.kb_constraints:
            if cid in self.bias_clauses:
                kb_clauses.extend(self.bias_clauses[cid])

        run_result = CONGENRunResult(
            kb_constraints=result.kb_constraints,
            kb_clauses=kb_clauses,
            redundant_constraints=result.redundant_constraints,
            n_bias=result.n_bias,
            n_mss=result.n_mss,
            n_kb=result.n_kb,
            runtime_ms=runtime_ms,
            consistency_checks=consistency_checks,
            memory_peak_mb=memory_peak_mb
        )

        logging.debug('<<< CONGENRunner: KB=%d, runtime=%.2fms, checks=%d',
                      result.n_kb, runtime_ms, consistency_checks)

        return run_result
