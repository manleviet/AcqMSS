# Test Report — ConGenModelBuilder Auto-Prepare

**Date:** 2026-02-18
**Scope:** `tests/test_congen.py` (18 tests) + full suite (309 tests)
**Trigger:** New `TestConGenModelBuilder` tests for auto-prepare feature

---

## Test Results Overview

### `tests/test_congen.py` (target file)

| Status | Count |
|--------|-------|
| Passed | 18 |
| Failed | 0 |
| Skipped | 0 |

**Time:** 3.14 s

### Full Suite (`tests/`)

| Status | Count |
|--------|-------|
| Passed | 307 |
| Failed | 2 |
| Skipped | 0 |
| Warnings | 2 |

**Time:** 52.99 s

---

## New TestConGenModelBuilder Tests (5)

| Test | Result |
|------|--------|
| `test_auto_prepare_from_file` | PASS |
| `test_auto_prepare_from_data` | PASS |
| `test_build_without_oracle_returns_unprepared` | PASS (required fix) |
| `test_cv_re_prepare` | PASS |
| `test_last_call_wins` | PASS |

---

## Fix Applied

**File:** `conacq/algorithms/acqmss/congen_model.py`

**Problem:** `ConGenModel.task` property raised `RuntimeError("Call prepare() first")` when `_task is None`, but `test_build_without_oracle_returns_unprepared` asserts `model.task is None`.

**Fix:** Changed return type from `ConGenTask` → `Optional[ConGenTask]` and removed the RuntimeError guard — property now returns `None` when unprepared.

```python
# Before
@property
def task(self) -> ConGenTask:
    """Get prepared task. Call prepare() first."""
    if self._task is None:
        raise RuntimeError("Call prepare() first")
    return self._task

# After
@property
def task(self) -> Optional[ConGenTask]:
    """Get prepared task, or None if prepare() has not been called."""
    return self._task
```

**Impact:** Convenience getters (`get_kb`, `get_assumptions`, `get_c`, etc.) delegate to `self.task` — they will now raise `AttributeError` on `None` instead of `RuntimeError`. Acceptable since all callers follow the prepare-before-use contract.

---

## Pre-existing Failures (2, unrelated)

**File:** `tests/test_evaluation.py`

| Test | Error |
|------|-------|
| `TestIntegration::test_evaluate_real_fm_7` | `FileNotFoundError: data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json` |
| `TestIntegration::test_accuracy_with_real_examples` | Same missing file |

These tests lack a `pytest.skip` guard for missing result files. Pre-existing before this change.

---

## Warnings

- `PytestCollectionWarning` — `TestSuiteReader` has `__init__` (known, in `explanation/transformations/testsuite_reader.py`)
- `PytestUnknownMarkWarning` — `pytest.mark.slow` unregistered (known)

---

## Recommendations

1. Add `pytest.skip` guard to `test_evaluate_real_fm_7` and `test_accuracy_with_real_examples` when `RESULT_PATH` does not exist.
2. Consider adding `pytest.raises(AttributeError)` or explicit `is_prepared` predicate on `ConGenModel` if callers need to distinguish unprepared vs. error states more explicitly.

---

## Unresolved Questions

- Should `description_provider` property also return `Optional` instead of raising (symmetric with `task`)? Currently still raises `RuntimeError`.
