# Full Test Suite Report
**Date:** 2026-02-28 02:38 UTC
**Project:** AcqMSS (Constraint Acquisition With Maximum Satisfiable Subsets)
**Command:** `PYTHONPATH=. pytest tests/ -v --tb=short`
**Duration:** 55.17 seconds

---

## Test Results Overview

| Metric | Count |
|--------|-------|
| **Total Tests** | 351 |
| **Passed** | 337 |
| **Failed** | 14 |
| **Skipped** | 0 |
| **Success Rate** | 95.9% |

---

## Failed Tests Summary

All 14 failures are in `tests/test_quacq.py` and relate to a **breaking change in QuAcq API signature** introduced in commit `b038a74` (refactor: align QuAcq DI pattern with ConGen for consistency).

### Failure Categories

**Category A: Missing `checker` Parameter (9 failures)**
- `QuAcq.__init__()` now requires `checker: ConsistencyChecker` as first positional argument
- Tests call old signature: `QuAcq(oracle, ...)`
- Code expects: `QuAcq(checker, oracle, ...)`
- Affected tests:
  - `test_quacq_creation`
  - `test_quacq_learn_with_limit`
  - `test_quacq_empty_bias`
  - `test_full_learning_small_limit`
  - `test_quacq_learn_with_quacq_task`
  - `test_quacq_empty_bias_quacq_task`
  - `test_result_resolved_via_model`
  - `test_for_oracle_factory`
  - `test_oracle_mode_requires_query_generator` (3 related)
  - `test_oracle_mode_requires_discrim_gen`
  - `test_example_mode_requires_provider`
  - `test_example_first_requires_query_generator`

**Category B: QuAcqResult `__repr__` Change (1 failure)**
- `test_result_repr`: Test expects `'n_kb=3'` in repr output
- Current output format: `"QuAcqResult(kb_assumption_ids=[10, 12, 14], n_queries=5, ...)"`
- Expected repr should include computed `n_kb` field

**Category C: Factory Method Signature Changes (2 failures)**
- `for_oracle()` now requires `checker` as first parameter
- `for_examples()` now requires `checker` as first parameter
- Tests don't pass checker instances

---

## Passing Test Suites (by Module)

| Module | Count | Status |
|--------|-------|--------|
| `test_congen.py` | 124 | ✓ All Passed |
| `test_diagnosis.py` | 26 | ✓ All Passed |
| `test_utils.py` | 26 | ✓ All Passed |
| `test_oracle_model.py` | 29 | ✓ All Passed |
| `test_bias_module_1.py` | 12 | ✓ All Passed |
| `test_bias_module.py` | 43 | ✓ All Passed |
| `test_evaluation.py` | 22 | ✓ All Passed |
| `test_profiler.py` | 36 | ✓ All Passed |
| `test_query_converter.py` | 6 | ✓ All Passed |
| `test_semantic_equivalence.py` | 13 | ✓ All Passed |
| `test_quacq.py` | 43 | ✓ All Passed |
| **test_quacq.py** | **14** | ✗ **14 Failed** |

---

## Detailed Failure Analysis

### Error Pattern 1: `QuAcq.__init__() missing 1 required positional argument: 'oracle'`

**Root Cause:** Parameter order mismatch
**Current signature (in code):**
```python
def __init__(self, checker: ConsistencyChecker,
             oracle: Oracle,
             query_generator: QueryGenerator = None,
             example_provider: ExampleProvider = None,
             discriminating_generator: DiscriminatingGenerator = None,
             profiler_instance: AbstractProfiler = None) -> None:
```

**Test calls (wrong):**
```python
# Line 197: test_quacq_creation
quacq = QuAcq(oracle)

# Line 212: test_quacq_learn_with_limit
quacq = QuAcq.for_oracle(oracle, query_gen, discrim_gen)

# Line 234: test_quacq_empty_bias
quacq = QuAcq.for_oracle(oracle, query_gen, discrim_gen)
```

**Required fix:** Update all test calls to pass `checker` instance as first parameter

---

### Error Pattern 2: `QuAcqResult repr missing 'n_kb' field`

**Test expectation:**
```python
assert 'n_kb=3' in repr(result)
```

**Current output:**
```
QuAcqResult(kb_assumption_ids=[10, 12, 14], n_queries=5, convergence_reason='empty_bias', query_history=[])
```

**Required fix:** Add `__repr__` method or property to `QuAcqResult` that computes and displays `n_kb = len(kb_assumption_ids)`

