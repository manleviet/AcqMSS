"""
Run ConMin and collect performance metrics.

Runs ConMin (passive maximally-general acquisition, paper Algorithm 1) directly to:
1. Support cross-validation (each fold trains a fresh KB)
2. Collect performance metrics (#checks, runtime, memory, n_mss, n_kb, cover)

Mirrors ``ConGenRunner`` (build-once model → per-fold prepare → build_checker →
acquire → collect → resolve). ConMin-specific: the acquire call wires the full
lines-5-8 inputs (neg_encodings + support_count), a runner-side guard raises on
E⁻-present-but-no-encodings (foot-gun #5: a silent-empty KB), and the result carries
the 5-part decomposition (learned FM / ¬e⁻ fallback / root) for the P4d eval.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field, replace
import random
import tracemalloc
import logging

from conacq.algorithms.conmin import ConMin, ConMinModelBuilder, ConMinTaskInput
from explanation.api import build_checker, SolverBackend
from profiling import profiler_session, ProfilerPreset

from .base_runner import BaseRunResult, BaseRunner
from .metrics import CONMIN_METRICS, collect


@dataclass
class ConMinRunResult(BaseRunResult):
    """Result of running ConMin with metrics.

    Inherits the shared BaseRunResult fields (kb_constraints/kb_clauses/bg_clauses,
    the RunMetrics bundle, …). Adds ConGen-parallel fields (redundant_constraints,
    n_mss) so the generic CV loop's ``getattr`` reads succeed, plus the ConMin
    decomposition the P4d eval consumes: the ¬e⁻ ``fallback_clauses`` and the three
    passive-strategy slices (A / cover / KB), and the AcqMinCover diagnostics.
    """
    redundant_constraints: List[str] = field(default_factory=list)
    n_mss: int = 0
    # 5-part decomposition (bg=bg_clauses, kb=kb_clauses/kb_constraints inherited).
    fallback_clauses: List[List[int]] = field(default_factory=list)
    # Passive-strategy slices (design brief §9a) for the P4d comparison conditions.
    mss_ids: List[int] = field(default_factory=list)
    cover_ids: List[int] = field(default_factory=list)
    kb_assumption_ids: List[int] = field(default_factory=list)
    # AcqMinCover diagnostics. NOTE: n_uncoverable is |U| (pre-Reduce); Reduce may
    # drop an entailed ¬e⁻, so len(fallback_clauses) ≤ n_uncoverable — the two are
    # distinct quantities, never read n_uncoverable as the delivered-fallback count.
    n_components: int = 0
    largest_component: int = 0
    n_greedy_fallback: int = 0
    n_uncoverable: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.

        Keeps the base schema (kb_constraints/bg_clauses/statistics/performance) that
        run_compare / extract_results consume, and nests the ConMin-only decomposition
        under a ``conmin`` block so those consumers are untouched.
        """
        d = self._base_to_dict()
        d['redundant_constraints'] = self.redundant_constraints
        d['n_mss'] = self.n_mss
        d['conmin'] = {
            'kb_clauses': self.kb_clauses,
            'fallback_clauses': self.fallback_clauses,
            'slices': {
                'mss_ids': self.mss_ids,
                'cover_ids': self.cover_ids,
                'kb_assumption_ids': self.kb_assumption_ids,
            },
            'cover': {
                'n_components': self.n_components,
                'largest_component': self.largest_component,
                'n_greedy_fallback': self.n_greedy_fallback,
                'n_uncoverable': self.n_uncoverable,
            },
        }
        return d


