"""
Run QuAcq (interactive) learning and collect performance metrics.

Supports two modes:
- Oracle mode ('automated'/'interactive'): via QuAcqModel + QuAcq.learn()
- Example mode ('example_only'/'example_first'): via QuAcqModel + QuAcq.learn_from_examples()

Follows rebuild-per-run lifecycle: oracle in __init__(), fresh model+task per run() via builder.
"""

import logging
import random
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from .base_runner import BaseRunResult, BaseRunner


@dataclass
class QuAcqRunResult(BaseRunResult):
    """
    Result of running QuAcq (interactive) learning with metrics.

    Inherits 9 shared fields from BaseRunResult.
    Adds: n_queries, convergence_reason, query_history.
    """
    n_queries: int = 0
    convergence_reason: str = ''

    # Query history: (config, answer, source) tuples for evaluation pipeline
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
        Initialize runner with file paths. Builds oracle once.

        Args:
            bias_path: Path to bias file (.json)
            fm_path: Path to feature model (.uvl)
            solver_name: SAT solver name
            max_queries: Maximum membership queries per run
            query_mode: Default query mode for example-based learning
            use_incremental: Use incremental solver mode for Oracle
        """
        super().__init__(bias_path, fm_path, solver_name, use_incremental=use_incremental)

        # Store builder config (model rebuilt each run via builder)
        self._use_incremental = use_incremental

        # Cache feature IDs from bias (avoids re-reading file on every access)
        from conacq.bias import BiasIO
        self._feature_ids = BiasIO.load_from_json(bias_path).feature_ids

        self.max_queries = max_queries
        self.query_mode = query_mode

    @property
    def feature_ids(self) -> Dict[str, int]:
        """Feature name -> SAT variable ID mapping from bias."""
        return self._feature_ids

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
        - 'automated'/'interactive' -> oracle path via QuAcq.learn()
        - 'example_only'/'example_first' -> example path via QuAcq.learn_from_examples()

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

        # Start memory tracking
        tracemalloc.start()
        start_time = time.perf_counter()

        try:
            from conacq.algorithms.quacq.quacq import QuAcq
            from explanation.operations.algorithms.profiler import (
                profiler_session, ProfilerPreset
            )

            with profiler_session(ProfilerPreset.BENCHMARK) as profiler:
                # Build fresh model per run via builder
                from conacq.algorithms.quacq.quacq_model_builder import QuAcqModelBuilder
                model = (QuAcqModelBuilder
                         .from_bias(self.bias_path)
                         .with_oracle(self.oracle)
                         .use_incremental(self._use_incremental)
                         .build())
                task = model.task

                if shuffle_seed is not None:
                    random.Random(shuffle_seed).shuffle(task.set_c)
                    logging.debug('Shuffled bias (set_c) with seed=%d', shuffle_seed)

                quacq = QuAcq(self.solver_name, profiler)

                if is_oracle_mode:
                    result = self._run_oracle_mode(
                        quacq, task, self.oracle, model.description_provider, mode)
                else:
                    result = self._run_example_mode(
                        quacq, task, self.oracle, model.description_provider,
                        positive_examples, negative_examples,
                        mode, shuffle_seed)

                # Resolve KB clauses and BG clauses
                _, kb_clauses = model.resolve_kb(result.kb_assumption_ids)
                bg_clauses = self.oracle.get_root_clauses()

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

        run_result = QuAcqRunResult(
            kb_constraints=result.kb_constraints,
            kb_clauses=kb_clauses,
            bg_clauses=bg_clauses,
            n_bias=len(model.constraint_map),
            n_kb=result.n_kb,
            n_queries=result.n_queries,
            convergence_reason=result.convergence_reason,
            runtime_ms=runtime_ms,
            consistency_checks=consistency_checks,
            memory_peak_mb=memory_peak_mb,
            profiler_data=profiler_snapshot,
            query_history=result.query_history
        )

        logging.debug('<<< QuAcqRunner: KB=%d, queries=%d, runtime=%.2fms',
                      result.n_kb, result.n_queries, runtime_ms)

        return run_result

    def _run_oracle_mode(self, quacq, task, oracle, description_provider, mode):
        """Run oracle-based learning via QuAcq.learn()."""
        if mode == 'interactive':
            from conacq.oracle import UserPromptOracle
            learn_oracle = UserPromptOracle(list(task.feature_ids.keys()))
        else:
            learn_oracle = oracle

        return quacq.learn(
            task, learn_oracle, description_provider,
            max_queries=self.max_queries)

    def _run_example_mode(self, quacq, task, oracle, description_provider,
                          positive_examples, negative_examples,
                          mode, shuffle_seed):
        """Run example-based learning via QuAcq.learn_from_examples()."""
        from conacq.example_generators import ExampleProvider

        mixed_examples = list(positive_examples) + list(negative_examples)
        example_provider = ExampleProvider(mixed_examples, shuffle_seed)

        return quacq.learn_from_examples(
            task, example_provider, oracle,
            description_provider,
            query_mode=mode, max_queries=self.max_queries)
