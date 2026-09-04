# Phase 1: Extend PerformanceMetrics Dataclass

## Context Links
- Source: `conacq/eval/performance_metrics.py` (lines 38-95)
- Caller: `conacq/runners/quacq_runner.py` lines 92-117 (get_performance_metrics)
- Base fallback: `conacq/runners/base_runner.py` lines 58-66 (base get_performance_metrics)

## Overview
- **Priority**: P1 (blocks all QuAcq CV runs)
- **Status**: complete
- Add 16 QuAcq-specific fields to `PerformanceMetrics` dataclass, all with defaults so ConGen path is unaffected. Update `to_dict()` to include them.

## Key Insights
- `QuAcqRunResult.get_performance_metrics()` already passes exactly these 16 kwargs (lines 99-116 of quacq_runner.py). The dataclass just needs to accept them.
- All 16 fields have clear types: 6 float runtimes (ms), 10 int call counts.
- `reduce_runtime_ms` and `redundancy_consistency_checks` already exist on PerformanceMetrics (ConGen uses them too). QuAcq also sets them, so no duplication needed for those 2.
- Net new fields: **14** (not 16). `reduce_runtime_ms` (line 74) and `redundancy_consistency_checks` (line 77) already present.
- Actually `reduce_calls` is new (ConGen doesn't track call count, only runtime).

## Requirements
- Add 14 new optional fields with defaults to `PerformanceMetrics`
- Update docstring to mention QuAcq metrics
- Update `to_dict()` to include all new fields
- Zero-default ensures ConGen and base `get_performance_metrics()` work unchanged

## Related Code Files
- **Modify**: `conacq/eval/performance_metrics.py`
- **No change needed**: `conacq/runners/quacq_runner.py` (already correct once dataclass accepts kwargs)
- **No change needed**: `conacq/runners/base_runner.py` (base uses only 4 core fields, defaults handle rest)

## Implementation Steps

1. In `PerformanceMetrics` dataclass (after line 77), add these 14 fields with defaults:

```python
# QuAcq-specific runtime metrics (ms)
quacq_runtime_ms: float = 0.0
query_generation_runtime_ms: float = 0.0
findscope_runtime_ms: float = 0.0
findc_runtime_ms: float = 0.0
dis_gen_runtime_ms: float = 0.0

# QuAcq-specific call counts
quacq_calls: int = 0
query_generation_calls: int = 0
query_generation_consistency_checks: int = 0
prune_calls: int = 0
prune_is_consistent_calls: int = 0
findscope_calls: int = 0
findc_calls: int = 0
findc_consistency_checks: int = 0
dis_gen_calls: int = 0
dis_gen_consistency_checks: int = 0
reduce_calls: int = 0
```

Note: `reduce_runtime_ms` and `redundancy_consistency_checks` already exist. `reduce_calls` is new.

2. Update `to_dict()` to include QuAcq fields (add after line 94):

```python
# QuAcq-specific metrics (zero when unused)
'quacq_runtime_ms': self.quacq_runtime_ms,
'query_generation_runtime_ms': self.query_generation_runtime_ms,
'findscope_runtime_ms': self.findscope_runtime_ms,
'findc_runtime_ms': self.findc_runtime_ms,
'dis_gen_runtime_ms': self.dis_gen_runtime_ms,
'quacq_calls': self.quacq_calls,
'query_generation_calls': self.query_generation_calls,
'query_generation_consistency_checks': self.query_generation_consistency_checks,
'prune_calls': self.prune_calls,
'prune_is_consistent_calls': self.prune_is_consistent_calls,
'findscope_calls': self.findscope_calls,
'findc_calls': self.findc_calls,
'findc_consistency_checks': self.findc_consistency_checks,
'dis_gen_calls': self.dis_gen_calls,
'dis_gen_consistency_checks': self.dis_gen_consistency_checks,
'reduce_calls': self.reduce_calls,
```

3. Update module docstring and class docstring to mention QuAcq metrics.

## Todo List
- [ ] Add 16 QuAcq fields to PerformanceMetrics (14 new + verify 2 existing)
- [ ] Update PerformanceMetrics.to_dict() with new fields
- [ ] Update docstrings (module + class)
- [ ] Verify QuAcqRunResult.get_performance_metrics() kwargs match field names exactly

## Success Criteria
- `QuAcqRunResult.get_performance_metrics()` no longer raises TypeError
- `PerformanceMetrics(runtime_ms=1, consistency_checks=1, memory_peak_mb=1, n_kb=1)` still works (ConGen path)
- `to_dict()` includes all QuAcq fields

## Risk Assessment
- **Low risk**: Only adding optional fields with defaults. No existing behavior changes.
- **Field name mismatch**: Must verify quacq_runner.py kwargs match new field names exactly (already verified above).

## Next Steps
- Phase 2: Extend AggregatedPerformanceMetrics and aggregate_metrics()
