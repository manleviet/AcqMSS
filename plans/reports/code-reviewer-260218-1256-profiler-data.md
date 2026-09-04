# Code Review: Add profiler_data to ConGenRunResult and CrossValidationFoldResult

**Date:** 2026-02-18
**Reviewer:** code-reviewer
**ID:** 260218-1256

---

## Scope

- **Files changed:** 7
  - `conacq/runners/congen_runner.py` — profiler_data field, profiler_session refactor, runtime timing via profiler timer
  - `conacq/eval/cross_validation.py` — profiler_data pass-through in CV fold, `use_incremental` rename in constructor call
  - `conacq/algorithms/acqmss/congen.py` — removed `resolve_congen_names()` and `save_result()` dead code
  - `conacq/algorithms/acqmss/reduce.py` — added `redundancy_consistency_checks` counter
  - `conacq/algorithms/interactive/learner.py` — removed `save_result()` dead code
  - `conacq/algorithms/__init__.py` — removed `resolve_congen_names` export
  - `conacq/algorithms/acqmss/__init__.py` — removed `resolve_congen_names` export
- **LOC changed:** ~130 (additions + deletions)
- **Focus:** profiler integration, dataclass field additions, dead code removal

---

## Overall Assessment

The profiler integration design is sound: `profiler_session` context manager replaces manual start/stop, `profiler.timer()` replaces manual `time.perf_counter()` arithmetic, and `profiler.to_dict()` captures a full snapshot. Dead code removal (`resolve_congen_names`, `save_result`) is clean with zero remaining references.

However, there is **one critical bug** in how `runtime_ms` is extracted from the profiler timer metric.

---

## Critical Issues

### 1. `runtime_ms` gets a list, not a float -- type mismatch bug

**File:** `conacq/runners/congen_runner.py`, line 194
**Code:**
```python
runtime_ms = profiler.get_metric('congen_total_time', 0)
```

**Problem:** `profiler.timer("congen_total_time")` records via `record_time()`, which stores values as a **list of durations in seconds**: `self._profile[key] = current + [duration]`. So `get_metric('congen_total_time', 0)` returns `[0.123456]` (a list), not `0.123456` (a float). Additionally, the value is in **seconds**, not milliseconds.

**Impact:** `ConGenRunResult.runtime_ms` will be assigned a `list[float]` instead of `float`. This will:
- Break JSON serialization expectations (list instead of number)
- Propagate wrong type to `PerformanceMetrics.runtime_ms`
- Cause `CrossValidationFoldResult.performance.runtime_ms` to be a list
- Break logging format string `'runtime=%.2fms'`

**Fix:**
```python
timer_values = profiler.get_metric('congen_total_time', [0])
runtime_ms = timer_values[0] * 1000 if timer_values else 0
```

Or use `get_stats`:
```python
stats = profiler.get_stats('congen_total_time')
runtime_ms = (stats['total'] * 1000) if stats else 0
```

**Severity:** CRITICAL -- runtime data corruption, likely causes downstream errors.

---

## High Priority

### 2. `profiler.to_dict()` called before `profiler.stop()` -- missing `_profiler_total_time`

**File:** `conacq/runners/congen_runner.py`, line 197
**Code:**
```python
profiler_snapshot = profiler.to_dict()
```

This executes inside `with profiler_session(...)` before the context manager calls `profiler.stop()`. The `stop()` method records `_profiler_total_time` into the profile dict. So the snapshot will **not** include total profiler session time.

**Impact:** Minor data gap -- the `profiler_data` dict in results won't contain `_profiler_total_time`. If consumers rely on this key, they'll get `KeyError` or missing data.

**Fix:** Move snapshot capture after the `with` block, or accept the omission and document it. Since the profiler is still running when `to_dict()` is called, the timer data for `congen_total_time` will be present (recorded when the inner `with profiler.timer()` exits), but the global `_profiler_total_time` won't.

**Recommendation:** Either:
- (a) Move `profiler_snapshot = profiler.to_dict()` and all post-processing outside the `with profiler_session` block (requires restructuring), or
- (b) Add a comment documenting that `_profiler_total_time` is intentionally excluded from the snapshot.

### 3. `n_fold_cross_validation` parameter naming inconsistency

**File:** `conacq/eval/cross_validation.py`, line 297
**Code:**
```python
def n_fold_cross_validation(..., is_incremental: bool = True, ...):
```

The public API still uses `is_incremental` while `ConGenRunner.__init__` was renamed to `use_incremental`. The internal mapping works correctly (`use_incremental=is_incremental` on line 333), but the inconsistency creates confusion.

**Impact:** Not a runtime bug, but a naming inconsistency in a public API that should be resolved for clarity.

**Fix:** Rename the parameter in `n_fold_cross_validation` to `use_incremental` as well, and update all callers (`apps/run_congen_eval.py` line 242).

---

## Medium Priority

### 4. `return run_result` placement inside `with profiler_session` block

