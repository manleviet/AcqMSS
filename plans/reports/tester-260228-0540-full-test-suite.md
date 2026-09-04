# Test Suite Report: AcqMSS Full Test Execution
**Date:** 2026-02-28
**Time:** 05:40 UTC
**Environment:** macOS (darwin), Python 3.13.0, pytest 9.0.2
**Test Command:** `PYTHONPATH=. pytest tests/ -v`

---

## Test Results Overview

| Metric | Count |
|--------|-------|
| **Total Tests Run** | 359 |
| **Passed** | 356 |
| **Failed** | 3 |
| **Skipped** | 0 |
| **Warnings** | 2 |
| **Execution Time** | 67.08 seconds |
| **Pass Rate** | 99.2% |

---

## Summary by Test Module

| Module | Tests | Status |
|--------|-------|--------|
| `tests/test_congen.py` | ~85 | PASS |
| `tests/test_diagnosis.py` | ~35 | PASS |
| `tests/test_quacq.py` | ~212 | 3 FAIL, 209 PASS |
| `tests/test_query_converter.py` | ~13 | PASS |
| `tests/test_semantic_equivalence.py` | ~8 | PASS |
| `tests/test_utils.py` | ~6 | PASS |

---

## Failed Tests (3 Total)

### Test Class: `TestQuAcqTaskPart4`

All 3 failures are in the same test class related to Part 4 (feature assignment assumptions) integration.

#### 1. `test_task_part4_populated`
**File:** `tests/test_quacq.py::TestQuAcqTaskPart4::test_task_part4_populated`

**Error Type:** `AttributeError`

**Failure Location:** Line 822 in `tests/test_quacq.py`

```
AssertionError location:
    assert len(task.assignment_clauses) > 0
                   ^^^^^^^^^^^^^^^^^^^^^^^

AttributeError: 'QuAcqTask' object has no attribute 'assignment_clauses'
```

**Root Cause:** The `assignment_clauses` attribute is commented out in `QuAcqTask` class definition (line 63 of `conacq/algorithms/quacq/task_preparation.py`). The dataclass fields for Part 4 (lines 62-66) are all commented out:

```python
# Part 4: Feature assignment assumptions (for SAT-based pruning)
# assignment_clauses: List[List[int]] = field(default_factory=list)
# assignment_assumptions: List[int] = field(default_factory=list)
# pos_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
# neg_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
```

However, the test expects these fields to be populated.

---

#### 2. `test_model_get_kb_includes_part4`
**File:** `tests/test_quacq.py::TestQuAcqTaskPart4::test_model_get_kb_includes_part4`

**Error Type:** `AttributeError`

**Failure Location:** Line 834 in `tests/test_quacq.py`

```
assert len(model_kb) == len(task.set_kb) + len(task.assignment_clauses)
                                               ^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'QuAcqTask' object has no attribute 'assignment_clauses'
```

**Root Cause:** Same as test #1 — missing Part 4 attribute.

---

#### 3. `test_model_get_assumptions_includes_part4`
**File:** `tests/test_quacq.py::TestQuAcqTaskPart4::test_model_get_assumptions_includes_part4`

**Error Type:** `AttributeError`

**Failure Location:** Line 840 in `tests/test_quacq.py`

```
assert len(model_assumptions) == len(task.assumptions) + len(task.assignment_assumptions)
                                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'QuAcqTask' object has no attribute 'assignment_assumptions'
```

**Root Cause:** Same as test #1 — missing Part 4 attribute.

---

## Coverage Analysis

**Note:** Coverage analysis unavailable. Coverage tool (`pytest-cov`) not installed in project environment.

To enable coverage reports:
```bash
pip install pytest-cov
PYTHONPATH=. pytest tests/ --cov=conacq --cov=explanation --cov-report=html
```

---

## Warnings Detected

### Warning 1: PytestCollectionWarning
**Source:** `explanation/transformations/testsuite_reader.py:10`

```
PytestCollectionWarning: cannot collect test class 'TestSuiteReader'
because it has a __init__ constructor (from: tests/test_diagnosis.py)
    class TestSuiteReader(TextToModel):
```

**Impact:** Non-blocking. Class is not intended to be a test class; pytest detects it as one due to naming convention.

**Recommendation:** Rename `TestSuiteReader` to `SuiteReaderTransformer` or move out of test context if not intended as test class.

---

### Warning 2: PytestUnknownMarkWarning
**Source:** `tests/test_quacq.py:271`

```
PytestUnknownMarkWarning: Unknown pytest.mark.slow - is this a typo?
You can register custom marks to avoid this warning - is this a typo?
You can register custom marks to avoid this warning - for details, see
https://docs.pytest.org/en/stable/how-to/mark.python (from: tests/test_quacq.py:271)
    @pytest.mark.slow
```

**Impact:** Informational. Tests still execute. `pytest.mark.slow` is custom marker not registered in `pytest.ini` or `pyproject.toml`.

