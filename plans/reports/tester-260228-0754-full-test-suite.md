# Test Suite Report — 2026-02-28 07:54

## Summary

**Status:** BLOCKED — Test collection failed, 0 tests executed

**Critical Issue:** Import error in `tests/test_quacq.py` prevents test collection entirely.

---

## Test Results

- **Total Tests Collected:** 0 / 294 (collection failed)
- **Passed:** 0
- **Failed:** 0
- **Errors:** 1 (BLOCKING)
- **Skipped:** 0
- **Warnings:** 1 (non-blocking)

---

## Critical Issues

### 1. ImportError in test_quacq.py (BLOCKING)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py`

**Error:**
```
ImportError: cannot import name 'get_constraints_with_scope' from 'conacq.algorithms.quacq.quacq_model'
```

**Root Cause:**

Latest commit `5d4eee8` ("refactor(quacq): centralize get_constraints_with_scope in QuAcqModel...") moved `get_constraints_with_scope` from a module-level function to an instance method on `QuAcqModel` class.

**Evidence:**
- Commit `5d4eee8` changed the function to a method (line 185 of `quacq_model.py`)
- Test file still imports as standalone function (line 19 of `test_quacq.py`)
- Test methods `test_get_constraints_with_scope_exact()` and `test_get_constraints_with_scope_subset()` call it with wrong signature

**Signature Mismatch:**
- Test expects: `get_constraints_with_scope(scope, remaining_bias, constraint_clauses, id_to_feature)`
- Method signature: `get_constraints_with_scope(self, scope, remaining_bias)` — only takes 2 params, accesses `self._require_task()` internally

**Impact:** Test suite cannot run. All 294 tests blocked.

---

## Non-Critical Warnings

**PytestCollectionWarning:** `TestSuiteReader` has `__init__` constructor
- File: `explanation/transformations/testsuite_reader.py:10`
- Impact: Pytest can't auto-collect (has custom constructor) — minor, existing issue
- Status: Known and acknowledged in CLAUDE.md

---

## Next Steps (Required to Unblock)

1. **Remove invalid import** from `tests/test_quacq.py` line 19
2. **Update test methods** `test_get_constraints_with_scope_exact` and `test_get_constraints_with_scope_subset` to:
   - Create QuAcqModel instance
   - Call `.get_constraints_with_scope(scope, remaining_bias)` on instance
   - Adjust test data setup to match new method signature (no longer takes `constraint_clauses` or `id_to_feature` as params)
3. **Re-run tests** to validate fix

---

## Unresolved Questions

- Should `get_constraints_with_scope` be re-exported as standalone function for backward compatibility, or should tests be updated to use instance method?
