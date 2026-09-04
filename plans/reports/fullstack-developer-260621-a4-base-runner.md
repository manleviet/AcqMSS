# A4 BaseRunner Profiling + Metrics — Implementation Report

**Date:** 2026-06-21  
**Phase:** 05 — A4 base runner profiling + metric-extraction  
**Branch:** feat/redesign-abc  

---

## Status

**DONE**

All 420 tests pass (376 pre-existing + 44 new safety-net tests). No metric drift detected.

---

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| `conacq/runners/base_runner.py` | Added `_run_with_profiling()` + metric-map wiring | +101 (105→205) |
| `conacq/runners/congen_runner.py` | Re-pointed to base; removed boilerplate; declarative metric map | −57 net (279→222) |
| `conacq/runners/quacq_runner.py` | Re-pointed to base; removed boilerplate; declarative metric map | −6 net (413→407) |
| `conacq/eval/__init__.py` | No net change (reverted lazy-getattr; circular fixed at source) | 0 |
| **Created** `tests/test_runners_characterization.py` | Safety-net: 44 tests for ConGenRunner + QuAcqRunner | 283 |

---

## Tasks Completed

- [x] Safety-net tests written and green against pre-refactor code (44 tests)
- [x] Circular import fixed at source (`PerformanceMetrics` now local-import in `get_performance_metrics()` in both runners)
- [x] `BaseRunner._run_with_profiling()` extracted with declarative metric map
- [x] `shuffle(task.set_c)` deduplicated — single definition in `base_runner.py:169`
- [x] `tracemalloc` / `profiler_session` / `CheckerFactory` removed from both runners
- [x] ConGenRunner re-pointed; declares `_CONGEN_METRIC_MAP`
- [x] QuAcqRunner re-pointed; declares `_QUACQ_METRIC_MAP`
- [x] Full suite green: 420 passed, 1 pre-existing warning

---

## Architecture

### `_run_with_profiling` signature

```python
def _run_with_profiling(
    self,
    task,
    timer_key: str,
    algorithm_fn: Callable,          # (checker, profiler) -> raw_result
    metric_map: Dict[str, Callable], # {key: (profiler) -> value}
    shuffle_seed: Optional[int] = None,
) -> Dict[str, Any]:
```

Returns dict with: `raw_result`, `runtime_ms`, `memory_peak_mb`,
`consistency_checks`, `profiler_data`, plus all keys from `metric_map`.

### Metric-map shape

```python
_CONGEN_METRIC_MAP = {
    'congen_runtime_ms': lambda p: sum(p.get_metric('congen_runtime', [0])) * 1000,
    'acqmss_calls':      lambda p: p.get_metric('acqmss_calls', 0),
    # ...
}
```

- Keys are **opaque to the base** — no `PerformanceMetrics` field names baked in.
- C2 can swap the metric sink (e.g. to `RunMetrics`) without reworking these maps.

---

## Safety-Net Assertion Policy

| Metric class | Assertion |
|---|---|
| `n_bias`, `n_kb`, `n_mss`, `consistency_checks`, `acqmss_calls`, `is_consistent_test_cases_calls`, `redundancy_consistency_checks` | **Pinned exact** (deterministic) |
| `is_consistent_calls` | **Presence + lower-bound** (varies with incremental solver cache state between runs — not a paper metric) |
| `runtime_ms`, `memory_peak_mb`, `solver_time_ms`, `*_runtime_ms` | **Presence + type** only (non-deterministic timing) |
| `kb_constraints` (sorted), `kb_clauses` count, `bg_clauses` count, `redundant_constraints` count | **Pinned exact** (deterministic given fixed seed+input) |
| `n_queries`, `convergence_reason` (QuAcq) | **Pinned exact** |
| `quacq_calls`, `findscope_calls`, `findc_calls`, `dis_gen_calls`, `reduce_calls` | **Pinned exact** |
| `profiler_data` | **Non-empty dict** |

### Reclassification note

`is_consistent_calls` was initially pinned to 1656 but varied to 1647 on a second run — the incremental SAT solver reuses clause-level state across `is_consistent()` invocations; cache hits change per-run depending on OS memory layout / formula simplification. Reclassified as presence-only. All other count metrics remained stable across both runs.

---

## Shuffle Dedup Confirmed

```
grep shuffle conacq/runners/{base_runner,congen_runner,quacq_runner}.py
→ Only base_runner.py:169 contains the shuffle call
```

Before: two identical `random.Random(shuffle_seed).shuffle(task.set_c)` lines (one in each runner).  
After: one definition in `BaseRunner._run_with_profiling()`.

---

## Circular Import Fix

**Root cause:** `congen_runner.py` had a module-level import  
`from conacq.eval.performance_metrics import PerformanceMetrics`  
which triggered `conacq/eval/__init__.py`, which imported from `conacq.runners`  
(not yet fully initialized) → `ImportError`.

**Fix:** moved the import inside `get_performance_metrics()` in both runners
(method-local, called rarely, no overhead). No lazy `__getattr__` needed.

---

## Before → After (runner `run()` bodies)

**ConGenRunner.run() before:** ~95 lines (profiler context manager, tracemalloc,
checker create/cleanup, shuffle, 8 extracted metric variables, result build).

**ConGenRunner.run() after:** ~40 lines (task prep, `_algorithm` closure,
`_run_with_profiling()` call, `resolve_result`, `ConGenRunResult` constructor).

**QuAcqRunner.run() before:** ~120 lines (same boilerplate + mode dispatch).

**QuAcqRunner.run() after:** ~55 lines (mode validation, task prep, `_algorithm`
closure capturing mode+examples, `_run_with_profiling()` call, result build).

---

## Final pytest summary

```
420 passed, 1 warning in 63.31s
```

Pre-existing: 376. New (safety-net): 44. Known flaky test  
(`test_consistency_check_count_parity`) passed on this run.

---

## Unresolved Questions

None.
