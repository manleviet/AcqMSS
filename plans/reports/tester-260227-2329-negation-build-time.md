# Test Results: Negation Build-Time Refactor

**Date**: February 27, 2026
**Test Suite**: Full test suite (340 tests)
**Status**: **ALL PASSED** ✓

## Summary

Negation computation refactoring moved from prepare-time to build-time in both ConGenModelBuilder and QuAcqModelBuilder. This was a behavior-preserving refactor with one critical bug fix.

### Test Results Overview
- **Total Tests**: 340
- **Passed**: 340 (100%)
- **Failed**: 0
- **Skipped**: 0
- **Execution Time**: 53.93 seconds

## Key Tests Verified

### ConGen Module (test_congen.py)
- `test_congen_*` (3 tests): ConGen pipeline with different example sets — PASSED
- `test_acqmss_*` (2 tests): ACQMSS core functionality — PASSED
- `test_reduce_*` (1 test): REDUCE algorithm — PASSED
- `test_generate_ne_*` (1 test): GenerateNE algorithm — PASSED
- `TestConGenModelBuilder` (5 tests):
  - `test_auto_prepare_from_file` — PASSED
  - `test_auto_prepare_from_data` — PASSED
  - `test_build_without_oracle_raises` — PASSED
  - **`test_cv_re_prepare` — FIXED & PASSED** (was failing, see issue below)
  - `test_last_call_wins` — PASSED
- `TestOracleFeatureIds` (6 tests): Oracle consistency checks — PASSED

### QuAcq Module (test_quacq.py)
- All 48 QuAcq tests passed, including:
  - QuAcq learning with assumption IDs
  - Task preparation and background clauses
  - Query generation and converter tests

### Diagnosis Module (test_diagnosis.py)
- 201+ diagnosis tests (FastDiag, FastDiagP, HSDAG, KBDiag, WipeOutR variants)
- All passed with incremental/non-incremental modes and profiling enabled/disabled

### Supporting Modules
- **test_evaluation.py**: 27 tests — PASSED
- **test_oracle_model.py**: 7 tests — PASSED
- **test_profiler.py**: 11 tests — PASSED
- **test_query_converter.py**: 10 tests — PASSED
- **test_semantic_equivalence.py**: 8 tests — PASSED
- **test_utils.py**: 8 tests — PASSED

## Critical Bug Fix

### Issue: Idempotent Re-prepare Failing
**Location**: `conacq/algorithms/acqmss/task_preparation.py` (line 118)
**Problem**: When `prepare()` was called multiple times on the same model (e.g., for CV folds), the assumption IDs shifted to different ranges, causing non-idempotent behavior.

**Root Cause**:
1. During `build()`, negation computation increments `model.next_available_id`
2. During `prepare()`, line 98 correctly reads from `model.next_available_id` to skip Tseitin vars
3. At line 118, `model.next_available_id` was updated to the final assumption ID
4. Second `prepare()` call started from the updated (wrong) `model.next_available_id` instead of the post-build value

**Example**:
```
First prepare():  model.next_available_id: 116 → 768 (stored back)
Second prepare(): model.next_available_id: 768 → 1420 (started from wrong value)
Result: KB[2] = [-1, 2, -768] (second) vs [-1, 2, -116] (first) — DIFFERENT!
```

**Fix**: Removed line 118 that updated `model.next_available_id` after prepare().
- `model.next_available_id` is set by builder at build time and must remain fixed
- Prepare() should not mutate this value across multiple calls
- Added explanatory comment about idempotent re-prepare requirements

**Test Validation**:
```python
Before fix:  task1_kb == task2_kb: False (KB differed on 2nd prepare)
After fix:   task1_kb == task2_kb: True  (KB identical on both prepares)
```

## Warnings (Expected, Non-Critical)

### PytestCollectionWarning
- **File**: `explanation/transformations/testsuite_reader.py:10`
- **Message**: Cannot collect `TestSuiteReader` (has `__init__` constructor)
- **Status**: Known issue, documented in CLAUDE.md

### PytestUnknownMarkWarning
- **File**: `tests/test_quacq.py:230`
- **Message**: `pytest.mark.slow` is unregistered
- **Status**: Known issue, documented in CLAUDE.md

## Coverage Analysis

Critical path coverage verified:
- ConGen constraint encoding (bias constraints + assumptions)
- QuAcq task preparation (constraint mappings + negations)
- Negation computation via Tseitin variables
- Test case assumption generation (E+ and E-)
- NE (Negative Example) generation and negation
- CV fold re-prepare idempotency

## Performance Notes

- Full test suite completes in ~54 seconds
- Diagnosis tests represent 201+ test variants covering multiple solver modes
- No performance regressions detected

## Unresolved Questions

None. The refactoring is complete and behavior-preserving.

## Next Steps

1. Commit the fix with clear message referencing idempotent prepare semantics
2. Monitor CV evaluation pipelines that rely on re-prepare() calls
3. Update any documentation about model lifecycle if needed
