# Brainstorm: Add profiler_data to ConGenRunResult

## Problem Statement

ConGen's profiler collects rich metrics during execution (solver_time, redundancy_checks, gauges, etc.) but only 3 are extracted into results (`runtime_ms`, `consistency_checks`, `memory_peak_mb`). All other profiler data is discarded when `profiler_session` exits. Need to capture full profiler snapshot in results and propagate to JSON output.

## Evaluated Approaches

### A: Add profiler_data dict to ConGenResult (algorithm layer)
- **Pro:** Self-contained algorithm result, reduces runner coupling
- **Con:** ConGenResult snapshots before runner's `congen_total_time` timer stops → misses that metric. Mixes algorithm concerns with profiling
- **Rejected:** Timing mismatch issue, violates separation of concerns

### B: Add typed performance fields to ConGenResult
- **Pro:** Strongly typed, IDE-friendly
- **Con:** Must modify dataclass every time a new metric is added. Same timing mismatch as A
- **Rejected:** Maintenance burden, timing issue

### C: Enhance ConGenRunResult with profiler_data dict (**CHOSEN**)
- **Pro:** Clean separation (ConGenResult stays algorithm-only). Runner owns the profiler lifecycle, so it captures complete data. Flat dict from `profiler.to_dict()` — no custom serialization needed. Adding new profiler metrics requires zero code changes in result classes
- **Con:** ConGenResult remains "profiler-blind" (acceptable — by design)

## Final Solution

### Design Decisions
1. **ConGenResult unchanged** — stays algorithm-only
2. **ConGenRunResult gets `profiler_data: Dict[str, Any]`** — runner calls `profiler.to_dict()` after timer stops
3. **Flat dict format** — `profiler.to_dict(include_stats=True)` returns timers as stats (count/mean/min/max)
4. **Propagate to CrossValidationFoldResult** — each fold's JSON output includes full profiler snapshot
5. **Nested under `performance.profiler`** in JSON output

### Files to Modify

| File | Change |
|------|--------|
| `conacq/runners/congen_runner.py` | Add `profiler_data` field to `ConGenRunResult`. Update `to_dict()` to include `profiler` under `performance`. Update `run()` to capture `profiler.to_dict()` |
| `conacq/eval/cross_validation.py` | Add `profiler_data` to `CrossValidationFoldResult`. Update `to_dict()`. Pass `profiler_data` from `run_result` in `_run_fold()` |
| `conacq/eval/performance_metrics.py` | (Optional) Add `profiler_data` to `PerformanceMetrics` if aggregation desired. Or keep separate |

### Data Flow

```
profiler_session(BENCHMARK) as profiler
  → ConGen.acquire() records metrics via profiler
  → Runner: profiler.to_dict() → ConGenRunResult.profiler_data
  → CV: fold_result.profiler_data = run_result.profiler_data
  → report.py → _save_json() → JSON file with profiler snapshot per fold
```

### JSON Output Format

```json
{
  "fold_index": 0,
  "accuracy": 0.95,
  "performance": {
    "runtime_ms": 130.5,
    "consistency_checks": 5,
    "memory_peak_mb": 12.3,
    "profiler": {
      "paper_consistency_checks": 5,
      "redundancy_consistency_checks": 2,
      "solver_time": { "count": 7, "mean": 0.012, "min": 0.001, "max": 0.05 },
      "solver_time_accum": 0.084,
      "congen_runtime": 125.3,
      "congen_total_time": 130.5,
      "_profiler_total_time": 130.8
    }
  }
}
```

## Implementation Considerations

- `profiler.to_dict()` must be called **after** `profiler.timer("congen_total_time")` context exits but **before** `profiler_session` exits — current runner code structure already supports this (lines 191-193 are after the timer block)
- Existing typed fields (`runtime_ms`, `consistency_checks`, `memory_peak_mb`) kept for backward compatibility — `profiler_data` is additive
- `PerformanceMetrics.to_dict()` and `AggregatedPerformanceMetrics` do NOT need changes — they aggregate only the 3 core metrics. `profiler_data` is pass-through (stored, serialized, not aggregated)

## Risk Assessment

- **Low risk:** Additive change only, no existing fields modified
- **JSON size increase:** ~200-500 bytes per fold (negligible)
- **NullProfiler compatibility:** `NullProfiler.to_dict()` returns `{}` — safe default

## Success Criteria

- [ ] `ConGenRunResult.profiler_data` populated with full profiler snapshot
- [ ] JSON output includes `performance.profiler` per fold
- [ ] Existing tests pass without modification
- [ ] NullProfiler (disabled) produces empty profiler_data
