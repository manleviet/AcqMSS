"""
Run ConGen and collect performance metrics.

Runs ConGen directly to:
1. Support cross-validation (each fold needs to train a new KB)
2. Collect performance metrics (#checks, runtime, memory, n_mss, n_kb)
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field, replace
import random
import tracemalloc
import logging

from conacq.algorithms.acqmss.congen import ConGen
from conacq.algorithms.acqmss.congen_model_builder import ConGenModelBuilder
from explanation.api import build_checker, SolverBackend
from profiling import profiler_session, ProfilerPreset

from .base_runner import BaseRunResult, BaseRunner
from .metrics import CONGEN_METRICS, collect


@dataclass
class ConGenRunResult(BaseRunResult):
    """
    Result of running ConGen with metrics.

    Inherits the shared fields from BaseRunResult (including the declarative
    ``metrics`` RunMetrics bundle). Adds ConGen-specific: redundant_constraints,
    n_mss. The extended profiler metrics are no longer hand-listed here — they
    live in ``metrics`` (built via ``collect(profiler, CONGEN_METRICS)``).
    """
    redundant_constraints: List[str] = field(default_factory=list)
    n_mss: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = self._base_to_dict()
        d['redundant_constraints'] = self.redundant_constraints
        d['n_mss'] = self.n_mss
        return d


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

    @property
    def feature_ids(self) -> Dict[str, int]:
        """Feature name -> SAT variable ID mapping (a plain dict — see ADR-0007)."""
        return self.model.name_to_id

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
                    # Prepare for this fold's examples (runs GenerateNE)
                    self.model.prepare(
                        oracle=self.oracle,
                        positive_examples=positive_examples,
                        negative_examples=negative_examples
                    )
                    task = self.model.task

                    # Shuffle bias iteration order if seed provided.
                    # Task is frozen: shuffle a copy and rebind, never mutate in place.
                    if shuffle_seed is not None:
                        shuffled_set_c = list(task.set_c)
                        random.Random(shuffle_seed).shuffle(shuffled_set_c)
                        task = replace(task, set_c=shuffled_set_c)
                        logging.debug('Shuffled set_c with seed=%d', shuffle_seed)

                    # Build the checker from the running task (which may have
                    # been shuffled — model.task holds the un-shuffled order).
                    checker = build_checker(
                        task,
                        SolverBackend.from_flags(use_incremental=self.model.use_incremental),
                        self.solver_name, profiler
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

            # Collect metrics declaratively from the profiler + the values that
            # do not live in it (memory from tracemalloc, KB sizes from result).
            memory_peak_mb = peak / (1024 * 1024)
            run_metrics = collect(profiler, CONGEN_METRICS, extra={
                'memory_peak_mb': memory_peak_mb,
                'n_mss': result.n_mss,
                'n_kb': result.n_kb,
            })
            runtime_ms = run_metrics.values['runtime_ms']
            consistency_checks = run_metrics.values['consistency_checks']

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
                metrics=run_metrics,
                profiler_data=profiler_snapshot
            )

            logging.debug('<<< ConGenRunner: KB=%d, runtime=%.2fms, checks=%d',
                          result.n_kb, runtime_ms, consistency_checks)

        return run_result
