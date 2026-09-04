# Phase 3: Fix CrossValidationFoldResult.to_dict() Serialization

## Context Links
- Source: `conacq/eval/cross_validation.py` lines 54-78
- PerformanceMetrics.to_dict(): `conacq/eval/performance_metrics.py` lines 79-95 (will include QuAcq fields after Phase 1)

## Overview
- **Priority**: P2 (data loss in JSON output, but not a crash)
- **Status**: complete
- `CrossValidationFoldResult.to_dict()` manually picks 5 fields from `self.performance` (lines 60-66) instead of delegating to `self.performance.to_dict()`. This means all extended metrics (both ConGen profiler and QuAcq) are silently dropped from fold-level JSON output.

## Key Insights
- Current code (lines 60-67):
  ```python
  'performance': {
      'runtime_ms': self.performance.runtime_ms,
      'consistency_checks': self.performance.consistency_checks,
      'memory_peak_mb': self.performance.memory_peak_mb,
      'n_mss': self.performance.n_mss,
      'n_kb': self.performance.n_kb,
      'profiler': self.profiler_data,
  },
  ```
- This misses ALL extended metrics (congen_runtime_ms, acqmss_*, solver_time_ms, etc.) and will miss all QuAcq metrics too.
- Fix: delegate to `self.performance.to_dict()` and merge `profiler_data` into it.
- The `profiler` key carries the raw profiler snapshot (pass-through). Keep it.

## Requirements
- Replace manual field picking with `self.performance.to_dict()`
- Preserve `profiler` key in the output dict (merge it in)
- Backward compatible: same keys still present, just more data now

## Related Code Files
- **Modify**: `conacq/eval/cross_validation.py` (lines 60-67 only)

## Implementation Steps

1. Replace the `'performance'` section in `CrossValidationFoldResult.to_dict()`:

**Before** (lines 60-67):
```python
'performance': {
    'runtime_ms': self.performance.runtime_ms,
    'consistency_checks': self.performance.consistency_checks,
    'memory_peak_mb': self.performance.memory_peak_mb,
    'n_mss': self.performance.n_mss,
    'n_kb': self.performance.n_kb,
    'profiler': self.profiler_data,
},
```

**After**:
```python
'performance': {
    **self.performance.to_dict(),
    'profiler': self.profiler_data,
},
```

This is a single-line change (plus dict unpacking). The `to_dict()` already includes `runtime_ms`, `consistency_checks`, `memory_peak_mb`, `n_mss`, `n_kb` plus all extended and QuAcq metrics.

2. Verify no other code depends on the exact shape of fold `performance` dict. Check consumers:
   - `apps/extract_results.py` reads fold dicts -- check it accesses `performance` keys
   - `apps/run_cv.py` writes the JSON but doesn't read fold performance back

## Todo List
- [ ] Replace manual field picking with `self.performance.to_dict()` + profiler merge
- [ ] Verify `apps/extract_results.py` doesn't break (check field access patterns)

## Success Criteria
- `CrossValidationFoldResult.to_dict()['performance']` includes all PerformanceMetrics fields
- `profiler` key still present in output
- Existing keys (`runtime_ms`, `consistency_checks`, etc.) still at same dict level

## Risk Assessment
- **Low risk**: Pure additive change. Existing keys preserved. New keys added.
- **extract_results.py**: May access `performance['runtime_ms']` etc. -- still present. No breakage.
- **JSON size**: Fold JSONs will be slightly larger. Negligible impact.

## Next Steps
- Phase 4: Test and verify all changes
