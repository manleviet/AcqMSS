# Phase 2: Extend AggregatedPerformanceMetrics + aggregate_metrics()

## Context Links
- Source: `conacq/eval/performance_metrics.py` (lines 98-342)
- Existing pattern: ConGen extended metrics use `_stat4()` helper (lines 286-293) and 4-field groups (mean/std/min/max)
- Consumer: `conacq/eval/cross_validation.py` line 278 (`aggregate_metrics(performance_list)`)

## Overview
- **Priority**: P1 (without this, QuAcq metrics lost during CV aggregation)
- **Status**: complete
- Add aggregated stats (mean/std/min/max) for each QuAcq metric group to `AggregatedPerformanceMetrics`. Update `aggregate_metrics()` to extract and compute them. Update `to_dict()`.

## Key Insights
- Existing pattern is consistent: each metric group gets 4 fields (mean/std/min/max) in the aggregated dataclass
- `_stat4()` helper already computes (mean, std, min, max) -- reuse for all new fields
- Runtime fields: float mean/std/min/max. Count fields: float mean/std, int min/max (matches existing pattern for acqmss_calls)
- 16 new metric groups -> 64 new fields on AggregatedPerformanceMetrics. But some can be grouped logically.
- Actually: group by metric type. 6 runtime groups (4 fields each = 24) + 10 count groups (4 fields each = 40) = 64 fields. Plus `reduce_calls` group (4 fields). Total: ~64 new fields.
- Wait -- `reduce_runtime` already exists in aggregated (lines 147-150). `redundancy_checks` already exists (lines 171-174). So those 2 groups are already handled.
- Net new: 14 metric groups x 4 fields = 56 new fields.

## Requirements
- Add 56 new fields to `AggregatedPerformanceMetrics` (14 groups x 4 stats each)
- Update `aggregate_metrics()` to extract values and compute stats via `_stat4()`
- Update `AggregatedPerformanceMetrics.to_dict()` with new metric groups
- All defaults = 0/0.0 so ConGen aggregation works unchanged

## Related Code Files
- **Modify**: `conacq/eval/performance_metrics.py`

## Implementation Steps

### Step 1: Add fields to AggregatedPerformanceMetrics

After existing redundancy_checks block (line 174), add these groups. Follow existing naming convention (`{metric}_mean`, `{metric}_std`, `{metric}_min`, `{metric}_max`):

**QuAcq runtime groups** (5 new, reduce_runtime already exists):
```python
# QuAcq runtime
quacq_runtime_mean_ms: float = 0.0
quacq_runtime_std_ms: float = 0.0
quacq_runtime_min_ms: float = 0.0
quacq_runtime_max_ms: float = 0.0

# Query generation runtime
query_gen_runtime_mean_ms: float = 0.0
query_gen_runtime_std_ms: float = 0.0
query_gen_runtime_min_ms: float = 0.0
query_gen_runtime_max_ms: float = 0.0

# FindScope runtime
findscope_runtime_mean_ms: float = 0.0
findscope_runtime_std_ms: float = 0.0
findscope_runtime_min_ms: float = 0.0
findscope_runtime_max_ms: float = 0.0

# FindC runtime
findc_runtime_mean_ms: float = 0.0
findc_runtime_std_ms: float = 0.0
findc_runtime_min_ms: float = 0.0
findc_runtime_max_ms: float = 0.0

# DiscriminatingGenerator runtime
dis_gen_runtime_mean_ms: float = 0.0
dis_gen_runtime_std_ms: float = 0.0
dis_gen_runtime_min_ms: float = 0.0
dis_gen_runtime_max_ms: float = 0.0
```

