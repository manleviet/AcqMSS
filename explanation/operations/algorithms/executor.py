"""Parallel & memoizing ConsistencyExecutor implementations (the L2/L3 side).

One-way dependency: this module imports from ``checker.py`` (the serial side);
``checker.py`` never imports this module — so there is no cycle, and the
canonical ``explanation`` repo can mirror the same ``{checker, executor}`` split.

Pieces:
- ``ProcessExecutor`` — a shared process pool, the single place SAT solves run in
  parallel (L3). Each worker builds its OWN checker ONCE from the KB (the KB is
  sent once via the pool initializer); per call only assumptions (picklable
  ints) are shipped and a ``bool`` / ``(bool, model)`` comes back.
- ``ConsistencyCache`` — thread-safe map of assumptions-hash → RESOLVED ``bool``
  (never futures). One cache per executor instance, so it is KB-namespaced by
  construction (no cross-KB collisions). Thread-safe so L1 node-threads can be
  bolted on later without changing it.
- ``MemoizingExecutor`` — decorator that adds the cache over ANY executor. A
  cache HIT is NOT a consistency check (no counter increment); only a MISS
  delegates to the inner executor, which counts the real solve at the boundary.

Profiler (option B): ``ProcessExecutor`` increments the call counters in the MAIN
process at the call/submit boundary, so counts are never lost to worker processes.
A serial ``ConsistencyChecker`` and a ``ProcessExecutor`` therefore report identical
counts for identical work.

``solver_time`` (return-and-aggregate): each worker's checker holds a real, started
``Profiler``, so the serial per-call ``record_time("solver_time", solver.time())`` (the
SAME PySAT clock as the serial path) fires inside the worker. The worker harvests that
just-recorded value and returns it with the result; ``ProcessExecutor`` records it on the
MAIN profiler next to the ``increment(...)``. Caveat: the summed parallel ``solver_time``
is cumulative CPU-effort and is ``>`` wall-clock — wall-clock comes from ``@measure_time``
at the main process; do not conflate the two. (Each worker keeps one growing
``solver_time`` list for its lifetime; bounded because a ``ProcessExecutor`` is short-lived
— one per diagnosis.)
"""
import multiprocessing as mp
import threading
from concurrent.futures import Future
from typing import Dict, List, Optional, Tuple

from .checker import (
    ConsistencyChecker,
    IncrementalPySATChecker,
    NonIncrementalPySATChecker,
)
from .profiler import (
    get_global_profiler, AbstractProfiler, create_profiler, ProfilerPreset,
)
from .utils import get_hashcode


# --- ProcessExecutor worker state (one persistent checker per worker process) ---
_worker_checker: Optional[ConsistencyChecker] = None


def _init_worker(set_kb: List[List[int]], assumptions: List[int],
                 solver_name: str, use_incremental: bool) -> None:
    """Pool initializer: build the worker's checker ONCE from the KB.

    Runs in each worker process. The checker holds a real, STARTED ``Profiler`` so
    its serial ``record_time("solver_time", solver.time())`` fires in the worker
    (same PySAT clock as the serial path); the worker harvests that value and
    returns it, and the main process counts calls at the boundary (option B).
    """
    global _worker_checker
    checker_cls = IncrementalPySATChecker if use_incremental else NonIncrementalPySATChecker
    profiler = create_profiler(ProfilerPreset.BENCHMARK)
    profiler.start()
    _worker_checker = checker_cls(set_kb, assumptions, solver_name, profiler)


def _worker_solver_time() -> float:
    """Last ``solver_time`` recorded by this worker's checker (this call's value).

    Calls are sequential within a worker process, so the final list entry is the
    duration of the solve that just completed.
    """
    return _worker_checker.profiler.get_metric("solver_time", [0.0])[-1]


def _worker_is_consistent(set_c: List[int]) -> Tuple[bool, float]:
    result = _worker_checker.is_consistent(set_c)
    return result, _worker_solver_time()


def _worker_solve(set_c: List[int]) -> Tuple[bool, Optional[List[int]], float]:
    sat = _worker_checker.is_consistent(set_c)
    model = _worker_checker.get_model() if sat else None
    return sat, model, _worker_solver_time()


class ConsistencyCache:
    """Thread-safe cache of resolved CC results, keyed by assumptions-hash.

    Stores resolved bools only. One instance per executor ⇒ inherently scoped to
    that executor's KB (no cross-KB namespacing needed).
    """

    def __init__(self) -> None:
        self._results: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def lookup(self, key: str) -> Tuple[bool, Optional[bool]]:
        """Return (hit, value). value is None only when hit is False."""
        with self._lock:
            if key in self._results:
                return True, self._results[key]
            return False, None

    def store(self, key: str, value: bool) -> None:
        with self._lock:
            self._results[key] = value

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._results

    def __len__(self) -> int:
        with self._lock:
            return len(self._results)