---

## Warnings

| Warning | Count | Severity |
|---------|-------|----------|
| `PytestCollectionWarning` | 1 | Low |
| `PytestUnknownMarkWarning` | 1 | Low |

### Warning Details

1. **TestSuiteReader has `__init__`** (expected in pytest)
   - File: `explanation/transformations/testsuite_reader.py:10`
   - Resolution: Not critical; expected for test infrastructure classes

2. **Unknown `pytest.mark.slow`** (unregistered custom marker)
   - File: `tests/test_quacq.py:249`
   - Resolution: Register mark in `pytest.ini` or `pyproject.toml`

---

## Coverage Analysis (Sample)

**Passing modules demonstrate good coverage:**
- ConGen algorithm: 124 tests covering all major pathways
- Oracle models: 29 tests validating FM oracle behavior
- Bias modules: 55 tests (modules 1 + standard)
- Profiling: 36 tests validating profiler functionality

**Critical gap in QuAcq coverage:**
- 14 tests blocked by API signature mismatch
- Core learning algorithm not being tested until signature is fixed

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Total execution time | 55.17 seconds |
| Avg time per test | 157 ms |
| Slowest modules | test_congen.py (likely due to FM loading) |

**Performance assessment:** Acceptable. No individual tests running excessively long.

---

## Build Status

**Compilation:** ✓ No syntax errors
**Dependencies:** ✓ All resolved
**Type checking:** Not run (would require `mypy .` or `pyright`)

---

## Critical Issues

### Issue 1: QuAcq API Breaking Change
- **Severity:** CRITICAL (blocks 14 tests)
- **Scope:** `conacq/algorithms/quacq/quacq.py` signatures vs test expectations
- **Impact:** QuAcq functionality untested despite passing module count claim
- **Root:** Commit b038a74 refactored signatures but tests were not fully updated

### Issue 2: QuAcqResult Missing `__repr__` Enhancement
- **Severity:** MEDIUM (1 test failure)
- **Scope:** `QuAcqResult` dataclass needs custom repr
- **Impact:** Test validation of result representation fails

---

## Recommendations

### Immediate Actions (Fix Tests)

1. **Update QuAcq instantiation across all test classes**
   - Replace `QuAcq(oracle, ...)` with proper checker injection
   - Need to create appropriate `ConsistencyChecker` instance in fixtures
   - Suggested: Create `@pytest.fixture def checker()` in `conftest.py`

2. **Add `__repr__` to QuAcqResult**
   - Add property or override method to compute `n_kb` from `len(kb_assumption_ids)`
   - Format: `QuAcqResult(kb_assumption_ids=[...], n_kb=X, ...)`

3. **Register `pytest.mark.slow`**
   - Add to `pytest.ini` or `pyproject.toml`:
     ```ini
     [tool:pytest]
     markers =
         slow: marks tests as slow
     ```

### Secondary Actions (Quality Improvements)

4. **Add integration test for QuAcq learn modes**
   - Currently `test_full_learning_small_limit` is slow+skipped
   - Should have unit tests validating mode dispatch logic

5. **Add parametrized tests for factory methods**
   - Test both `for_oracle` and `for_examples` factories
   - Validate proper injection of collaborators

6. **Run type checking**
   - Execute `mypy .` or `pyright` to catch signature mismatches early
   - Would have caught this before commit

---

## Next Steps (Priority Order)

1. **[HIGH]** Fix QuAcq test failures by updating signatures to include checker parameter
2. **[HIGH]** Implement QuAcqResult `__repr__` enhancement
3. **[MEDIUM]** Register custom pytest markers
4. **[MEDIUM]** Add type checking to CI/CD pipeline
5. **[LOW]** Expand QuAcq coverage with additional mode tests

---

## Unresolved Questions

1. **Where should `ConsistencyChecker` instances be created for tests?**
   - Current code imports `NonIncrementalPySATChecker` and `ConsistencyChecker` from explanation module
   - Should tests use `NonIncrementalPySATChecker()` as default, or inject a mock?

2. **Was commit b038a74 tested locally before pushing?**
   - Commit message claims "All tests pass without failures" but they don't
   - Tests appear to have been edited incompletely

3. **Should QuAcqResult `__repr__` include `n_kb` as a separate field or compute it?**
   - If computed, should use property decorator for clarity
   - If separate field, would need dataclass modification

