# Brainstorm: ConGenRunResult Metrics Expansion

## Problem Statement

ConGenRunResult currently stores only 2 performance metrics (`runtime_ms`, `consistency_checks`) despite the profiler collecting 10+ granular metrics. Need to expose 8 additional profiler metrics as first-class fields across the full pipeline: ConGenRunResult → PerformanceMetrics → AggregatedPerformanceMetrics → aggregate_metrics() → tests.

## Requirements

- Add 8 new fields to ConGenRunResult, PerformanceMetrics, AggregatedPerformanceMetrics
- All runtime metrics in milliseconds (_ms suffix)
- Timer values aggregated via sum (all recursive calls)
- Full stats (mean/std/min/max) for aggregated metrics
- Update InteractiveRunResult with defaults (0) for ConGen-specific metrics

## New Metrics

| Field | Type | Profiler Key | Notes |
|---|---|---|---|
| `congen_runtime_ms` | float | `congen_runtime` | sum * 1000, ConGen.acquire() total |
| `is_consistent_test_cases_calls` | int | `is_consistent_test_cases_calls` | counter, Checker calls |
| `is_consistent_calls` | int | `is_consistent_calls` | counter, Checker calls |
| `solver_time_ms` | float | `solver_time` | sum * 1000, SAT solver time |
| `acqmss_runtime_ms` | float | `acqmss_runtime` | sum * 1000, AcqMSS recursive calls |
| `acqmss_calls` | int | `acqmss_calls` | counter, recursive call count |
| `reduce_runtime_ms` | float | `reduce_runtime` | sum * 1000, Reduce phase |
| `redundancy_consistency_checks` | int | `redundancy_consistency_checks` | counter, Reduce-only checks |

## Approach

### Extraction Pattern (ConGenRunner.run)

Timer metrics from profiler are lists (each call appends). Counter metrics are ints.

```python
# Timers: get list, sum, convert to ms
congen_runtime_ms = sum(profiler.get_metric('congen_runtime', [0])) * 1000
acqmss_runtime_ms = sum(profiler.get_metric('acqmss_runtime', [0])) * 1000
reduce_runtime_ms = sum(profiler.get_metric('reduce_runtime', [0])) * 1000
solver_time_ms = sum(profiler.get_metric('solver_time', [0])) * 1000

# Counters: direct int
is_consistent_test_cases_calls = profiler.get_metric('is_consistent_test_cases_calls', 0)
is_consistent_calls = profiler.get_metric('is_consistent_calls', 0)
acqmss_calls = profiler.get_metric('acqmss_calls', 0)
redundancy_consistency_checks = profiler.get_metric('redundancy_consistency_checks', 0)
```

### Files to Modify

| # | File | Changes |
|---|---|---|
| 1 | `conacq/eval/performance_metrics.py` | PerformanceMetrics +8 fields, AggregatedPerformanceMetrics +32 fields (8×4 stats), aggregate_metrics() update |
| 2 | `conacq/runners/congen_runner.py` | ConGenRunResult +8 fields, run() extraction, to_dict(), get_performance_metrics() |
| 3 | `conacq/runners/interactive_runner.py` | InteractiveRunResult.get_performance_metrics() — pass 0 defaults |
| 4 | `tests/test_evaluation.py` | Update all PerformanceMetrics constructors |

### AggregatedPerformanceMetrics New Fields

For each new metric, 4 stats (mean/std/min/max):
- `congen_runtime_mean_ms`, `congen_runtime_std_ms`, `congen_runtime_min_ms`, `congen_runtime_max_ms`
- `solver_time_mean_ms`, `solver_time_std_ms`, `solver_time_min_ms`, `solver_time_max_ms`
- `acqmss_runtime_mean_ms`, `acqmss_runtime_std_ms`, `acqmss_runtime_min_ms`, `acqmss_runtime_max_ms`
- `reduce_runtime_mean_ms`, `reduce_runtime_std_ms`, `reduce_runtime_min_ms`, `reduce_runtime_max_ms`
- `is_consistent_test_cases_calls_mean`, `_std`, `_min`, `_max`
- `is_consistent_calls_mean`, `_std`, `_min`, `_max`
- `acqmss_calls_mean`, `_std`, `_min`, `_max`
- `redundancy_checks_mean`, `_std`, `_min`, `_max`

### InteractiveRunResult Defaults

InteractiveRunResult (QuAcq) doesn't use ConGen algorithms. Pass 0 for all 8 new fields:
```python
congen_runtime_ms=0.0, is_consistent_test_cases_calls=0,
is_consistent_calls=0, solver_time_ms=0.0,
acqmss_runtime_ms=0.0, acqmss_calls=0,
reduce_runtime_ms=0.0, redundancy_consistency_checks=0
```

## Risk Assessment

- **Low risk**: All profiler keys already instrumented — no new instrumentation needed
- **Medium risk**: AggregatedPerformanceMetrics grows from 13 → 45 fields. Consider grouping in to_dict()
- **Test impact**: Need to update all PerformanceMetrics(...) in test_evaluation.py

## Success Criteria

- All 8 metrics correctly extracted from profiler in ConGenRunner.run()
- PerformanceMetrics and AggregatedPerformanceMetrics fully updated
- All existing tests pass with updated constructors
- Cross-validation correctly aggregates new metrics
