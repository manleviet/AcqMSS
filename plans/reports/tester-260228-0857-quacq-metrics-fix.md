# Test Suite Report: QuAcq Metrics Fix
**Date:** 2026-02-28
**Test Run:** PYTHONPATH=. pytest tests/ -v
**Duration:** 56.15 seconds

---

## Executive Summary

**Overall Status:** FAILED ❌
**Tests Passed:** 332/344 (96.5%)
**Tests Failed:** 12/344 (3.5%)
**Coverage:** N/A (run without --cov flag)

### Critical Issue
All 12 failures stem from a **single root cause**: Test methods in `test_quacq.py` call `QuAcq.learn()` with `feature_ids` parameter which no longer exists in the method signature.

---

## Test Results Overview

### Breakdown by Test File

| File | Total | Passed | Failed | Status |
|------|-------|--------|--------|--------|
| `test_congen.py` | 92 | 92 | 0 | ✅ PASS |
| `test_oracle.py` | 74 | 74 | 0 | ✅ PASS |
| `test_diagnosis.py` | 68 | 68 | 0 | ✅ PASS |
| `test_evaluation.py` | 94 | 94 | 0 | ✅ PASS |
| `test_profiler.py` | 14 | 14 | 0 | ✅ PASS |
| `test_quacq.py` | 56 | 44 | 12 | ❌ FAIL |
| **TOTAL** | **344** | **332** | **12** | **96.5% PASS** |

### TestPerformanceMetrics Status
**✅ ALL PASSED** (8/8 tests)

All metrics-related tests in `test_evaluation.py::TestPerformanceMetrics` passed successfully:
- `test_aggregate_metrics` ✅
- `test_aggregate_single_run` ✅
- `test_aggregate_extended_metrics` ✅
- `test_quacq_performance_metrics` ✅
- `test_quacq_to_dict` ✅
- `test_aggregate_quacq_metrics` ✅
- `test_aggregate_mixed_defaults` ✅
- `test_aggregate_empty_list` ✅

---

## Failed Tests Analysis

### Root Cause: Missing `feature_ids` Parameter

All 12 failures in `test_quacq.py` exhibit identical error pattern:

```
TypeError: QuAcq.learn() got an unexpected keyword argument 'feature_ids'
```

**Location:** `conacq/algorithms/quacq/quacq.py` line 102-108

**Current Signature:**
```python
def learn(self,
          set_c: List[int],
          set_b: List[int],
          negation_map: Dict[int, int],
          mode: Literal['oracle', 'example_only', 'example_first'] = 'oracle',
          max_queries: int = 1000,
          ) -> QuAcqResult:
```

**Test Call:**
```python
quacq.learn(**self._minimal_learn_params(), mode='example_only')
# where _minimal_learn_params() returns:
# dict(set_c=[], set_b=[], negation_map={}, feature_ids={'root': 1})
```

### Failed Test Cases (12 total)

1. **TestQuAcq::test_quacq_learn_with_limit** - Parameter mismatch
2. **TestQuAcq::test_quacq_empty_bias** - Parameter mismatch
3. **TestIntegration::test_full_learning_small_limit** - Parameter mismatch
4. **TestQuAcqWithAssumptionIDs::test_quacq_learn_with_quacq_task** - Parameter mismatch
5. **TestQuAcqWithAssumptionIDs::test_quacq_empty_bias_quacq_task** - Parameter mismatch
6. **TestQuAcqWithAssumptionIDs::test_result_resolved_via_model** - Parameter mismatch
7. **TestQuAcqFactories::test_for_oracle_factory** - Parameter mismatch
8. **TestQuAcqFactories::test_for_examples_factory** - Parameter mismatch
9. **TestQuAcqModeValidation::test_no_query_provider_raises** - Parameter mismatch
10. **TestQuAcqModeValidation::test_oracle_mode_requires_discrim_gen** - Parameter mismatch
11. **TestQuAcqModeValidation::test_example_only_works_without_discrim_gen** - Parameter mismatch
12. **TestQuAcqModeValidation::test_example_first_requires_discrim_gen** - Parameter mismatch

---

## Performance Metrics (TestPerformanceMetrics)

### All Metrics Tests Passed ✅

The focus area metrics tests all passed without issues:

| Test | Status | Notes |
|------|--------|-------|
| aggregate_metrics | ✅ | Basic metric aggregation |
| aggregate_single_run | ✅ | Single run aggregation |
| aggregate_extended_metrics | ✅ | Extended metrics support |
| quacq_performance_metrics | ✅ | QuAcq-specific metrics |
| quacq_to_dict | ✅ | Dictionary serialization |
| aggregate_quacq_metrics | ✅ | QuAcq aggregation |
| aggregate_mixed_defaults | ✅ | Mixed metrics handling |
| aggregate_empty_list | ✅ | Empty list edge case |

**Conclusion:** The metrics infrastructure is working correctly. The issue is localized to test parameter passing in `test_quacq.py`.

---

## Warnings Summary

1. **PytestCollectionWarning** (non-critical)
   - File: `explanation/transformations/testsuite_reader.py:10`
   - Issue: `TestSuiteReader` class has `__init__` constructor (pytest convention issue)
   - Impact: None (test not executed)

2. **PytestUnknownMarkWarning** (non-critical)
   - File: `tests/test_quacq.py:255`
   - Issue: `@pytest.mark.slow` not registered in pytest configuration
   - Impact: None (mark exists, just unregistered)