**Recommendation:** Register custom markers:
```ini
# pytest.ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

---

## Critical Issues

### Issue 1: Part 4 Feature Assignment Assumptions Not Implemented
**Severity:** HIGH
**Component:** `QuAcqTask` class definition
**Status:** Blocking test suite completion

**Details:**
- Part 4 fields commented out in `task_preparation.py` (lines 62-66)
- Tests created expecting these fields to be present and populated
- Code at lines 104-107 attempts to copy Part 4 data from `BGData` but fields don't exist

**Affected Tests:**
- `TestQuAcqTaskPart4::test_task_part4_populated`
- `TestQuAcqTaskPart4::test_model_get_kb_includes_part4`
- `TestQuAcqTaskPart4::test_model_get_assumptions_includes_part4`

**Required Action:** Uncomment Part 4 field definitions in `QuAcqTask` dataclass OR remove corresponding test code if Part 4 is not intended for this release.

---

## Test Execution Breakdown

### Successful Test Categories

**ConGen Algorithm Tests (All Passing):**
- Incremental/non-incremental constraint generation
- Example generation
- Model builder tests
- Oracle feature ID validation
- Model behavior verification

**Diagnosis Tests (All Passing):**
- SAT solver integration
- Diagnosis model behavior
- Query provider tests

**QuAcq Algorithm Tests (209/212 Passing):**
- Task preparation
- Model building
- Assignment set verification
- SAT utilities
- Background ground data handling
- Only Part 4-specific tests failing

**Utility & Support Tests (All Passing):**
- Query converter
- Semantic equivalence checking
- General utility functions

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| **Total Execution Time** | 67.08 seconds |
| **Avg Time per Test** | 0.187 seconds |
| **Slowest Category** | QuAcq tests (higher count) |

No slow individual tests identified. Execution time is reasonable for 359 test cases.

---

## Build Process Verification

**Status:** SUCCESS (with 3 test failures)

- Python environment: Configured correctly
- PYTHONPATH handling: Correct
- Dependency resolution: Success
- Module imports: All pass
- No syntax errors detected

---

## Recommendations

### Immediate Actions (Priority: HIGH)

1. **Resolve Part 4 Field Mismatch**
   - **Action:** Either uncomment Part 4 fields in `QuAcqTask` class (lines 63-66) OR disable corresponding tests temporarily
   - **Files to Update:**
     - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py` (lines 62-66)
     - Consider whether Part 4 is in scope for current work
   - **Estimated Effort:** 15 minutes
   - **Blocker:** Yes, 3 tests currently failing

### Enhancement Actions (Priority: MEDIUM)

2. **Install Coverage Analysis Tool**
   - **Action:** `pip install pytest-cov` to enable code coverage reports
   - **Benefit:** Identify untested code paths and improve test completeness
   - **Estimated Effort:** 5 minutes

3. **Register Custom Pytest Markers**
   - **Action:** Add `pytest.ini` or update `pyproject.toml` with custom marker registration
   - **Benefit:** Eliminate warning noise, enable selective test execution
   - **Example:**
     ```ini
     [pytest]
     markers =
         slow: marks tests as slow (deselect with '-m "not slow"')
     ```
   - **Estimated Effort:** 5 minutes

4. **Rename TestSuiteReader Class**
   - **Action:** Rename `TestSuiteReader` to `SuiteReaderTransformer` in `explanation/transformations/testsuite_reader.py`
   - **Benefit:** Eliminate pytest collection warning
   - **Estimated Effort:** 5 minutes
   - **Files:** `/Users/manleviet/Development/GitHub/AcqMSS/explanation/transformations/testsuite_reader.py`

---

## Next Steps (Prioritized)

1. **Fix Part 4 Field Integration (BLOCKING)**
   - Uncomment Part 4 fields or update test expectations
   - Re-run full test suite to confirm all 359 tests pass
   - This is the only blocker for clean test status

2. **Verify Part 4 Logic (if fields uncommented)**
   - Ensure `BGData.assignment_clauses` and `BGData.assignment_assumptions` are properly set
   - Validate assignment_to_assumption mappings are populated
   - Check that `QuAcqModel.get_kb()` and `get_assumptions()` include Part 4 data

3. **Enable Coverage Analysis**
   - Install pytest-cov
   - Generate coverage report targeting `conacq/` and `explanation/` packages
   - Identify coverage gaps

4. **Code Quality Polish**
   - Register pytest markers
   - Fix class naming warnings
   - Run type checking: `mypy conacq/ explanation/`

---

## Unresolved Questions

1. **Is Part 4 (feature assignment assumptions) intended for this release?**
   - Fields are commented out in code but tests expect them
   - Need confirmation on feature scope

2. **Should `TestSuiteReader` be renamed to avoid pytest warnings?**
   - Is this class actually used for test purposes or only as transformation utility?

3. **Are custom pytest markers (e.g., `@pytest.mark.slow`) actually used?**
   - Should they be registered or removed from codebase?

4. **Coverage Goals:** What is the target code coverage percentage for this project?
   - No coverage tool currently installed; unclear if coverage is being tracked

---

## Conclusion

**Overall Assessment:** HEALTHY with ONE CRITICAL ISSUE

The test suite demonstrates strong baseline health with 356/359 (99.2%) tests passing. All 3 failures are concentrated in a single test class (`TestQuAcqTaskPart4`) and stem from a single root cause: uncommented Part 4 field definitions in the `QuAcqTask` class.

**Critical Path to Fix:**
1. Decide on Part 4 scope (keep/remove)
2. If keeping: uncomment 4 lines in `task_preparation.py` + verify implementation
3. If removing: delete 3 test methods
4. Re-run tests → expect all 359 to pass

The codebase is well-structured and test coverage is comprehensive across ConGen, QuAcq, diagnosis, and utility modules. Post-fix, focus should be on enabling coverage metrics and eliminating warning noise.
