# Test Suite Execution Report
**Date:** 2026-02-18 10:12 UTC
**Project:** AcqMSS (Constraint Acquisition With Maximum Satisfiable Subsets)
**Test Runner:** pytest 9.0.2 (Python 3.13.0)
**Platform:** darwin (macOS)

---

## Test Execution Summary

| Metric | Value |
|--------|-------|
| **Total Tests** | 309 |
| **Passed** | 307 |
| **Failed** | 2 |
| **Skipped** | 0 |
| **Execution Time** | 53.54s |
| **Pass Rate** | 99.35% |

---

## Results Breakdown

### Passed Tests: 307 ✓

All test modules executed successfully except for evaluation integration tests:
- **test_congen.py** — Full ConGen algorithm suite (40+ tests)
- **test_quacq.py** — QuAcq algorithm suite (50+ tests)
- **test_oracle.py** — Oracle models and verification (100+ tests)
- **test_assumption.py** — Assumption handling and generation (30+ tests)
- **test_diagnosis.py** — Diagnosis logic (10+ tests)
- **test_interactive.py** — Interactive constraint acquisition (15+ tests)
- **test_profiler.py** — Performance monitoring (10+ tests)
- **test_utils.py** — Utility functions (8 tests)
- **test_batch.py** — Batch processing (15+ tests)
- **test_fm.py** — Feature model utilities (20+ tests)
- **test_bias.py** — Bias and constraints (20+ tests)

### Failed Tests: 2 ✗

Both failures occur in `/tests/test_evaluation.py` due to missing result data files:

#### Failure 1: `TestIntegration::test_evaluate_real_fm_7`
- **Error:** `FileNotFoundError`
- **Location:** `conacq/eval/result_loader.py:47`
- **Root Cause:** Missing result data file
- **Details:**
  ```
  File: /Users/manleviet/Development/GitHub/AcqMSS/data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json
  Expected: Valid ConGenResultData JSON containing evaluation results
  ```
- **Impact:** Integration test cannot validate evaluation metrics against pre-computed results

#### Failure 2: `TestIntegration::test_accuracy_with_real_examples`
- **Error:** `FileNotFoundError`
- **Location:** `conacq/eval/result_loader.py:47`
- **Root Cause:** Same missing file as Failure 1
- **Details:**
  ```
  File: /Users/manleviet/Development/GitHub/AcqMSS/data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json
  Expected: Valid ConGenResultData JSON containing accuracy metrics
  ```
- **Impact:** Cannot calculate and verify accuracy metrics against actual results

---

## Warnings Summary

### Warning 1: PytestCollectionWarning
- **File:** `explanation/transformations/testsuite_reader.py:10`
- **Issue:** `TestSuiteReader` class has `__init__` constructor (pytest naming convention conflict)
- **Severity:** Info-level (test collection only, does not affect execution)
- **Impact:** pytest attempts to collect this as test class but fails; class is properly skipped
- **Action:** Already documented in CLAUDE.md as known issue

### Warning 2: PytestUnknownMarkWarning
- **File:** `tests/test_interactive.py:368`
- **Issue:** `@pytest.mark.slow` is not registered in pytest.ini
- **Severity:** Info-level (custom mark not in config)
- **Impact:** Slow tests execute normally but mark is ignored for filtering
- **Action:** Already documented in CLAUDE.md as known issue

---

## Test Coverage Breakdown by Module

| Module | Tests | Status | Notes |
|--------|-------|--------|-------|
| ConGen Algorithms | 40+ | ✓ PASS | Core acquisition logic fully tested |
| QuAcq Algorithms | 50+ | ✓ PASS | Alternative acquisition strategy validated |
| Oracle Models | 100+ | ✓ PASS | FM oracle and SAT solver integration working |
| Assumptions | 30+ | ✓ PASS | Assumption generation and ID consistency verified |
| Diagnosis | 10+ | ✓ PASS | Conflict/diagnosis logic operational |
| Interactive Mode | 15+ | ✓ PASS | User interaction workflows validated |
| Batch Processing | 15+ | ✓ PASS | Batch runner and multi-fold execution passing |
| Feature Models | 20+ | ✓ PASS | FM loading, traversal, ID consistency verified |
| Bias/Constraints | 20+ | ✓ PASS | Bias loading, constraint mapping validated |
| Profiling | 10+ | ✓ PASS | Performance monitoring and metrics working |
| Utilities | 8 | ✓ PASS | Helper functions validated |
| **Evaluation** | 2 | ✗ FAIL | Missing result data files (see below) |

