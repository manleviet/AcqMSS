# Test Suite Report: Full Test Execution

**Date:** 2026-02-28 07:51 UTC
**Test Run:** Full suite `PYTHONPATH=. pytest tests/ -v`
**Duration:** ~0.36s (collection phase only)
**Status:** CRITICAL FAILURE - Build Break

---

## Test Results Overview

| Metric | Value |
|--------|-------|
| **Tests Collected** | 0 / 242 |
| **Tests Passed** | 0 |
| **Tests Failed** | 0 |
| **Tests Skipped** | 0 |
| **Collection Errors** | 6 |
| **Warnings** | 1 |

---

## Critical Issues

### BLOCKING: ImportError in Module Imports Chain

**Root Cause:** `findc.py` line 17 attempts to import non-existent function from `sat_utils`

```python
# findc.py line 17
from .sat_utils import get_constraints_with_scope
```

**Problem:** `get_constraints_with_scope` does NOT exist in `sat_utils.py`

**Actual Location:** Method on `QuAcqModel` class (quacq_model.py:184-204)

**Evidence:**
- `sat_utils.py` line 1-99: Contains utility functions `config_to_assumptions()`, `partial_config_to_assumptions()`, `get_constraint_vars()`, `violates_clauses()`, `prune_rejecting()`, `get_kb_clauses()` — NO `get_constraints_with_scope()`
- `quacq_model.py` line 184-204: Method `get_constraints_with_scope(self, scope, remaining_bias)` exists but NOT exported as standalone function
- `findc.py` line 65-66: Called with 4 args: `get_constraints_with_scope(scope, remaining_bias, constraint_clauses, id_to_feature)` — signature mismatch

**Impact:** ALL 6 test files blocked at import time (collection fails before any tests run)

```
ERROR tests/test_bias_module.py
ERROR tests/test_bias_module_1.py
ERROR tests/test_congen.py
ERROR tests/test_evaluation.py
ERROR tests/test_quacq.py
ERROR tests/test_semantic_equivalence.py
```

---

## Import Chain Trace

Every test file fails at the same point:

```
test_file.py (import conacq)
  → conacq/__init__.py (import algorithms)
    → conacq/algorithms/__init__.py (import acqmss)
      → conacq/algorithms/acqmss/__init__.py (import quacq)
        → conacq/algorithms/quacq/__init__.py (import quacq)
          → conacq/algorithms/quacq/quacq.py (import findc)
            → conacq/algorithms/quacq/findc.py LINE 17
              → ImportError: cannot import name 'get_constraints_with_scope'
```

---

## Warnings

### PytestCollectionWarning (Non-blocking)

**File:** `explanation/transformations/testsuite_reader.py:10`

```
cannot collect test class 'TestSuiteReader' because it has a __init__ constructor
```

**Note:** This is a known issue per CLAUDE.md. Class designed as utility, not test class. Safe to ignore.

---

## Code Analysis

### Expected vs Actual

**In `findc.py` (line 65-66):**
```python
candidates = get_constraints_with_scope(
    scope, remaining_bias, constraint_clauses, id_to_feature)
```

**Signature Expected:** `(scope, remaining_bias, constraint_clauses, id_to_feature) → List[int]`

**Actual in QuAcqModel (line 184-204):**
```python
def get_constraints_with_scope(self, scope: set, remaining_bias: set) -> List[int]:
```

**Signature Actual:** `(self, scope, remaining_bias) → List[int]` (requires `self`, doesn't take `constraint_clauses` or `id_to_feature`)

---

## Affected Test Coverage

**Cannot assess** — 0 tests executed. The following test files are affected:

1. **test_bias_module.py** — Bias generator tests
2. **test_bias_module_1.py** — Bias configuration tests
3. **test_congen.py** — ConGen algorithm tests
4. **test_evaluation.py** — Evaluation module tests
5. **test_quacq.py** — QuAcq algorithm tests (includes `get_constraints_with_scope` unit tests!)
6. **test_semantic_equivalence.py** — Semantic equivalence checker tests

**Tests that CAN run** (9 unaffected):
- test_diagnosis.py
- test_oracle.py
- test_oracle_models.py
- test_utils.py
- And others not importing via conacq main package

---

## Summary

**Build Status:** BROKEN
**Blocking Issue:** Missing function export / incorrect import
**Quick Fix Category:** Import statement + function signature alignment
**Scope:** Single module pair (`findc.py` ↔ `sat_utils.py` or `quacq_model.py`)
**Data Loss Risk:** None — code issue, not data

---

## Recommended Action

1. **Verify intent:** Confirm whether `get_constraints_with_scope` should be:
   - Standalone function in `sat_utils.py` (extracted from QuAcqModel)
   - Method call on `self.model.get_constraints_with_scope()` in FindC

2. **Align signatures:** Update either:
   - `findc.py` import + call site, OR
   - `sat_utils.py` to include exported function with correct signature

3. **Rerun tests:** After fix, full test suite should execute

---

## Unresolved Questions

1. Should `get_constraints_with_scope` be extracted to `sat_utils.py` as a pure function, or should `findc.py` use the method on `self.model`?
2. What parameters should the function accept? Current call site passes 4 args but QuAcqModel method takes only 2 (plus self).
