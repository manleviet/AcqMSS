# Phase 02: Make PerformanceMetrics.n_mss Optional

## Context
- Parent: [plan.md](plan.md)
- Depends on: Phase 01

## Overview
- **Priority**: High
- **Status**: Complete
- **Progress**: 100%
- **Description**: Change `PerformanceMetrics.n_mss` from `int` to `Optional[int] = None`; remove `n_mss=0` hack in InteractiveRunResult

## Key Insights
- InteractiveRunResult hardcodes `n_mss=0` — semantically wrong (QuAcq has no MSS step)
- `AggregatedPerformanceMetrics` has `n_mss_mean` which aggregates n_mss values
- `aggregate_metrics()` computes stats on n_mss list — needs to handle None values
- `CrossValidationFoldResult` has `n_mss` field populated from `getattr(run_result, 'n_mss', 0)`

## Requirements
- `PerformanceMetrics.n_mss: Optional[int] = None`
- `aggregate_metrics()` filters out None n_mss values before computing stats
- `AggregatedPerformanceMetrics.n_mss_mean` becomes `Optional[float] = None`
- `to_dict()` methods handle None n_mss gracefully (omit or null)
- InteractiveRunResult.get_performance_metrics() passes `n_mss=None` instead of 0

## Related Code Files
- **Modify**: `conacq/eval/performance_metrics.py` (PerformanceMetrics, AggregatedPerformanceMetrics, aggregate_metrics)
- **Modify**: `conacq/runners/interactive_runner.py` (or base_runner.py after Phase 01)
- **Modify**: `conacq/eval/cross_validation.py` (CrossValidationFoldResult.n_mss handling)

## Implementation Steps

1. Update `PerformanceMetrics.n_mss` to `Optional[int] = None`
2. Reorder fields: move n_mss after n_kb (both have defaults now)
3. Update `PerformanceMetrics.to_dict()` to handle None n_mss
4. Update `AggregatedPerformanceMetrics.n_mss_mean` to `Optional[float] = None`
5. Update `aggregate_metrics()` to filter None n_mss values
6. Update InteractiveRunResult.get_performance_metrics() to pass `n_mss=None`
7. Update CrossValidationFoldResult to handle None n_mss

## Todo
- [x] Update PerformanceMetrics.n_mss to Optional
- [x] Update aggregate_metrics() for None handling
- [x] Update AggregatedPerformanceMetrics
- [x] Remove n_mss=0 hack in InteractiveRunResult
- [x] Update CrossValidationFoldResult n_mss handling

## Completion Summary
- PerformanceMetrics.n_mss: Optional[int] = None (from required int)
- AggregatedPerformanceMetrics.n_mss_mean: Optional[float] = None
- aggregate_metrics() filters None values before computing stats
- InteractiveRunResult.get_performance_metrics() passes n_mss=None (removed 0 hack)
- CrossValidationFoldResult handles None n_mss gracefully via getattr with None default

## Success Criteria
- No more `n_mss=0` hack for QuAcq results
- ConGen results still pass `n_mss=<actual value>`
- Aggregation handles mixed None/int n_mss lists

## Risk Assessment
- **Downstream consumers**: `extract_results.py`, `report.py` may read n_mss. Need to handle None.
- **JSON output**: n_mss: null vs omitted — choose null for explicit indication.
