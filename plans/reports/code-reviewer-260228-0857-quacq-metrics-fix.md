# Code Review: QuAcq Performance Metrics Pipeline Fix

**Date:** 2026-02-28
**Reviewer:** code-reviewer
**Commit:** 84e1c11 (partial -- metrics changes within larger commit)
**Plan:** `plans/260228-0852-quacq-metrics-fix/`

---

## Scope

- **Files:** 3 modified (`performance_metrics.py`, `cross_validation.py`, `test_evaluation.py`)
- **LOC changed:** ~350 added
- **Focus:** Bug fix -- QuAcq metrics pipeline crash + CV aggregation data loss

## Overall Assessment

**PASS.** The fix is correct, well-tested, and backward-compatible. All 30 evaluation tests pass. The field names in `PerformanceMetrics` exactly match the kwargs from `QuAcqRunResult.get_performance_metrics()` (verified programmatically). The end-to-end pipeline `QuAcqRunResult -> PerformanceMetrics -> aggregate_metrics -> AggregatedPerformanceMetrics -> to_dict()` works correctly.

---

## Critical Issues

None.

---

## High Priority

### 1. File exceeds 200-line threshold (652 lines)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/performance_metrics.py`
**Impact:** Maintainability. The file is now 652 lines, 3x the Python threshold (200). Each new algorithm (beyond ConGen/QuAcq) will add ~80 fields to `AggregatedPerformanceMetrics` and ~16 to `PerformanceMetrics` plus the corresponding `aggregate_metrics()` and `to_dict()` boilerplate.

**Recommendation (future):** Consider splitting into:
- `performance_metrics.py` -- `PerformanceMetrics` dataclass + `to_dict()`
- `aggregated_metrics.py` -- `AggregatedPerformanceMetrics` dataclass + `aggregate_metrics()` + `to_dict()`

Or alternatively, use `dataclasses.asdict()` for `PerformanceMetrics.to_dict()` since the keys exactly match field names, which would eliminate the manual dict construction entirely.

**Verdict:** Not blocking. The file is repetitive but uniform. Splitting now would add import churn for zero functional benefit.

---

## Medium Priority

### 2. AggregatedPerformanceMetrics naming inconsistency with PerformanceMetrics

**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/performance_metrics.py`

`PerformanceMetrics` uses full names (`query_generation_runtime_ms`, `query_generation_calls`) while `AggregatedPerformanceMetrics` shortens to `query_gen_runtime_*_ms`, `query_gen_calls_*`. Same for `prune_is_consistent_calls` -> `prune_ic_calls_*`.

This is intentional (plan mentions "shortened for manageability") and documented in the plan. The tradeoff is reasonable -- aggregated fields have 4 statistical suffixes each, so full names would be unwieldy (e.g., `query_generation_consistency_checks_mean`). The shortened form is consistently applied.

**Verdict:** Acceptable. The naming contract is: `PerformanceMetrics` uses canonical names matching the runner, `AggregatedPerformanceMetrics` uses shortened prefixes for the 4-stat groups. Keep this documented.

### 3. `to_dict()` duplication between PerformanceMetrics fields and manual dict

Both `PerformanceMetrics.to_dict()` and the dataclass fields have identical keys (verified: 29 fields = 29 dict keys, zero missing). The manual dict is pure boilerplate.

**Potential simplification:**
```python
def to_dict(self) -> dict:
    return dataclasses.asdict(self)
```

**Verdict:** Low-risk improvement for a future cleanup. Current approach is explicit and works.

---

## Low Priority

### 4. Terse variable names in `aggregate_metrics()`

Variables like `qrt_mean`, `qgrt_std`, `fsrt_min`, `fcchk_max`, `dgc_std`, `pic_mean` are hard to parse in isolation. However, the pattern is consistent (`{metric_abbrev}_{stat}`) and local to a single function.

**Verdict:** Acceptable given the function structure. The 4-tuple unpacking pattern (`a, b, c, d = _stat4(values)`) enforces consistency.

### 5. ConGen-only JSON output now includes zero-valued QuAcq fields

`PerformanceMetrics.to_dict()` always emits all 29 keys, even for ConGen runs where all QuAcq fields are 0/0.0. This adds ~16 zero-valued keys to every ConGen fold JSON.

**Verdict:** Negligible. JSON size impact is trivial. Consistent schema across run types simplifies downstream consumers (no conditional field presence).

---

## Edge Cases Verified

| Scenario | Status |
|----------|--------|
| `QuAcqRunResult.get_performance_metrics()` kwargs match `PerformanceMetrics` fields exactly | Verified (16 QuAcq kwargs, all accepted) |
| `ConGenRunResult.get_performance_metrics()` still works (no QuAcq kwargs) | Verified (all QuAcq fields default to 0/0.0) |
| `BaseRunResult.get_performance_metrics()` still works (minimal 4 kwargs) | Verified |
| `aggregate_metrics()` with pure-ConGen metrics (QuAcq fields all zero) | Verified (test_aggregate_mixed_defaults) |
| `aggregate_metrics()` with pure-QuAcq metrics (ConGen fields all zero) | Verified (test_aggregate_quacq_metrics) |
| `CrossValidationFoldResult.to_dict()` delegates to `performance.to_dict()` | Verified, includes `profiler` key merged in |
| `CrossValidationResult.to_dict()` -> `performance.to_dict()` (uses `AggregatedPerformanceMetrics`) | Verified |
| `conacq/eval/report.py` line 261 `cv_result.performance.to_dict()` | Verified (uses `AggregatedPerformanceMetrics.to_dict()`) |
| Empty metrics list still raises ValueError | Verified (test_aggregate_empty_list) |
| Single-run aggregation (std=0) | Verified (test_aggregate_single_run) |

---

## Positive Observations

1. **Backward compatibility preserved.** All 0/0.0 defaults mean no caller changes needed for ConGen path.
2. **CV fold serialization fix is elegant.** `**self.performance.to_dict()` replaces 5 manual field picks, automatically including all current and future fields.
3. **Tests cover the key scenarios:** construction, serialization, aggregation with QuAcq values, aggregation with mixed defaults, and the empty-list error case.
4. **`_stat4()` helper reuse** -- all 16 new metric groups use the same pattern as existing ConGen groups.

---

## Test Results

```
tests/test_evaluation.py: 30 passed in 0.17s
```

New tests added: 4 (test_quacq_performance_metrics, test_quacq_to_dict, test_aggregate_quacq_metrics, test_aggregate_mixed_defaults)

---

## Recommended Actions

1. **No blocking changes required.** The fix is correct and complete.
2. **(Future)** Consider `dataclasses.asdict()` for `PerformanceMetrics.to_dict()` to eliminate manual dict construction.
3. **(Future)** If a third algorithm is added, refactor the aggregation to be data-driven (field metadata) rather than manual field-by-field expansion.

---

## Metrics

- **Type Coverage:** All fields typed (dataclass fields with explicit `float`/`int` annotations)
- **Test Coverage:** 4 new tests covering construction, serialization, aggregation, backward compatibility
- **Linting Issues:** 0

---

## Unresolved Questions

None.
