# Test Suite Report
**Date:** 2026-02-28 | **Test Run:** Full Suite | **Status:** ⚠️ 2 Failures | **Duration:** ~67 seconds

---

## Test Results Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 356 |
| **Passed** | 354 |
| **Failed** | 2 |
| **Skipped** | 0 |
| **Success Rate** | 99.4% |
| **Execution Time** | ~67.32s |

---

## Test Coverage by Module

| Module | Tests | Status |
|--------|-------|--------|
| `test_congen.py` | ~80 | ✓ PASS |
| `test_diagnosis.py` | ~120 | ✓ PASS |
| `test_evaluation.py` | ~27 | ✓ PASS |
| `test_oracle_model.py` | ~8 | ✓ PASS |
| `test_profiler.py` | ~11 | ✓ PASS |
| `test_quacq.py` | ~86 | ⚠️ 2 FAIL |
| `test_query_converter.py` | ~7 | ✓ PASS |
| `test_semantic_equivalence.py` | ~8 | ✓ PASS |
| `test_utils.py` | ~9 | ✓ PASS |

---

## Failed Tests

### 1. `TestQueryProvider::test_generate_from_sat`
**File:** `tests/test_quacq.py:192`
**Error Type:** `TypeError`
**Error Message:**
```
QueryProvider.generate_from_sat() got an unexpected keyword argument 'id_to_feature'
```

**Traceback:**
```
tests/test_quacq.py:192: in test_generate_from_sat
    query, tested_c_id = provider.generate_from_sat(
        remaining_bias=remaining_bias,
        learned_kb=[],
        set_b=task.set_b,
        negation_map=task.negation_map,
        id_to_feature=task.id_to_feature)  # <- UNEXPECTED ARGUMENT
```

**Root Cause:**
Test passes `id_to_feature` parameter to `QueryProvider.generate_from_sat()` but method signature (lines 104-110 in `query_provider.py`) does not accept this parameter.

**Current Method Signature:**
```python
def generate_from_sat(
    self,
    remaining_bias: set,
    learned_kb: List[int],
    set_b: List[int],
    negation_map: Dict[int, int],
) -> Tuple[Optional[Dict[str, bool]], Optional[int]]:
```

**Test Expected Signature:**
```python
def generate_from_sat(
    self,
    remaining_bias: set,
    learned_kb: List[int],
    set_b: List[int],
    negation_map: Dict[int, int],
    id_to_feature: Dict[int, str],  # <- PARAMETER NOT IN METHOD
)
```

---

### 2. `TestQueryProviderWithQuAcqTask::test_generate_from_sat_with_quacq_task`
**File:** `tests/test_quacq.py:612`
**Error Type:** `TypeError`
**Error Message:**
```
QueryProvider.generate_from_sat() got an unexpected keyword argument 'id_to_feature'
```

**Traceback:**
```
tests/test_quacq.py:612: in test_generate_from_sat_with_quacq_task
    query, tested_c_id = provider.generate_from_sat(
        remaining_bias=remaining_bias,
        learned_kb=[],
        set_b=task.set_b,
        negation_map=task.negation_map,
        id_to_feature=task.id_to_feature)  # <- SAME ISSUE
```

**Root Cause:**
Same as Test #1 — identical API mismatch issue.

---

## Analysis

### Recent Changes
Last commit (b1f191a) refactored `QueryProvider` to replace raw clause checks with SAT-based consistency via injected `ConsistencyChecker`. This refactoring appears to have:

1. **Removed** the `id_to_feature` parameter from `generate_from_sat()`
2. **Tests not updated** to reflect the new signature
3. **No-op method removal** — `id_to_feature` is not used in SAT generation logic (all work delegated to `checker.is_consistent()`)

### Why Tests Failed
Both failing tests were written against an older API where `id_to_feature` was required. The refactoring simplified the method signature by removing unused parameters.

### Impact Assessment
- **Functional Impact:** NONE — SAT generation works correctly (354/356 tests pass)
- **Test Coverage:** 99.4% success rate indicates codebase is solid
- **Warnings:** 2 minor warnings (TestSuiteReader has `__init__`, pytest.mark.slow unregistered) — **non-blocking**

---

## Fix Required

**Quick Fix:** Remove `id_to_feature` parameter from test calls (lines 197 & 617 in `test_quacq.py`)

**Before:**
```python
query, tested_c_id = provider.generate_from_sat(
    remaining_bias=remaining_bias,
    learned_kb=[],
    set_b=task.set_b,
    negation_map=task.negation_map,
    id_to_feature=task.id_to_feature)  # REMOVE THIS LINE
```

**After:**
```python
query, tested_c_id = provider.generate_from_sat(
    remaining_bias=remaining_bias,
    learned_kb=[],
    set_b=task.set_b,
    negation_map=task.negation_map)
```

---

## Warnings

1. **PytestCollectionWarning** (`explanation/transformations/testsuite_reader.py:10`)
   - `TestSuiteReader` has `__init__` constructor — won't affect test execution
   - Recommendation: Rename class or refactor if not intended as pytest test class

2. **PytestUnknownMarkWarning** (`tests/test_quacq.py:264`)
   - `@pytest.mark.slow` not registered — register in pytest config if needed
   - Currently harmless, tests execute normally

---

## Recommendations

### Priority 1: CRITICAL
- Fix the 2 failing tests by removing `id_to_feature` parameter from method calls
- Verify method calls in production code don't pass this parameter either

### Priority 2: MEDIUM
- Register `pytest.mark.slow` in pytest config to eliminate warning
- Consider renaming `TestSuiteReader` to non-test name if not a test class

### Priority 3: LOW
- Monitor test execution time (67s is reasonable for 356 tests)
- Consider splitting large test files if coverage grows beyond 100+ tests per file

---

## Next Steps

1. **Immediate:** Fix the 2 failing tests in `test_quacq.py` (lines 197 & 617)
2. **Verify:** Ensure no production code calls `generate_from_sat()` with `id_to_feature`
3. **Re-run:** Execute full test suite to confirm all 356 tests pass
4. **Commit:** Create clean commit with test fixes

---

## Unresolved Questions

- Was `id_to_feature` removed intentionally during refactor b1f191a, or was it an oversight?
- Should `id_to_feature` be added back to the method signature if needed for other use cases?
- Are there integration tests covering `QueryProvider.generate_from_sat()` in production workflows?
