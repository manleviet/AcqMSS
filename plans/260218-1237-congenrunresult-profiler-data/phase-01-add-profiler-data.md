# Phase 1: Add profiler_data Field and Propagation

## Context Links

- Parent plan: [plan.md](plan.md)
- Brainstorm: [brainstorm report](../reports/brainstorm-260218-1237-congenrunresult-profiler-data.md)
- Profiler API: `explanation/operations/algorithms/profiler.py` — `Profiler.to_dict(include_stats=True)`

## Overview

- **Priority:** P3
- **Status:** complete
- **Description:** Add `profiler_data: Dict[str, Any]` to `ConGenRunResult`, capture full profiler snapshot in runner, propagate through `CrossValidationFoldResult` to JSON output.

## Key Insights

- `profiler.to_dict()` called at line 191 area (after timer block, before profiler_session exits) — timing is correct
- `NullProfiler.to_dict()` returns `{}` — safe default, no special handling needed
- `_run_cv_loop()` uses duck-typed runner via `getattr()` pattern — profiler_data follows same pattern
- `PerformanceMetrics` and `AggregatedPerformanceMetrics` unchanged — profiler_data is pass-through only

## Requirements

### Functional
- `ConGenRunResult.profiler_data` populated with `profiler.to_dict()` snapshot
- `ConGenRunResult.to_dict()` includes `profiler_data` under `performance.profiler`
- `CrossValidationFoldResult.profiler_data` receives data from run_result
- `CrossValidationFoldResult.to_dict()` includes `profiler_data` under `performance.profiler`

### Non-Functional
- Zero changes to ConGenResult (algorithm layer)
- Backward compatible — existing typed fields unchanged
- Existing tests pass without modification

## Related Code Files

### Modify
| File | Lines | Change |
|------|-------|--------|
| `conacq/runners/congen_runner.py` | 26-77 | Add `profiler_data` field to `ConGenRunResult`, update `to_dict()`, update `get_performance_metrics()` docstring |
| `conacq/runners/congen_runner.py` | 191-218 | Capture `profiler.to_dict()` and pass to `ConGenRunResult` constructor |
| `conacq/eval/cross_validation.py` | 31-72 | Add `profiler_data` field to `CrossValidationFoldResult`, update `to_dict()` |
| `conacq/eval/cross_validation.py` | 217-231 | Pass `profiler_data` from `run_result` to `CrossValidationFoldResult` |

### No Changes
| File | Reason |
|------|--------|
| `conacq/algorithms/acqmss/congen.py` | ConGenResult stays algorithm-only |
| `conacq/eval/performance_metrics.py` | profiler_data is pass-through, not aggregated |

## Implementation Steps

### Step 1: Update ConGenRunResult (congen_runner.py)

1.1. Add import `from typing import Any` (already has `Dict` imported)

1.2. Add field to `ConGenRunResult`:
```python
# After line 52 (memory_peak_mb)
profiler_data: Dict[str, Any] = field(default_factory=dict)
```
Note: Need to add `field` import from dataclasses (already imported: `from dataclasses import dataclass` → change to `from dataclasses import dataclass, field`)

1.3. Update `to_dict()` — add `profiler` key under `performance`:
```python
'performance': {
    'runtime_ms': self.runtime_ms,
    'consistency_checks': self.consistency_checks,
    'memory_peak_mb': self.memory_peak_mb,
    'profiler': self.profiler_data,  # NEW
}
```

1.4. Update docstring to document new field.

### Step 2: Capture profiler.to_dict() in ConGenRunner.run()

2.1. After line 193 (`consistency_checks = ...`), add:
```python
profiler_snapshot = profiler.to_dict()
```

2.2. Pass to ConGenRunResult constructor (around line 208-218):
```python
run_result = ConGenRunResult(
    ...,
    profiler_data=profiler_snapshot
)
```

### Step 3: Update CrossValidationFoldResult (cross_validation.py)

3.1. Add import: `from typing import Any` (add `Any` to existing import)

3.2. Add field to `CrossValidationFoldResult`:
```python
# After n_test_neg (line 48)
profiler_data: Dict[str, Any] = field(default_factory=dict)
```
Note: `field` already imported in this file.

3.3. Update `to_dict()` — add `profiler` key under `performance`:
```python
'performance': {
    'runtime_ms': self.performance.runtime_ms,
    'consistency_checks': self.performance.consistency_checks,
    'memory_peak_mb': self.performance.memory_peak_mb,
    'n_mss': self.performance.n_mss,
    'n_kb': self.performance.n_kb,
    'profiler': self.profiler_data,  # NEW
},
```

### Step 4: Pass profiler_data in _run_cv_loop()

4.1. In `_run_cv_loop()`, update `CrossValidationFoldResult` construction (around line 217-231):
```python
fold_results.append(CrossValidationFoldResult(
    ...,
    profiler_data=getattr(run_result, 'profiler_data', {}),
))
```
Uses `getattr` for duck-typing compat with InteractiveRunner.

## Todo List

- [x] Add `profiler_data: Dict[str, Any]` field to `ConGenRunResult`
- [x] Update `ConGenRunResult.to_dict()` with `performance.profiler`
- [x] Capture `profiler.to_dict()` in `ConGenRunner.run()`
- [x] Pass `profiler_snapshot` to `ConGenRunResult` constructor
- [x] Add `profiler_data: Dict[str, Any]` field to `CrossValidationFoldResult`
- [x] Update `CrossValidationFoldResult.to_dict()` with `performance.profiler`
- [x] Pass `profiler_data` from `run_result` in `_run_cv_loop()`
- [x] Run existing tests — all must pass (307/309 pass, 2 pre-existing failures)

## Success Criteria

- `ConGenRunResult.profiler_data` contains full profiler snapshot (counters, timers as stats, gauges)
- JSON output includes `performance.profiler` key per fold
- Existing tests pass without modification
- NullProfiler (disabled preset) produces `profiler_data = {}`

## Risk Assessment

- **Low risk:** Purely additive — no existing fields/behavior modified
- **JSON size:** ~200-500 bytes per fold increase (negligible)
- **Duck-typing:** `getattr(run_result, 'profiler_data', {})` handles InteractiveRunner gracefully

## Security Considerations

- None — profiler data contains only timing/counter metrics, no sensitive info

## Next Steps

- Run tests to verify backward compatibility
- Code review
