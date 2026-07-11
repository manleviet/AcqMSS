"""
Run QuAcq (interactive) learning and collect performance metrics.

Supports three modes:
- Oracle mode ('automated'/'interactive'): via QuAcqModel + QuAcq.learn(mode='oracle')
- Example mode ('example_only'/'example_first'): via QuAcqModel + QuAcq.learn(mode=...)

Builds model once in __init__(), re-prepares per run() for fresh task.
"""

import logging
import random
import tracemalloc
from dataclasses import dataclass, field, replace
from typing import List, Dict, Optional, Tuple

from conacq.example_generators import QueryProvider
from explanation.api import CheckerFactory
from profiling import profiler_session, ProfilerPreset
from .base_runner import BaseRunResult, BaseRunner
from ..algorithms import QuAcq
from ..algorithms.quacq.discriminating_generator import DiscriminatingGenerator
from ..eval import PerformanceMetrics


@dataclass
class QuAcqRunResult(BaseRunResult):
    """
    Result of running QuAcq (interactive) learning with metrics.

    Inherits 9 shared fields from BaseRunResult.
    Adds: n_queries, convergence_reason, query_history.
    """
    n_queries: int = 0
    convergence_reason: str = ''

    # Extended profiler metrics
    quacq_runtime_ms: float = 0.0
    query_generation_runtime_ms: float = 0.0
    findscope_runtime_ms: float = 0.0
    findc_runtime_ms: float = 0.0
    dis_gen_runtime_ms: float = 0.0
    reduce_runtime_ms: float = 0.0
    solver_time_ms: float = 0.0

    is_consistent_calls: int = 0
    is_consistent_test_cases_calls: int = 0
    quacq_calls: int = 0
    query_generation_calls: int = 0
    query_generation_consistency_checks: int = 0
    prune_calls: int = 0
    prune_is_consistent_calls: int = 0
    findscope_calls: int = 0
    findc_calls: int = 0
    findc_consistency_checks: int = 0
    dis_gen_calls: int = 0
    dis_gen_consistency_checks: int = 0
    reduce_calls: int = 0
    redundancy_consistency_checks: int = 0

    # Query history: (config, answer, source) tuples for progressive pipeline
    query_history: List[Tuple[Dict[str, bool], bool, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = self._base_to_dict()
        d['n_queries'] = self.n_queries
        d['convergence_reason'] = self.convergence_reason
        d['performance'].update({
            'quacq_runtime_ms': self.quacq_runtime_ms,
            'query_generation_runtime_ms': self.query_generation_runtime_ms,
            'findscope_runtime_ms': self.findscope_runtime_ms,
            'findc_runtime_ms': self.findc_runtime_ms,
            'dis_gen_runtime_ms': self.dis_gen_runtime_ms,
            'reduce_runtime_ms': self.reduce_runtime_ms,
            'solver_time_ms': self.solver_time_ms,
            'is_consistent_calls': self.is_consistent_calls,
            'is_consistent_test_cases_calls': self.is_consistent_test_cases_calls,
            'quacq_calls': self.quacq_calls,
            'query_generation_calls': self.query_generation_calls,
            'query_generation_consistency_checks': self.query_generation_consistency_checks,
            'prune_calls': self.prune_calls,
            'prune_is_consistent_calls': self.prune_is_consistent_calls,
            'findscope_calls': self.findscope_calls,
            'findc_calls': self.findc_calls,
            'findc_consistency_checks': self.findc_consistency_checks,
            'dis_gen_calls': self.dis_gen_calls,
            'dis_gen_consistency_checks': self.dis_gen_consistency_checks,
            'reduce_calls': self.reduce_calls,
            'redundancy_consistency_checks': self.redundancy_consistency_checks,
        })
        d['query_history'] = [
            {'config': config, 'answer': answer, 'source': source}
            for config, answer, source in self.query_history
        ]
        return d

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get performance metrics including QuAcq-specific metrics."""
        return PerformanceMetrics(
            runtime_ms=self.runtime_ms,
            consistency_checks=self.consistency_checks,
            memory_peak_mb=self.memory_peak_mb,
            n_kb=self.n_kb,
            quacq_runtime_ms=self.quacq_runtime_ms,
            query_generation_runtime_ms=self.query_generation_runtime_ms,
            findscope_runtime_ms=self.findscope_runtime_ms,
            findc_runtime_ms=self.findc_runtime_ms,
            dis_gen_runtime_ms=self.dis_gen_runtime_ms,
            reduce_runtime_ms=self.reduce_runtime_ms,
            solver_time_ms=self.solver_time_ms,
            is_consistent_calls=self.is_consistent_calls,
            is_consistent_test_cases_calls=self.is_consistent_test_cases_calls,
            quacq_calls=self.quacq_calls,
            query_generation_calls=self.query_generation_calls,
            query_generation_consistency_checks=self.query_generation_consistency_checks,
            prune_calls=self.prune_calls,
            prune_is_consistent_calls=self.prune_is_consistent_calls,
            findscope_calls=self.findscope_calls,
            findc_calls=self.findc_calls,
            findc_consistency_checks=self.findc_consistency_checks,
            dis_gen_calls=self.dis_gen_calls,
            dis_gen_consistency_checks=self.dis_gen_consistency_checks,
            reduce_calls=self.reduce_calls,
            redundancy_consistency_checks=self.redundancy_consistency_checks
        )


def _learn_params_from_task(task) -> dict:
    """Extract flat learn() params from QuAcqTask."""
    return dict(
        set_c=task.set_c,
        set_b=task.set_b,
        negation_map=task.negation_map,
    )


class QuAcqRunner(BaseRunner):
    """
    Run QuAcq (interactive) learning and collect performance metrics.

    Uses QuAcqModel + QuAcq with assumption-based constraint IDs.
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
            query_mode: str = 'example_only',
            use_incremental: bool = True
    ):
        """
        Initialize runner with file paths. Builds model once (expensive negation here).

        Args:
            bias_path: Path to bias file (.json)
            fm_path: Path to feature model (.uvl)
            solver_name: SAT solver name
            max_queries: Maximum membership queries per run
            query_mode: Default query mode for example-based learning
            use_incremental: Use incremental solver mode for Oracle
        """
        super().__init__(bias_path, fm_path, solver_name, use_incremental=use_incremental)

        # Build model once (expensive negation computed here, not per run)
        from conacq.algorithms.quacq.quacq_model_builder import QuAcqModelBuilder
        self.model = (QuAcqModelBuilder
                      .from_bias(bias_path)
                      .with_oracle(self.oracle)
                      .use_incremental(use_incremental)
                      .build())
        self.max_queries = max_queries
        self.query_mode = query_mode

    @property
    def feature_ids(self) -> Dict[str, int]:
        """Feature name -> SAT variable ID mapping from bias."""
        return self.model.name_to_id

    def run(
            self,
            positive_examples: Optional[List[Dict[str, bool]]] = None,
            negative_examples: Optional[List[Dict[str, bool]]] = None,
            mode: Optional[str] = None,
            shuffle_seed: Optional[int] = None
    ) -> QuAcqRunResult:
        """
        Run QuAcq learning and collect metrics.

        Mode dispatch:
        - 'automated'/'interactive' -> oracle path
        - 'example_only'/'example_first' -> example path

        Args:
            positive_examples: List of E+ (required for example modes)
            negative_examples: List of E- (required for example modes)
            mode: Learning mode. Defaults to self.query_mode for example modes.
            shuffle_seed: If provided, shuffle bias keys with this seed

        Returns:
            QuAcqRunResult with KB and performance metrics
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

        logging.debug('>>> QuAcqRunner.run(mode=%s)', mode)

        # Create profiler to collect metrics
        with profiler_session(ProfilerPreset.BENCHMARK) as profiler:
            # Start memory tracking
            tracemalloc.start()
            with profiler.timer("quacq_total_time"):
                checker = None
                try:
                    # Re-prepare model for this run (fresh task, reuses negation)
                    self.model.prepare(self.oracle)
                    task = self.model.task

                    # Task is frozen: shuffle a copy and rebind, never mutate in place.
                    if shuffle_seed is not None:
                        shuffled_set_c = list(task.set_c)
                        random.Random(shuffle_seed).shuffle(shuffled_set_c)
                        task = replace(task, set_c=shuffled_set_c)
                        logging.debug('Shuffled bias (set_c) with seed=%d', shuffle_seed)

                    # Create checker via factory
                    checker = CheckerFactory.create_from_task(
                        self.model.task, self.solver_name,
                        self.model.use_incremental, profiler
                    )

                    # Extract flat params from task
                    task_data = _learn_params_from_task(task)

                    if is_oracle_mode:
                        result = self._run_oracle_mode(
                            checker, task, task_data, profiler, mode)
                    else:
                        result = self._run_example_mode(
                            checker, task, task_data, profiler,
                            positive_examples, negative_examples,
                            mode, shuffle_seed)

                finally:
                    current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()

                    # Cleanup checker
                    if checker is not None:
                        checker.cleanup()

            # Extract core metrics
            timer_values = profiler.get_metric('quacq_total_time', [0])
            runtime_ms = timer_values[0] * 1000 if timer_values else 0
            memory_peak_mb = peak / (1024 * 1024)
            consistency_checks = profiler.get_metric('paper_consistency_checks', 0)

            # Extract extended profiler metrics (timers are lists, sum all calls)
            quacq_runtime_ms = sum(profiler.get_metric('quacq_runtime', [0])) * 1000
            query_generation_runtime_ms = sum(profiler.get_metric('query_generation_runtime', [0])) * 1000
            findscope_runtime_ms = sum(profiler.get_metric('findscope_runtime', [0])) * 1000
            findc_runtime_ms = sum(profiler.get_metric('findc_runtime', [0])) * 1000
            dis_gen_runtime_ms = sum(profiler.get_metric('dis_gen_runtime', [0])) * 1000
            reduce_runtime_ms = sum(profiler.get_metric('reduce_runtime', [0])) * 1000
            solver_time_ms = sum(profiler.get_metric('solver_time', [0])) * 1000

            is_consistent_calls = profiler.get_metric('is_consistent_calls', 0)
            is_consistent_test_cases_calls = profiler.get_metric('is_consistent_test_cases_calls', 0)
            quacq_calls = profiler.get_metric('quacq_calls', 0)
            query_generation_calls = profiler.get_metric('query_generation_calls', 0)
            query_generation_consistency_checks = profiler.get_metric('query_generation_consistency_checks', 0)
            prune_calls = profiler.get_metric('prune_calls', 0)
            prune_is_consistent_calls = profiler.get_metric('prune_is_consistent_calls', 0)
            findscope_calls = profiler.get_metric('findscope_calls', 0)
            findc_calls = profiler.get_metric('findc_calls', 0)
            findc_consistency_checks = profiler.get_metric('findc_consistency_checks', 0)
            dis_gen_calls = profiler.get_metric('dis_gen_calls', 0)
            dis_gen_consistency_checks = profiler.get_metric('dis_gen_consistency_checks', 0)
            reduce_calls = profiler.get_metric('reduce_calls', 0)
            redundancy_consistency_checks = profiler.get_metric('redundancy_consistency_checks', 0)

            profiler_snapshot = profiler.to_dict()

            # Resolve KB names and clauses, get BG clauses
            kb_names, kb_clauses = self.model.resolve_kb(result.kb_assumption_ids)
            bg_clauses = self.oracle.get_root_clauses()

            run_result = QuAcqRunResult(
                kb_constraints=kb_names,
                kb_clauses=kb_clauses,
                bg_clauses=bg_clauses,
                n_bias=len(self.model.constraint_map),
                n_kb=len(result.kb_assumption_ids),
                n_queries=result.n_queries,
                convergence_reason=result.convergence_reason,
                runtime_ms=runtime_ms,
                consistency_checks=consistency_checks,
                memory_peak_mb=memory_peak_mb,
                quacq_runtime_ms=quacq_runtime_ms,
                query_generation_runtime_ms=query_generation_runtime_ms,
                findscope_runtime_ms=findscope_runtime_ms,
                findc_runtime_ms=findc_runtime_ms,
                dis_gen_runtime_ms=dis_gen_runtime_ms,
                reduce_runtime_ms=reduce_runtime_ms,
                solver_time_ms=solver_time_ms,
                is_consistent_calls=is_consistent_calls,
                is_consistent_test_cases_calls=is_consistent_test_cases_calls,
                quacq_calls=quacq_calls,
                query_generation_calls=query_generation_calls,
                query_generation_consistency_checks=query_generation_consistency_checks,
                prune_calls=prune_calls,
                prune_is_consistent_calls=prune_is_consistent_calls,
                findscope_calls=findscope_calls,
                findc_calls=findc_calls,
                findc_consistency_checks=findc_consistency_checks,
                dis_gen_calls=dis_gen_calls,
                dis_gen_consistency_checks=dis_gen_consistency_checks,
                reduce_calls=reduce_calls,
                redundancy_consistency_checks=redundancy_consistency_checks,
                profiler_data=profiler_snapshot,
                query_history=result.query_history
            )

            logging.debug('<<< QuAcqRunner: KB=%d, queries=%d, runtime=%.2fms',
                          len(result.kb_assumption_ids), result.n_queries, runtime_ms)

        return run_result

    def _run_oracle_mode(self, checker, task, task_data, profiler, mode):
        """Run oracle-based learning via QuAcq.learn(mode='oracle')."""
        if mode == 'interactive':
            from conacq.oracle import UserPromptOracle
            # learn_oracle = UserPromptOracle(list(task.feature_ids.keys()))
            learn_oracle = UserPromptOracle(list(self.model.name_to_id.keys()))
        else:
            learn_oracle = self.oracle

        query_provider = QueryProvider(checker=checker,
                                       model=self.model,
                                       profiler_instance=profiler)
        discrim_gen = DiscriminatingGenerator(
            checker=checker,
            model=self.model,
            profiler=profiler,
            root_assumption=task.set_b[0])

        quacq = QuAcq.for_oracle(checker, learn_oracle, query_provider, discrim_gen,
                                 model=self.model, profiler=profiler)

        return quacq.learn(
            **task_data, mode='oracle',
            max_queries=self.max_queries)

    def _run_example_mode(self, checker, task, task_data, profiler,
                          positive_examples, negative_examples,
                          mode, shuffle_seed):
        """Run example-based learning via QuAcq.learn(mode=...)."""
        mixed_examples = list(positive_examples) + list(negative_examples)
        query_provider = QueryProvider(
            pool=mixed_examples,
            seed=shuffle_seed,
            checker=checker,
            model=self.model,
            profiler_instance=profiler)

        # For example_first, also need discrim_gen
        discrim_gen = None
        if mode == 'example_first':
            discrim_gen = DiscriminatingGenerator(
                checker=checker,
                model=self.model,
                profiler=profiler,
                root_assumption=task.set_b[0])

        quacq = QuAcq(
            checker=checker,
            oracle=self.oracle,
            model=self.model,
            query_provider=query_provider,
            discriminating_generator=discrim_gen,
            profiler_instance=profiler)

        return quacq.learn(
            **task_data, mode=mode,
            max_queries=self.max_queries)
