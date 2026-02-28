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
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from conacq.example_generators import QueryProvider
from explanation.operations.algorithms.checker import CheckerFactory
from explanation.operations.algorithms.profiler import profiler_session, ProfilerPreset
from .base_runner import BaseRunResult, BaseRunner
from ..algorithms import QuAcq
from ..algorithms.quacq.discriminating_generator import DiscriminatingGenerator


@dataclass
class QuAcqRunResult(BaseRunResult):
    """
    Result of running QuAcq (interactive) learning with metrics.

    Inherits 9 shared fields from BaseRunResult.
    Adds: n_queries, convergence_reason, query_history.
    """
    n_queries: int = 0
    convergence_reason: str = ''

    # Query history: (config, answer, source) tuples for progressive pipeline
    query_history: List[Tuple[Dict[str, bool], bool, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = self._base_to_dict()
        d['n_queries'] = self.n_queries
        d['convergence_reason'] = self.convergence_reason
        d['query_history'] = [
            {'config': config, 'answer': answer, 'source': source}
            for config, answer, source in self.query_history
        ]
        return d


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
        return self.model.variables

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

                    if shuffle_seed is not None:
                        random.Random(shuffle_seed).shuffle(task.set_c)
                        logging.debug('Shuffled bias (set_c) with seed=%d', shuffle_seed)

                    # Create checker via factory
                    checker = CheckerFactory.create_from_model(
                        self.model, self.solver_name, profiler
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
            learn_oracle = UserPromptOracle(list(task.feature_ids.keys()))
        else:
            learn_oracle = self.oracle

        query_provider = QueryProvider(checker=checker,
                                       model=self.model,
                                       profiler_instance=profiler)
        discrim_gen = DiscriminatingGenerator(
            background_clauses=task.background_clauses,
            constraint_clauses=task.constraint_clauses,
            negated_clauses=task.negated_clauses,
            id_to_feature=task.id_to_feature,
            solver_name=self.solver_name)

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
                background_clauses=task.background_clauses,
                constraint_clauses=task.constraint_clauses,
                negated_clauses=task.negated_clauses,
                id_to_feature=task.id_to_feature,
                solver_name=self.solver_name)

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