class ConMinRunner(BaseRunner):
    """
    Run ConMin and collect performance metrics.

    Builds model once from file paths, reuses via prepare() per fold.

    Metrics collected:
    - runtime_ms: Execution time
    - consistency_checks: Number of SAT solver calls
    - memory_peak_mb: Peak memory usage
    - n_mss: MSS (admissible pool A) size
    - n_kb: Final KB size (Cflat ∪ S ∪ fallbacks, post-Reduce)
    - cover diagnostics: n_components / largest_component / n_greedy_fallback / |U|
    """

    def __init__(
            self,
            bias_path: str,
            fm_path: str,
            solver_name: str = 'glucose4',
            use_incremental: bool = True,
            k: int = 1,
    ):
        """Initialize runner with file paths. Builds model once (without examples).

        Args:
            bias_path: Path to bias JSON file
            fm_path: Path to feature model (.uvl) file
            solver_name: SAT solver name
            use_incremental: Use incremental solver mode
            k: support⁺ threshold for the S set (paper Algorithm 1 line 6)
        """
        super().__init__(bias_path, fm_path, solver_name, use_incremental=use_incremental)
        self.k = k

        # Build model (pure bias KB; solver mode is the runner's, examples per run).
        self.model = (ConMinModelBuilder
                      .from_bias(bias_path)
                      .with_oracle_data(self.oracle.oracle_data)
                      .build())

    @property
    def feature_ids(self) -> Dict[str, int]:
        """Feature name -> SAT variable ID mapping (a plain dict — see ADR-0007)."""
        return self.model.name_to_id

    def run(
            self,
            positive_examples: Optional[List[Dict[str, bool]]] = None,
            negative_examples: Optional[List[Dict[str, bool]]] = None,
            shuffle_seed: Optional[int] = None,
    ) -> ConMinRunResult:
        """Run ConMin with given examples and collect metrics.

        Args:
            positive_examples: List of E+ (each is {feature: True/False})
            negative_examples: List of E- (each is {feature: True/False})
            shuffle_seed: If provided, shuffle the bias iteration order (set_c) with
                this seed — mirrors ConGenRunner. ConMin's admissible pool A is
                order-invariant, but the FINAL KB is NOT (AcqMinCover + Reduce iterate
                A in bias order, so which named constraints survive shifts). Honoured
                so ConMin runs the SAME protocol as ConGen under shuffle_bias.

        Returns:
            ConMinRunResult with the decomposition + performance metrics.
        """
        positive_examples = positive_examples or []
        negative_examples = negative_examples or []
        logging.debug('>>> ConMinRunner.run(E+=%d, E-=%d)',
                      len(positive_examples), len(negative_examples))

        with profiler_session(ProfilerPreset.BENCHMARK) as profiler:
            tracemalloc.start()
            with profiler.timer("conmin_total_time"):
                checker = None
                try:
                    # Prepare this fold's task (pure — runs GenerateNE, computes
                    # support⁺, drops the root to root_axiom). The model keeps no task.
                    prepared = self.model.prepare_task(
                        ConMinTaskInput.from_examples(
                            self.oracle.oracle_data,
                            positive_examples,
                            negative_examples,
                        )
                    )
                    task = prepared.task
                    describe = prepared.describe

                    # Foot-gun #5: with E⁻ present but no per-e⁻ encodings, ConMin's
                    # lines 5-8 reduce to an empty KB (A only). That is a silent-empty
                    # KB, not a valid result — fail loud here (runner-side twin of the
                    # resolve_result guard) rather than emit a degenerate KB.
                    if negative_examples and not task.neg_encodings:
                        raise ValueError(
                            f"ConMin got {len(negative_examples)} negative example(s) "
                            f"but the prepared task has no neg_encodings — the cover "
                            f"step would silently yield an empty KB. Task preparation "
                            f"must capture per-e⁻ encodings when E⁻ is non-empty.")

                    # Shuffle the bias iteration order if a seed is given (mirrors
                    # ConGenRunner). The task is frozen: shuffle a copy and rebind. The
                    # final KB is order-dependent, so this must match ConGen's protocol.
                    if shuffle_seed is not None:
                        shuffled_set_c = list(task.set_c)
                        random.Random(shuffle_seed).shuffle(shuffled_set_c)
                        task = replace(task, set_c=shuffled_set_c)
                        logging.debug('Shuffled set_c with seed=%d', shuffle_seed)

                    checker = build_checker(
                        task,
                        SolverBackend.from_flags(use_incremental=self.use_incremental),
                        self.solver_name, profiler
                    )

                    # Run ConMin (paper Algorithm 1, lines 1-8). Wire the full
                    # lines-5-8 inputs — omitting neg_encodings/support_count would
                    # collapse the KB to A only.
                    conmin = ConMin(checker, profiler)
                    result = conmin.acquire(
                        set_b=task.set_c,
                        set_bg=task.set_b,
                        set_tc=task.set_tc,
                        set_neg_tv=task.set_neg_tv,
                        negation_map=task.negation_map,
                        neg_encodings=task.neg_encodings,
                        support_count=task.support_count,
                        k=self.k,
                    )

                    # Surface the consistency-gate trip (E+ ⊥ NE∪BG → empty A/KB) so a
                    # degenerate fold is not silently mistaken for a legitimate tiny KB.
                    if result.metadata.get('error'):
                        logging.warning(
                            'ConMin gate tripped (%s) → empty KB (E+=%d, E-=%d)',
                            result.metadata['error'],
                            len(positive_examples), len(negative_examples))

                finally:
                    current, peak = tracemalloc.get_traced_memory()
                    tracemalloc.stop()
                    if checker is not None:
                        checker.cleanup()

            memory_peak_mb = peak / (1024 * 1024)
            run_metrics = collect(profiler, CONMIN_METRICS, extra={
                'memory_peak_mb': memory_peak_mb,
                'n_mss': result.n_mss,
                'n_kb': result.n_kb,
                'n_components': result.n_components,
                'largest_component': result.largest_component,
                'n_greedy_fallback': result.n_greedy_fallback,
                'n_uncoverable': len(result.uncoverable),
            })
            runtime_ms = run_metrics.values['runtime_ms']
            consistency_checks = run_metrics.values['consistency_checks']
            profiler_snapshot = profiler.to_dict()

            # Resolve assumption IDs -> the 5-part decomposition (stateless): describe
            # + the task's set_kb / negation_map (for the ¬e⁻ fallbacks) + the root
            # clauses from the frozen OracleData snapshot.
            bg_clauses, kb_clauses, kb_names, fallback_clauses, redundant_names = \
                self.model.resolve_result(
                    result, describe,
                    self.oracle.oracle_data.get_root_clauses(),
                    task.set_kb, task.negation_map)

            run_result = ConMinRunResult(
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
                profiler_data=profiler_snapshot,
                fallback_clauses=fallback_clauses,
                mss_ids=list(result.mss_ids),
                cover_ids=list(result.cover_ids),
                kb_assumption_ids=list(result.kb_assumption_ids),
                n_components=result.n_components,
                largest_component=result.largest_component,
                n_greedy_fallback=result.n_greedy_fallback,
                n_uncoverable=len(result.uncoverable),
            )

            logging.debug('<<< ConMinRunner: KB=%d, mss=%d, runtime=%.2fms, checks=%d',
                          result.n_kb, result.n_mss, runtime_ms, consistency_checks)

        return run_result
