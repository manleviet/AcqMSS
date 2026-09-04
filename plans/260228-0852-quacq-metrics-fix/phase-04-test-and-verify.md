# Phase 4: Test and Verify

## Context Links
- Test file: `tests/test_evaluation.py` (class TestPerformanceMetrics, lines 293-385)
- Existing tests: `test_aggregate_metrics`, `test_aggregate_single_run`, `test_aggregate_extended_metrics`, `test_aggregate_empty_list`

## Overview
- **Priority**: P1
- **Status**: complete
- Add tests for QuAcq-specific metrics in PerformanceMetrics construction, to_dict(), aggregation, and CV fold serialization. Run full test suite to confirm no regressions.

## Key Insights
- Existing tests only use ConGen fields (congen_runtime_ms, acqmss_*, etc.)
- Need to verify: (a) QuAcq fields accepted by constructor, (b) to_dict() includes them, (c) aggregate_metrics() computes correct stats, (d) ConGen path still works with all-zero QuAcq defaults

## Requirements
- Test QuAcq PerformanceMetrics construction
- Test QuAcq fields in to_dict()
- Test QuAcq fields survive aggregate_metrics()
- Test mixed ConGen+QuAcq aggregation (QuAcq fields default to 0 for ConGen runs)
- Test CrossValidationFoldResult.to_dict() includes extended metrics
- Full test suite pass: `PYTHONPATH=. pytest tests/ -v`

## Related Code Files
- **Modify**: `tests/test_evaluation.py`
- **Verify** (no changes): all 3 source files from Phases 1-3

## Implementation Steps

### Step 1: Add test_quacq_performance_metrics

In `TestPerformanceMetrics` class, add:

```python
def test_quacq_performance_metrics(self):
    """Test PerformanceMetrics accepts QuAcq-specific fields."""
    pm = PerformanceMetrics(
        runtime_ms=500,
        consistency_checks=200,
        memory_peak_mb=25,
        n_kb=10,
        quacq_runtime_ms=450,
        query_generation_runtime_ms=100,
        findscope_runtime_ms=80,
        findc_runtime_ms=120,
        dis_gen_runtime_ms=50,
        reduce_runtime_ms=30,
        quacq_calls=5,
        query_generation_calls=20,
        query_generation_consistency_checks=40,
        prune_calls=15,
        prune_is_consistent_calls=30,
        findscope_calls=5,
        findc_calls=5,
        findc_consistency_checks=25,
        dis_gen_calls=3,
        dis_gen_consistency_checks=10,
        reduce_calls=2,
        redundancy_consistency_checks=8,
    )
    assert pm.quacq_runtime_ms == 450
    assert pm.findscope_calls == 5
    assert pm.reduce_calls == 2
```

### Step 2: Add test_quacq_to_dict

```python
def test_quacq_to_dict(self):
    """Test to_dict() includes QuAcq fields."""
    pm = PerformanceMetrics(
        runtime_ms=100, consistency_checks=50,
        memory_peak_mb=10, n_kb=5,
        quacq_runtime_ms=90, findc_calls=7,
    )
    d = pm.to_dict()
    assert d['quacq_runtime_ms'] == 90
    assert d['findc_calls'] == 7
    assert d['findscope_runtime_ms'] == 0.0  # default
```

### Step 3: Add test_aggregate_quacq_metrics

```python
def test_aggregate_quacq_metrics(self):
    """Test aggregate_metrics() handles QuAcq-specific fields."""
    metrics_list = [
        PerformanceMetrics(
            runtime_ms=100, consistency_checks=50,
            memory_peak_mb=10, n_kb=5,
            quacq_runtime_ms=80, findscope_calls=4,
            findc_consistency_checks=20,
        ),
        PerformanceMetrics(
            runtime_ms=200, consistency_checks=70,
            memory_peak_mb=15, n_kb=7,
            quacq_runtime_ms=160, findscope_calls=8,
            findc_consistency_checks=40,
        ),
    ]
    agg = aggregate_metrics(metrics_list)
    assert agg.quacq_runtime_mean_ms == 120  # (80+160)/2
    assert agg.quacq_runtime_min_ms == 80
    assert agg.quacq_runtime_max_ms == 160
    assert agg.findscope_calls_mean == 6  # (4+8)/2
    assert agg.findc_checks_mean == 30  # (20+40)/2
```

### Step 4: Add test_aggregate_mixed_congen_quacq

```python
def test_aggregate_mixed_defaults(self):
    """Test ConGen metrics aggregate fine with QuAcq fields at zero defaults."""
    metrics_list = [
        PerformanceMetrics(
            runtime_ms=100, consistency_checks=50,
            memory_peak_mb=10, n_kb=5,
            congen_runtime_ms=90,
        ),
    ]
    agg = aggregate_metrics(metrics_list)
    # ConGen fields work
    assert agg.congen_runtime_mean_ms == 90
    # QuAcq fields all zero (defaults)
    assert agg.quacq_runtime_mean_ms == 0.0
    assert agg.findscope_calls_mean == 0.0
```

### Step 5: Add test for CV fold to_dict (optional, if easy to construct)

Verify `CrossValidationFoldResult.to_dict()['performance']` uses `PerformanceMetrics.to_dict()` output. Can check that QuAcq fields appear in fold dict when present.

### Step 6: Run full test suite

```bash
PYTHONPATH=. pytest tests/ -v
```

Verify:
- All existing tests pass (no regressions)
- New tests pass
- No ConGen-related test failures

## Todo List
- [ ] Add test_quacq_performance_metrics
- [ ] Add test_quacq_to_dict
- [ ] Add test_aggregate_quacq_metrics
- [ ] Add test_aggregate_mixed_defaults
- [ ] Add test_cv_fold_to_dict_includes_extended_metrics (optional)
- [ ] Run full test suite
- [ ] Verify no regressions

## Success Criteria
- All new tests pass
- All existing tests pass unchanged
- `PYTHONPATH=. pytest tests/ -v` green

## Risk Assessment
- **Low risk**: Tests are additive. No existing test modified.
- **Test isolation**: New tests use only PerformanceMetrics + aggregate_metrics, no external dependencies.

## Next Steps
- Done. All 4 phases complete the fix.
