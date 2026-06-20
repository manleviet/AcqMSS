"""ConsistencyExecutor coverage matrix (Phase R, R8).

Proves the executor abstraction's core guarantee: the serial executor
(ConsistencyChecker) and the parallel executor (ProcessExecutor) produce
IDENTICAL results — only timing differs. Also covers the MemoizingExecutor
dedup semantics (a cache HIT is not a re-computation / not a consistency check)
and that one immutable KB yields independent per-task executes.
"""
import os
import logging
import unittest
from concurrent.futures import Future

from explanation.models import DiagnosisModelBuilder, TaskInput
from explanation.operations.algorithms.checker import CheckerFactory
from explanation.operations.algorithms.executor import (
    ProcessExecutor, MemoizingExecutor, ConsistencyCache,
)
from explanation.operations.algorithms.fastdiag import FastDiag
from explanation.operations.algorithms.fastdiagp import FastDiagP

RESOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
FM_INCONSISTENT = os.path.join(RESOURCES_DIR, "smartwatch_inconsistent.fide")

logging.disable(logging.CRITICAL)


def _inconsistent_task():
    """A KB + task whose FM diagnosis is non-empty (exercises FastDiagP lookahead)."""
    model = DiagnosisModelBuilder.from_fide(FM_INCONSISTENT).build()
    return model, model.prepare_task(TaskInput())


class _CountingExecutor:
    """Minimal ConsistencyExecutor that records how many real checks it runs."""

    def __init__(self):
        self.calls = 0

    def is_consistent(self, set_c):
        self.calls += 1
        return (sum(set_c) % 2) == 0

    def is_consistent_test_cases(self, set_c, set_tc, stop_at_first_violation):
        return [tc for tc in set_tc if not self.is_consistent(set_c + [tc])]

    def solve(self, set_c):
        self.calls += 1
        return True, [1]

    def submit(self, set_c):
        future: Future = Future()
        future.set_result(self.is_consistent(set_c))
        return future


class TestProcessExecutorParity(unittest.TestCase):
    """ProcessExecutor must answer identically to a serial ConsistencyChecker."""

    def test_is_consistent_and_solve_match_serial(self):
        _, task = _inconsistent_task()
        checker = CheckerFactory.create_from_task(task)
        executor = ProcessExecutor(task.set_kb, task.assumptions,
                                   use_incremental=True, n_workers=2)
        try:
            # A consistent probe (background only) and an inconsistent one (all C).
            for probe in (list(task.set_b),
                          list(task.set_b) + list(task.set_c)):
                self.assertEqual(checker.is_consistent(probe),
                                 executor.is_consistent(probe))
                s_sat, s_model = checker.solve(probe)
                p_sat, p_model = executor.solve(probe)
                self.assertEqual(s_sat, p_sat)
                self.assertEqual(s_model, p_model)
        finally:
            executor.cleanup()

    def test_fastdiagp_serial_vs_process_identical(self):
        _, task = _inconsistent_task()

        # Baseline: serial FastDiag.
        baseline = FastDiag(CheckerFactory.create_from_task(task)).find_diagnosis(
            list(task.set_c), list(task.set_b))

        # FastDiagP with the serial checker-as-executor.
        diag_serial = FastDiagP(CheckerFactory.create_from_task(task)).find_diagnosis(
            list(task.set_c), list(task.set_b))

        # FastDiagP with the parallel ProcessExecutor.
        executor = ProcessExecutor(task.set_kb, task.assumptions,
                                   use_incremental=True, n_workers=2)
        try:
            diag_parallel = FastDiagP(executor).find_diagnosis(
                list(task.set_c), list(task.set_b))
        finally:
            executor.cleanup()

        self.assertTrue(baseline, "expected a non-empty diagnosis (inconsistent FM)")
        self.assertEqual(baseline, diag_serial)
        self.assertEqual(baseline, diag_parallel)

    def test_consistency_check_count_parity(self):
        """Serial and parallel executors count is_consistent_calls identically.

        Guards the option-B boundary counting + in-flight dedup: a speculative
        submit and its later blocking check share ONE solve, so parallel does not
        double-count relative to serial.
        """
        from explanation.operations.algorithms.profiler import (
            create_profiler, ProfilerPreset,
        )
        _, task = _inconsistent_task()

        ps = create_profiler(ProfilerPreset.BENCHMARK); ps.start()
        checker = CheckerFactory.create_from_task(task, profiler_instance=ps)
        FastDiagP(MemoizingExecutor(checker, ps)).find_diagnosis(
            list(task.set_c), list(task.set_b))
        n_serial = ps.get_metric('is_consistent_calls', 0)

        pp = create_profiler(ProfilerPreset.BENCHMARK); pp.start()
        executor = ProcessExecutor(task.set_kb, task.assumptions,
                                   n_workers=2, profiler_instance=pp)
        try:
            FastDiagP(MemoizingExecutor(executor, pp)).find_diagnosis(
                list(task.set_c), list(task.set_b))
        finally:
            executor.cleanup()
        n_parallel = pp.get_metric('is_consistent_calls', 0)

        self.assertGreater(n_serial, 0)
        self.assertEqual(n_serial, n_parallel)


class TestMemoizingExecutor(unittest.TestCase):
    """A cache HIT is not a re-computation (and thus not a consistency check)."""

    def test_hit_does_not_recompute(self):
        inner = _CountingExecutor()
        memo = MemoizingExecutor(inner)

        first = memo.is_consistent([2, 4])     # MISS -> one real check
        second = memo.is_consistent([2, 4])    # HIT  -> no recompute
        self.assertEqual(first, second)
        self.assertEqual(inner.calls, 1)

        memo.is_consistent([1, 3])             # different key -> one more check
        self.assertEqual(inner.calls, 2)

    def test_submit_uses_cache(self):
        inner = _CountingExecutor()
        memo = MemoizingExecutor(inner)
        memo.is_consistent([2, 4])             # warms the cache (1 check)
        fut = memo.submit([2, 4])              # HIT -> resolved future, no dispatch
        self.assertTrue(fut.done())
        self.assertEqual(fut.result(), True)
        self.assertEqual(inner.calls, 1)

    def test_cache_namespaced_per_instance(self):
        # Two caches are independent (KB-namespaced by construction).
        a, b = ConsistencyCache(), ConsistencyCache()
        a.store("k", True)
        self.assertIn("k", a)
        self.assertNotIn("k", b)


class TestMultiTaskOneKB(unittest.TestCase):
    """One immutable KB yields independent tasks that execute independently."""

    def test_two_tasks_one_kb_independent_executes(self):
        model, _ = _inconsistent_task()
        task_a = model.prepare_task(TaskInput())
        task_b = model.prepare_task(TaskInput())
        self.assertIsNot(task_a, task_b)
        self.assertIsNot(task_a.set_c, task_b.set_c)

        diag_a = FastDiagP(CheckerFactory.create_from_task(task_a)).find_diagnosis(
            list(task_a.set_c), list(task_a.set_b))
        diag_b = FastDiagP(CheckerFactory.create_from_task(task_b)).find_diagnosis(
            list(task_b.set_c), list(task_b.set_b))
        self.assertEqual(diag_a, diag_b)
        self.assertTrue(diag_a)


if __name__ == "__main__":
    unittest.main()