**QuAcq call count groups** (10 new, reduce_calls is new too):
```python
# QuAcq calls
quacq_calls_mean: float = 0.0
quacq_calls_std: float = 0.0
quacq_calls_min: int = 0
quacq_calls_max: int = 0

# Query generation calls
query_gen_calls_mean: float = 0.0
query_gen_calls_std: float = 0.0
query_gen_calls_min: int = 0
query_gen_calls_max: int = 0

# Query generation consistency checks
query_gen_checks_mean: float = 0.0
query_gen_checks_std: float = 0.0
query_gen_checks_min: int = 0
query_gen_checks_max: int = 0

# Prune calls
prune_calls_mean: float = 0.0
prune_calls_std: float = 0.0
prune_calls_min: int = 0
prune_calls_max: int = 0

# Prune is_consistent calls
prune_ic_calls_mean: float = 0.0
prune_ic_calls_std: float = 0.0
prune_ic_calls_min: int = 0
prune_ic_calls_max: int = 0

# FindScope calls
findscope_calls_mean: float = 0.0
findscope_calls_std: float = 0.0
findscope_calls_min: int = 0
findscope_calls_max: int = 0

# FindC calls
findc_calls_mean: float = 0.0
findc_calls_std: float = 0.0
findc_calls_min: int = 0
findc_calls_max: int = 0

# FindC consistency checks
findc_checks_mean: float = 0.0
findc_checks_std: float = 0.0
findc_checks_min: int = 0
findc_checks_max: int = 0

# DiscriminatingGenerator calls
dis_gen_calls_mean: float = 0.0
dis_gen_calls_std: float = 0.0
dis_gen_calls_min: int = 0
dis_gen_calls_max: int = 0

# DiscriminatingGenerator consistency checks
dis_gen_checks_mean: float = 0.0
dis_gen_checks_std: float = 0.0
dis_gen_checks_min: int = 0
dis_gen_checks_max: int = 0

# Reduce calls (distinct from reduce_runtime which already exists)
reduce_calls_mean: float = 0.0
reduce_calls_std: float = 0.0
reduce_calls_min: int = 0
reduce_calls_max: int = 0
```

### Step 2: Update aggregate_metrics()

After existing extended metrics extraction (line 283), add QuAcq extraction:

```python
# QuAcq-specific metrics
quacq_rt = [m.quacq_runtime_ms for m in metrics_list]
qgen_rt = [m.query_generation_runtime_ms for m in metrics_list]
fs_rt = [m.findscope_runtime_ms for m in metrics_list]
fc_rt = [m.findc_runtime_ms for m in metrics_list]
dg_rt = [m.dis_gen_runtime_ms for m in metrics_list]

quacq_c = [float(m.quacq_calls) for m in metrics_list]
qgen_c = [float(m.query_generation_calls) for m in metrics_list]
qgen_chk = [float(m.query_generation_consistency_checks) for m in metrics_list]
prune_c = [float(m.prune_calls) for m in metrics_list]
prune_ic = [float(m.prune_is_consistent_calls) for m in metrics_list]
fs_c = [float(m.findscope_calls) for m in metrics_list]
fc_c = [float(m.findc_calls) for m in metrics_list]
fc_chk = [float(m.findc_consistency_checks) for m in metrics_list]
dg_c = [float(m.dis_gen_calls) for m in metrics_list]
dg_chk = [float(m.dis_gen_consistency_checks) for m in metrics_list]
red_c = [float(m.reduce_calls) for m in metrics_list]
```

Then compute stats with `_stat4()` and pass to constructor.

### Step 3: Update to_dict()

After existing blocks (line 247), add QuAcq sections following same nested dict pattern:

```python
'quacq_runtime': {
    'mean_ms': self.quacq_runtime_mean_ms,
    'std_ms': self.quacq_runtime_std_ms,
    'min_ms': self.quacq_runtime_min_ms,
    'max_ms': self.quacq_runtime_max_ms,
},
# ... (one block per metric group)
```

## Todo List
- [ ] Add 16 metric group fields (64 new fields) to AggregatedPerformanceMetrics
- [ ] Update aggregate_metrics(): extract QuAcq values, compute _stat4(), pass to constructor
- [ ] Update AggregatedPerformanceMetrics.to_dict() with 16 new sections
- [ ] Update class docstring

## Success Criteria
- `aggregate_metrics([quacq_perf1, quacq_perf2])` correctly computes mean/std/min/max for all QuAcq fields
- `aggregate_metrics([congen_perf1, congen_perf2])` still works (all QuAcq fields default to 0)
- `to_dict()` output includes all QuAcq metric groups

## Risk Assessment
- **File size**: performance_metrics.py will grow from ~343 to ~550 lines. Acceptable for a dataclass-heavy module, but monitor. Could extract QuAcq-specific aggregated fields to a separate module later if needed (YAGNI for now).
- **Field name consistency**: Use shortened prefixes (`query_gen_`, `dis_gen_`, `prune_ic_`) to keep names manageable while still descriptive.

## Next Steps
- Phase 3: Fix CrossValidationFoldResult.to_dict() serialization