class ProcessExecutor:
    """Parallel ConsistencyExecutor backed by a shared process pool (L3).

    The ONLY place parallel SAT solves run. No nested pools: this is the single
    worker budget for the whole diagnosis. Counts CC calls in the MAIN process
    at the boundary (option B) so they survive regardless of where the solve ran.
    """

    def __init__(self, set_kb: List[List[int]], assumptions: List[int],
                 solver_name: str = 'glucose3', use_incremental: bool = True,
                 n_workers: Optional[int] = None,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        workers = n_workers if n_workers is not None else max(1, mp.cpu_count() - 1)
        self._pool = mp.Pool(
            processes=workers,
            initializer=_init_worker,
            initargs=(set_kb, assumptions, solver_name, use_incremental),
        )

    def is_consistent(self, set_c: List[int]) -> bool:
        self.profiler.increment("is_consistent_calls")
        result, dt = self._pool.apply(_worker_is_consistent, (set_c,))
        self.profiler.record_time("solver_time", dt)
        return result

    def is_consistent_test_cases(self, set_c: List[int], set_tc: List[int],
                                 stop_at_first_violation: bool) -> List[int]:
        self.profiler.increment("is_consistent_test_cases_calls")
        set_tcp: List[int] = []
        for tc in set_tc:
            self.profiler.increment("is_consistent_calls")
            result, dt = self._pool.apply(_worker_is_consistent, (set_c + [tc],))
            self.profiler.record_time("solver_time", dt)
            if not result:
                set_tcp.append(tc)
            if stop_at_first_violation and set_tcp:
                break
        return set_tcp

    def solve(self, set_c: List[int]) -> Tuple[bool, Optional[List[int]]]:
        self.profiler.increment("is_consistent_calls")
        sat, model, dt = self._pool.apply(_worker_solve, (set_c,))
        self.profiler.record_time("solver_time", dt)
        return sat, model

    def submit(self, set_c: List[int]) -> Future:
        """Dispatch an async CC; returns a concurrent.futures.Future[bool]."""
        self.profiler.increment("is_consistent_calls")
        future: Future = Future()

        def _on_done(res: Tuple[bool, float]) -> None:
            # Runs on the pool's result-handler thread in the MAIN process, so it
            # reaches the main profiler (record_time is lock-guarded → thread-safe).
            sat, dt = res
            self.profiler.record_time("solver_time", dt)
            future.set_result(sat)

        self._pool.apply_async(
            _worker_is_consistent, (set_c,),
            callback=_on_done,
            error_callback=future.set_exception,
        )
        return future

    def cleanup(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool.terminate()
            self._pool = None

    def __enter__(self) -> "ProcessExecutor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


class MemoizingExecutor:
    """Decorator adding a result cache over any ConsistencyExecutor.

    Dedups CC across all submitters (e.g. FastDiagP speculative lookahead). A
    cache HIT returns the stored bool WITHOUT a solve and WITHOUT incrementing
    any counter (a HIT is not a consistency check). A MISS delegates to the inner
    executor, which counts the real solve at its boundary — so wrapping does not
    change counts versus the bare inner executor.
    """

    def __init__(self, inner, profiler_instance: AbstractProfiler = None) -> None:
        self.inner = inner
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        self.cache = ConsistencyCache()
        # In-flight CCs (key -> Future), so a speculative submit and the later
        # blocking check share ONE solve. Without this, a parallel run would
        # re-solve (and re-count) a check whose speculation had not yet landed,
        # breaking count parity with the serial executor.
        self._pending: Dict[str, Future] = {}
        self._pending_lock = threading.Lock()

    def is_consistent(self, set_c: List[int]) -> bool:
        key = get_hashcode(set_c)
        hit, value = self.cache.lookup(key)
        if hit:
            return value  # cache HIT — not a consistency check, not counted
        # Claim the key under the lock so concurrent callers (and speculative
        # submits) coalesce onto one solve — thread-safe for future L1 node
        # threads, and keeps counts deduped.
        with self._pending_lock:
            pending = self._pending.get(key)
            owner = pending is None
            if owner:
                pending = Future()
                self._pending[key] = pending
        if not owner:
            # Another caller/submit is already solving this exact CC: wait for it
            # rather than launching (and counting) a duplicate solve.
            return pending.result()
        try:
            result = self.inner.is_consistent(set_c)
            self.cache.store(key, result)
            pending.set_result(result)
            return result
        except Exception as exc:
            pending.set_exception(exc)
            raise
        finally:
            with self._pending_lock:
                self._pending.pop(key, None)

    def is_consistent_test_cases(self, set_c: List[int], set_tc: List[int],
                                 stop_at_first_violation: bool) -> List[int]:
        # Loops through the memoized is_consistent so repeated checks are deduped.
        set_tcp: List[int] = []
        for tc in set_tc:
            if not self.is_consistent(set_c + [tc]):
                set_tcp.append(tc)
            if stop_at_first_violation and set_tcp:
                break
        return set_tcp

    def solve(self, set_c: List[int]) -> Tuple[bool, Optional[List[int]]]:
        # Model results are not cached (cache holds bools only); delegate.
        return self.inner.solve(set_c)

    def submit(self, set_c: List[int]) -> Future:
        key = get_hashcode(set_c)
        hit, value = self.cache.lookup(key)
        if hit:
            future: Future = Future()
            future.set_result(value)
            return future
        with self._pending_lock:
            pending = self._pending.get(key)
            if pending is not None:
                return pending  # dedup: same CC already in flight
            future = self.inner.submit(set_c)
            self._pending[key] = future
        future.add_done_callback(lambda f: self._store_from_future(key, f))
        return future

    def _store_from_future(self, key: str, future: Future) -> None:
        try:
            self.cache.store(key, future.result())
        except Exception:
            # A failed speculative check simply isn't cached; the synchronous
            # path will surface the real error when the value is actually needed.
            pass
        finally:
            with self._pending_lock:
                self._pending.pop(key, None)