**File:** `conacq/runners/congen_runner.py`, line 227
**Code:**
```python
with profiler_session(ProfilerPreset.BENCHMARK) as profiler:
    ...
    return run_result  # <-- inside with block
```

The `return` is inside the context manager block. This works (Python calls `__exit__` on return), but the entire result construction, logging, and return happen while the profiler is still running. This means:
- The profiler continues timing during result construction (KB name resolution, list building)
- The `congen_total_time` timer already stopped (inner `with` block ended), so this is not a data correctness issue
- But it's a subtle code smell -- the `profiler_session` scope is wider than necessary

**Recommendation:** Consider restructuring so the `with profiler_session` block only wraps the acquisition logic, and result construction + return happen afterward.

### 5. `tracemalloc` still used alongside profiler timer

**File:** `conacq/runners/congen_runner.py`, lines 150-189

The profiler now handles timing via `profiler.timer("congen_total_time")`, but `tracemalloc` is still managed manually. This creates an asymmetry: timing uses the profiler, memory tracking doesn't.

**Impact:** Not a bug -- `tracemalloc` provides accurate peak memory which the profiler doesn't track. But consider recording `memory_peak_mb` as a profiler gauge for consistency:
```python
profiler.set_gauge("memory_peak_mb", peak / (1024 * 1024))
```

---

## Low Priority

### 6. `_original_constraint_order` renamed to `_original_bias_constraint_order`

The rename is consistent (only used in `__init__` and `run` of `ConGenRunner`). Old name only appears in historical report files, not in code. Clean rename.

### 7. `redundancy_consistency_checks` counter addition in Reduce

**File:** `conacq/algorithms/acqmss/reduce.py`, line 83
A new `redundancy_consistency_checks` counter is added alongside the existing `paper_consistency_checks` increment. This is a clean addition -- both counters track the same event but allow separate analysis of redundancy-phase checks vs total checks.

### 8. Dead code removal is complete

- `resolve_congen_names()` removed from `congen.py`, `__init__.py`, `acqmss/__init__.py` -- zero remaining references
- `ConGen.save_result()` removed from `congen.py` -- zero remaining references
- `InteractiveLearner.save_result()` removed from `learner.py` -- zero remaining references
- Unused imports `json`, `Path` cleaned from `congen.py`

---

## Edge Cases Found

1. **Timer metric as list:** The `profiler.timer()` API stores values as lists, not scalars. Any code using `get_metric()` on a timer key must handle the list type. This is the root cause of Critical Issue #1.

2. **InteractiveRunResult has no `profiler_data`:** The `getattr(run_result, 'profiler_data', {})` fallback in `_run_cv_loop` correctly handles this. When `InteractiveRunner` adds profiler support later, the `getattr` can be replaced with direct access.

3. **Empty profiler_data for interactive folds:** CV results will have `profiler_data: {}` for interactive folds. JSON consumers must handle empty dicts.

4. **`profiler.to_dict()` with `include_stats=True` (default):** Timer metrics in the snapshot will be stats dicts (`{count, total, mean, min, max}`), not raw lists. The `congen_total_time` entry in `profiler_data` will be a stats dict with seconds, while `runtime_ms` is supposed to be a float in milliseconds. Consumers must be aware of the different representations.

---

## Positive Observations

- `profiler_session` context manager is cleaner than manual start/stop lifecycle
- `profiler.timer()` for timing is more robust than manual `time.perf_counter()` arithmetic
- `getattr` fallback for duck-typed `InteractiveRunner` is the right pattern for shared CV loop
- Dead code removal is thorough with zero orphaned references
- `field(default_factory=dict)` correctly placed after non-default fields in both dataclasses
- The `profiler_data` field is optional (defaults to empty dict), maintaining backward compatibility

---

## Recommended Actions

1. **[CRITICAL]** Fix `runtime_ms` extraction from profiler timer (Issue #1). Extract first element and convert seconds to milliseconds.
2. **[HIGH]** Decide on `profiler.to_dict()` timing vs `profiler.stop()` (Issue #2). Either restructure or document.
3. **[HIGH]** Unify `is_incremental`/`use_incremental` naming across public APIs (Issue #3).
4. **[MEDIUM]** Consider recording memory as a profiler gauge for consistency (Issue #5).

---

## Metrics

- Type Coverage: Good -- `Dict[str, Any]` for profiler_data is appropriate (schema varies by profiler config)
- Test Coverage: Not assessed (no test changes in diff)
- Linting Issues: 0 (clean imports, no unused symbols)

---

## Unresolved Questions

1. Should `runtime_ms` come from the profiler timer or remain as manual `perf_counter` arithmetic? The profiler timer stores seconds as a list -- using it for `runtime_ms` requires extraction + conversion. The old approach was simpler and more direct.
2. Should `profiler_data` be included in `to_kb_dict()` output of `CrossValidationFoldResult`? Currently it's only in `to_dict()`.
3. Should `InteractiveRunResult` also get a `profiler_data` field for symmetry, even if it's always empty for now?