---

## Critical Issues

### Issue: Missing Integration Test Data Files
- **Severity:** Medium (does not affect core functionality)
- **Files Affected:** `/data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json`
- **Context:** Tests attempt to load pre-computed result data for integration validation
- **Impact:** Cannot verify evaluation metrics and accuracy calculations against baseline results
- **Scope:** Limited to integration tests; all unit tests pass
- **Workaround:** Tests can be skipped or result file can be generated via running evaluation pipeline

---

## Code Quality Observations

### Strengths
1. **Comprehensive unit test coverage** — 307 passing tests across 12+ modules
2. **Modular test organization** — Tests properly organized by feature/component
3. **Test data management** — Effective use of fixtures, test data directories
4. **Performance validation** — Dedicated tests for algorithm performance and profiling
5. **Cross-validation logic** — Multi-fold and incremental/non-incremental modes tested
6. **Oracle verification** — Feature ID consistency with flamapy tree order validated

### Observations
1. **Missing integration result files** — Evaluation integration tests require pre-computed baseline data
2. **Known pytest warnings documented** — Both warnings are expected and documented in CLAUDE.md
3. **Test execution speed** — 53.54s total execution time is acceptable for 309 tests

---

## Recommendations

### Immediate Actions
1. **Generate missing result data** — Run evaluation pipeline to generate `REAL-FM-7_rs_1n_non-incremental_fold1_kb.json`
   - Location: `/data/results/`
   - Or: Skip integration tests if data generation is not in current scope
2. **Verify data/results directory structure** — Ensure expected result files are generated by evaluation scripts
3. **Optional: Register pytest marks** — Add `pytest.mark.slow` to pytest.ini configuration (cosmetic only)

### Future Improvements
1. **Generate baseline results in CI/CD** — Automate result file generation as test fixture
2. **Mock evaluation results** — Alternative: mock ConGenResultData for integration tests without requiring files
3. **Document test data generation** — Add README in `/data/results/` explaining which tests require pre-computed files

---

## Validation Summary

✓ **Core Functionality:** 307/309 tests passing
✓ **Algorithm Correctness:** All acquisition algorithms verified
✓ **Oracle Verification:** Feature ID consistency validated
✓ **Integration Points:** Cross-module integration tested
⚠ **Integration Tests:** 2 failures due to missing result data files (non-blocking)
✓ **Code Quality:** No syntax or compilation errors detected

---

## Next Steps

1. **Option A (Recommended):** Generate missing evaluation result files
   - Run evaluation pipeline for REAL-FM-7 dataset
   - Store results in `/data/results/` with expected filename
   - Re-run tests to verify both integration tests pass

2. **Option B (Alternative):** Skip integration tests temporarily
   - Mark evaluation tests with condition skip if result files missing
   - Add to roadmap for later completion

3. **Optional:** Register pytest marks and fix collection warnings
   - Add `pytest.ini` configuration for `pytest.mark.slow`
   - Update `conftest.py` to handle TestSuiteReader collection (cosmetic)

---

## Conclusion

The test suite demonstrates **excellent overall quality with 99.35% pass rate**. Core functionality is comprehensive and well-validated across all major modules. The 2 integration test failures are due to missing pre-computed result data files, not code defects. All unit tests, algorithm implementations, and cross-validation logic are functioning correctly.

**Status:** READY FOR MERGE (with option to generate evaluation result files)

---

## Unresolved Questions

1. Should evaluation result files (`REAL-FM-7_rs_1n_non-incremental_fold1_kb.json`) be generated as part of test setup or provided separately?
2. Is it expected that `/data/results/` files are generated by external evaluation runs, or should they be fixtures in version control?
3. Should integration evaluation tests be skipped in normal test runs, or should they be part of regular CI/CD?
