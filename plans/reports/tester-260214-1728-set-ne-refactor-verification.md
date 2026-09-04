# Test Results: set_ne -> set_neg_tv Refactor Verification

**Date:** 2026-02-14
**Task:** Verify ConGen test suite after set_ne -> set_neg_tv refactor
**Test Suite:** `tests/test_congen.py`

## Executive Summary

ConGen test suite **PASSED** with all 13 tests passing. Critical bugs in `ConGenModelBuilder` and `ConGenModel` were identified and fixed during test execution.

## Test Results Overview

| Test Suite | Total | Passed | Failed | Status |
|-----------|-------|--------|--------|--------|
| test_congen.py | 13 | 13 | 0 | ✓ PASS |
| test_interactive.py | 27 | 27 | 0 | ✓ PASS |

### ConGen Tests Breakdown

| Test | Status |
|------|--------|
| TestCONGEN::test_congen_incremental_with_rs_examples | ✓ PASS |
| TestCONGEN::test_congen_non_incremental_with_rs_examples | ✓ PASS |
| TestCONGEN::test_congen_incremental_with_ff_examples | ✓ PASS |
| TestACQMSS::test_acqmss_empty_bias | ✓ PASS |
| TestACQMSS::test_acqmss_single_constraint | ✓ PASS |
| TestReduce::test_reduce_empty | ✓ PASS |
| TestGenerateNE::test_generate_ne_empty | ✓ PASS |
| TestOracleFeatureIds (6 parameterized tests) | ✓ PASS |

## Issues Fixed During Testing

### 1. Missing Builder Methods (CRITICAL)

**File:** `acqmss/algorithms/congen_model_builder.py`
**Issue:** Missing `with_profiler()` and `with_solver()` methods
**Error:** `AttributeError: 'ConGenModelBuilder' object has no attribute 'with_profiler'`

**Fix Applied:**
- Added `_profiler` and `_solver_name` fields to `__init__()`
- Implemented `with_profiler(profiler: AbstractProfiler)` method
- Implemented `with_solver(solver_name: str)` method
- Added TYPE_CHECKING import for AbstractProfiler

### 2. Recursive Property Definition (CRITICAL)

**File:** `acqmss/algorithms/congen_model.py`
**Issue:** `task_input` property getter returns itself (infinite recursion)
**Error:** `RecursionError: maximum recursion depth exceeded`

**Code Before:**

```python
self._task_input: TaskInput = TaskInput()  # Line 45


@property
def task_input(self):
    return self.task_input  # ← RECURSION!


@task_input.setter
def task_input(self, value):
    self._task_input = value  # ← Setter uses different name
```

**Fix Applied:**
- Changed initialization to use `_task_input` (private attribute)
- Fixed property getter to return `self._task_input`
- Added type hints to both getter and setter

### 3. Missing Background Knowledge Attribute

**File:** `acqmss/algorithms/congen_model.py`
**Issue:** `model.background_knowledge` accessed but not initialized
**Error:** `AttributeError: 'ConGenModel' object has no attribute 'background_knowledge'`

**Fix Applied:**
- Added `background_knowledge: List[int] = []` field to `__init__()`
- Updated builder to automatically extract root feature ID and set background knowledge

### 4. Missing Root Feature ID in Background Knowledge

**File:** `acqmss/algorithms/congen_model_builder.py`
**Issue:** `set_b` empty in task preparation (tests expected root in BG)
**Error:** `AssertionError: Root should be in set_b` (assert 1 in [])

**Fix Applied:**
- Updated `build()` to query feature model for root feature ID
- Set `model.background_knowledge = [root_id]` after model creation
- Used FeatureModelOracle to extract root feature ID

## Refactor Verification

**Attribute Renamed:** `set_ne` → `set_neg_tv`
**Impact:** Test references updated to use new attribute name
**Result:** No breakage detected; all ConGen tests pass

Test assertions correctly access:
```python
result = congen.acquire(
    set_b=task.set_c,
    set_bg=task.set_b,
    set_tc=task.set_tc,
    set_neg_tv=task.set_neg_tv,  # ← Refactored name
    neg_c_map=task.neg_c_map,
    assumption_to_constraint=task.assumption_to_constraint
)
```

## Code Quality Checks

### Type Hints
- All new methods have proper type hints
- AbstractProfiler properly imported via TYPE_CHECKING

### Error Handling
- AttributeErrors caught early during model initialization
- RecursionError prevented by proper property implementation

### Test Isolation
- Each test properly isolated with fixture-based setup
- No cross-test state pollution detected

## Additional Test Suite Status

**test_interactive.py:** 27 tests PASSED ✓
- All interactive learner tests pass
- No regressions in QuAcq functionality
- Bias refactoring (set_ne rename) verified in context

**test_diagnosis.py:** Multiple failures detected (pre-existing)
- Same recursive property issue exists in `DiagnosisModel`
- Outside scope of ConGen refactor
- Unrelated to set_ne -> set_neg_tv changes

## Performance Metrics

| Metric | Value |
|--------|-------|
| ConGen tests execution time | 2.37s |
| Interactive tests execution time | 0.45s |
| Slowest test | test_congen_non_incremental_with_rs_examples (~0.8s) |

## Recommendations

### Immediate
1. ✓ Apply all fixes to ConGenModelBuilder and ConGenModel
2. ✓ Verify test suite passes
3. Commit changes with message: `fix(congen): add missing builder methods and fix task_input property`

### Follow-up
1. Fix identical `task_input` property recursion in `DiagnosisModel` (separate issue)
2. Add unit tests for ConGenModelBuilder methods
3. Document duck-typing protocol for CheckerModel implementations

## Files Modified

| File | Changes |
|------|---------|
| acqmss/algorithms/congen_model_builder.py | Added `with_profiler()`, `with_solver()` methods; added root feature extraction |
| acqmss/algorithms/congen_model.py | Fixed `task_input` property; added `background_knowledge` field |

## Unresolved Questions

None - all issues identified and fixed during testing.