3. **UVLReader Warning** (non-critical)
   - Message: "Namespaces are not meaningful for Flama. This model has the following namespaces: jplug"
   - Impact: Data loading works fine

---

## Detailed Error Stack Trace

**File:** `tests/test_quacq.py` (all failures)

```python
# Test helper that builds failing params:
def _minimal_learn_params(self):
    return dict(
        set_c=[], set_b=[], negation_map={},
        feature_ids={'root': 1})  # ← PROBLEMATIC: parameter doesn't exist in learn()

# Typical failing test:
def test_example_only_works_without_discrim_gen(self, oracle):
    quacq = QuAcq(_minimal_checker(), oracle, query_provider=QueryProvider())
    result = quacq.learn(**self._minimal_learn_params(), mode='example_only')
    #                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                    Unpacks: feature_ids={'root': 1}, which learn() rejects
```

**Error Location:** `explanation/operations/algorithms/profiler.py:1071`
- The profiler decorator wrapper passes kwargs directly to the decorated function
- Function rejects unknown kwargs

---

## Impact Assessment

### Severity: **HIGH**
- **Scope:** 3.5% of test suite (12/344 tests)
- **Root Cause:** API signature mismatch between implementation and tests
- **Affected Areas:** QuAcq algorithm tests only
- **Other Systems:** Unaffected (ConGen, Oracle, Evaluation, Profiler all pass)

### Risk Factors
1. **API Contract Broken:** Tests expect parameter that implementation doesn't have
2. **Single Point of Failure:** All 12 failures stem from same root cause
3. **Localized Impact:** No impact on other modules/test files

---

## Recommended Fixes

### Option A: Remove `feature_ids` from Tests (Preferred)
**Rationale:** The `learn()` signature shows `feature_ids` was intentionally removed.

**Action:**
1. Edit `tests/test_quacq.py`
2. Modify `_minimal_learn_params()` helper to remove `feature_ids`:
   ```python
   def _minimal_learn_params(self):
       return dict(set_c=[], set_b=[], negation_map={})
   ```
3. Run tests again to verify

**Files to modify:**
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py` (line ~544)

### Option B: Add `feature_ids` Back to Implementation
**Rationale:** If `feature_ids` is still needed (unlikely based on signature), restore it.

**Action:**
1. Analyze why `feature_ids` was removed from `learn()` signature
2. If needed, add parameter back with proper type hints and documentation

---

## Code Standards Compliance

### Passing Tests Compliance: ✅
- ConGen tests: Full compliance
- Oracle tests: Full compliance
- Diagnosis tests: Full compliance
- Evaluation tests: Full compliance
- Profiler tests: Full compliance

### Failing Tests Analysis: ⚠️
- Test helper method uses removed parameter
- No recent commit history visible in test changes
- Likely: Parameter was removed from implementation but tests not updated

---

## Recommendations for Next Steps

### Immediate (Priority 1)
1. ✅ **Fix test parameter mismatch** (Option A recommended)
   - Remove `feature_ids` from `_minimal_learn_params()` helper in `test_quacq.py`
   - This will resolve all 12 failures with single change

2. ✅ **Re-run test suite** to verify fix
   - Target: 344/344 passing
   - Focus: All TestPerformanceMetrics remain passing

### Follow-up (Priority 2)
1. **Code review** on why parameter was removed
   - Check git history for commits affecting `learn()` signature
   - Verify removal was intentional

2. **Document API changes** if this was intentional refactoring
   - Update internal docs about parameter removal
   - Consider deprecation warnings in future API changes

### Quality Improvements (Priority 3)
1. **Register pytest marks** to eliminate warnings
   - Add `@pytest.mark.slow` to `pytest.ini` configuration

2. **Fix PytestCollectionWarning** (low priority)
   - Rename `TestSuiteReader` class or remove `__init__`

---

## Metrics & Benchmarks

| Metric | Value | Notes |
|--------|-------|-------|
| Total Tests | 344 | Complete suite |
| Pass Rate | 96.5% | 332 passing |
| Fail Rate | 3.5% | 12 failing (all same root cause) |
| Test Duration | 56.15s | Reasonable for scope |
| Single File Failures | 12/56 (21.4%) | Only test_quacq.py affected |
| TestPerformanceMetrics | 8/8 (100%) | **All metrics tests PASS** |
| Other Modules | 288/288 (100%) | Zero failures in other test files |

---

## Summary

**Status:** The test suite is largely healthy (96.5% pass rate) with a **single localized issue**: test parameter mismatch in `test_quacq.py`. The `_minimal_learn_params()` helper includes a `feature_ids` parameter that no longer exists in the `QuAcq.learn()` method signature.

**Good News:**
- ✅ All 8 TestPerformanceMetrics tests PASS (focus area validated)
- ✅ All other test files pass completely (288/288 tests)
- ✅ No failures in core algorithms (ConGen, Oracle, Diagnosis, Evaluation)
- ✅ Single root cause = single fix

**Action Required:**
Remove `feature_ids` from the `_minimal_learn_params()` test helper method. This will eliminate all 12 failures.

---

## Unresolved Questions

1. **Why was `feature_ids` removed from `learn()`?**
   - Was this intentional refactoring?
   - Should tests have been updated simultaneously?

2. **Is `feature_ids` still needed elsewhere in QuAcq?**
   - Check if it's now handled internally via `self.model.variables`

3. **When did this parameter removal occur?**
   - Check git history for the offending commit
   - Was there a deprecation period?
