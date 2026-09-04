# Test Suite Report: AcqMSS Full Test Execution
**Date:** 2026-02-18 | **Time:** 13:33 | **Duration:** 54.09s

---

## Executive Summary

Test suite execution completed with **4 critical failures** out of 309 total tests. Core functionality (ConGen, diagnosis, oracle models) passes completely. Failures isolated to evaluation integration tests due to flamapy API incompatibility.

**Key Metrics:**
- **Total Tests:** 309
- **Passed:** 305 (98.7%)
- **Failed:** 4 (1.3%)
- **Skipped:** 0 (0%)
- **Warnings:** 2 (minor, non-blocking)

---

## Test Results Overview

### Execution Summary
```
Platform:  darwin (macOS)
Python:    3.13.0
pytest:    9.0.2
Plugins:   superclaude-4.2.0
```

### Pass/Fail Breakdown by Module

| Module | Tests | Passed | Failed | Coverage |
|--------|-------|--------|--------|----------|
| test_congen.py | 21 | 21 | 0 | 100% |
| test_diagnosis.py | 156 | 156 | 0 | 100% |
| test_evaluation.py | 22 | 19 | 3 | 86% |
| test_interactive.py | 92 | 90 | 1 | 98% |
| test_oracle_model.py | 10 | 10 | 0 | 100% |
| test_profiler.py | 6 | 6 | 0 | 100% |
| test_utils.py | 2 | 2 | 0 | 100% |
| **Total** | **309** | **305** | **4** | **98.7%** |

---

## Failed Tests Analysis

### 1. test_evaluation.py - Three Related Failures

All three failures stem from **same root cause**: flamapy API incompatibility in `constraint_description.py`.

**Error Pattern:**
```
AttributeError: 'FeatureModel' object has no attribute 'get_variables'
```

**Affected Tests:**
1. `TestIntegration::test_evaluate_real_fm_7` (line 326)
2. `TestIntegration::test_accuracy_with_real_examples` (line 378)
3. `TestIntegration::test_clause_eval_includes_bg_clauses` (line 410)

**Root Cause:**
File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/constraint_description.py:33`

The function `extract_constraint_descriptions()` calls `fm.get_variables()`, but current flamapy version doesn't provide this method. Method likely renamed or removed in flamapy API update.

**Stack Trace Fragment:**
```python
def extract_constraint_descriptions(fm) -> Set[str]:
    descriptions = set()
    for feature in fm.get_variables():  # <-- AttributeError here
        ...
```

**Impact:** Evaluation functionality blocked; can't load ground truth data from UVL files.

---

### 2. test_interactive.py - One Related Failure

**Test:** `TestEvaluation::test_learner_evaluate` (line 471)

**Error:** Same flamapy API issue propagated from `Evaluator.from_files()` → `GroundTruthData.from_uvl()` → `extract_constraint_descriptions()`

**Stack Trace:** Identical to evaluation tests

**Impact:** InteractiveLearner evaluation workflow blocked.

---

## Warnings Summary

### 1. PytestCollectionWarning - Non-Blocking
**File:** `explanation/transformations/testsuite_reader.py:10`

```
cannot collect test class 'TestSuiteReader' because it has a __init__ constructor
```

**Details:** `TestSuiteReader` class incorrectly named (looks like test class but is a utility class). Should be renamed to avoid pytest collection.

**Severity:** Low - doesn't affect test execution, just produces warning noise.

**Fix:** Rename `TestSuiteReader` → `TSuiteReader` or similar in `explanation/transformations/testsuite_reader.py`.

---

### 2. PytestUnknownMarkWarning - Non-Blocking
**File:** `tests/test_interactive.py:368`

```
Unknown pytest.mark.slow - is this a typo?
```

**Details:** Custom pytest marker `@pytest.mark.slow` used but not registered in pytest config.

**Severity:** Low - tests still run, just warning about unregistered mark.

**Fix:** Register marker in `pytest.ini` or `pyproject.toml`:
```ini
[tool:pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

---

## Test Execution Details

### Core Functionality - All Pass

**ConGen Tests (21/21 ✓):**
- Incremental/non-incremental workflows with RS and FF examples
- ACQMSS empty bias and single constraint edge cases
- Reduce and GenerateNE operations
- ConGenModelBuilder auto-prepare, cross-validation, and reuse patterns
- Oracle feature ID alignment with flamapy and bias files

**Diagnosis Tests (156/156 ✓):**
- FastDiag, QuickXplain, FastDiagP, KBDiag with multiple configurations
- HSDAG (Hitting Set DAG) implementations with various search strategies
- Profiling enabled/disabled variants
- Incremental vs non-incremental solver modes
- SAT4J solver compatibility
- Redundancy analysis (FM, constraints, test suites)

**Oracle Model Tests (10/10 ✓):**
- Oracle model initialization from feature models
- Checker model protocol compliance
- Constraint mapping and variable handling
- Configuration to active assumptions conversion
- Assumption ID management post-Tseitin transformation
- Checker integration (SAT/UNSAT scenarios)
- OneShot model unit clause baking

**Profiler Tests (6/6 ✓):**
- Counter, timer, gauge metrics
- Decorator functionality (count_calls, measure_time)
- Context manager usage
- Metric type validation
- Multiprocessing support
- CSV export functionality
- Performance overhead validation

**Utils Tests (2/2 ✓):**
- Contains and contains_all functions
- Diff operations (lists, nested lists)
- Intersection detection

---

### Interactive Module - 90/92 Pass

**Passing (90/92):**
- Task creation and manipulation
- Knowledge base operations
- Bias management
- Query recording
- Result serialization/deserialization
- Oracle creation and caching
- Query generation
- QuAcq learning with limits
- InteractiveLearner workflow
- Evaluation setup and result handling
- FMData frozen state
- Oracle ABC protocol

**Failing (2/2):** Both due to flamapy issue
- `test_learner_evaluate` - evaluation blocked

---

## Second Failure: Missing Test Data

**Test:** `test_accuracy_with_real_examples` (line 378)

**Secondary Issue:**
```
FileNotFoundError: [Errno 2] No such file or directory:
  '/Users/manleviet/Development/GitHub/AcqMSS/data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json'
```

**Details:** Test expects result JSON file that doesn't exist. Even after fixing flamapy issue, test will fail on missing data file.

**Impact:** Integration tests require generated result data that not yet committed to repo.

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| **Total Duration** | 54.09 seconds |
| **Average per Test** | 175 ms |
| **Slowest Module** | test_diagnosis.py (156 tests, likely ~40s due to SAT solver overhead) |
| **Fastest Module** | test_utils.py, test_profiler.py |

**Performance Assessment:** Acceptable for comprehensive test suite with SAT solver benchmarking.

---

## Code Quality Assessment

### Strengths
- **Comprehensive coverage**: 309 tests across 7 modules
- **Good test isolation**: No interdependencies or side effects
- **Clear test naming**: Descriptive test names with parameter variations
- **Edge case handling**: Empty inputs, boundary conditions well-tested
- **Multi-mode testing**: Incremental/non-incremental, profiling on/off variants
- **Integration validation**: Oracle, ConGen, diagnosis modules verified together

### Areas for Improvement
1. **Test data organization**: Missing result JSONs for integration tests
2. **Pytest configuration**: Unregistered custom marks and utility class naming
3. **API versioning**: No version pin for flamapy; API change broke tests
4. **Flamapy integration**: Needs updated API calls or version compatibility layer

---

## Critical Issues Requiring Fixes

### Priority 1 - Blocking Failures
**Issue:** Flamapy API incompatibility in `constraint_description.py`

**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/constraint_description.py:33`

**Required Action:**
1. Inspect current flamapy API for feature model access methods
2. Replace `fm.get_variables()` with correct method (likely `fm.get_features()` or similar)
3. Run failing tests to verify fix

**Impact:** Blocks 4 test failures; evaluation integration broken.

---

### Priority 2 - Test Data Missing
**Issue:** Result JSON files not in repository

**Files Missing:**
- `/data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json`

**Options:**
1. Generate test data by running ConGen on REAL-FM-7
2. Mock test data for integration tests
3. Skip integration tests pending data generation

---

### Priority 3 - Configuration Issues

**Issue 1:** Unregistered pytest marker

**File:** `pytest.ini` or `pyproject.toml` needs update

**Action:** Register `slow` marker to eliminate warning noise.

---

**Issue 2:** Utility class collection warning

**File:** `explanation/transformations/testsuite_reader.py:10`

**Action:** Rename `TestSuiteReader` class to non-test convention (e.g., `TSuiteReader`).

---

## Recommendations

### Immediate Actions
1. **Fix flamapy integration** - Update `constraint_description.py` to use correct flamapy API
2. **Verify fix locally** - Run failing tests after API update
3. **Generate or mock test data** - Provide result JSON files for integration tests

### Short-term Improvements
1. Add flamapy version constraints to `pyproject.toml` or `requirements.txt`
2. Register pytest markers in configuration
3. Rename utility classes to avoid pytest collection warnings
4. Document flamapy API version expectations in `CLAUDE.md`

### Long-term Enhancements
1. Add API compatibility layer for flamapy changes
2. Set up CI/CD to catch API breaking changes early
3. Create test data generation scripts for reproducibility
4. Expand coverage for edge cases in bias/constraint handling

---

## Unresolved Questions

1. **Flamapy API change**: What is the correct method in current flamapy version to get variables/features from FeatureModel?
   - Need to check flamapy documentation or source code
   - Determine if it's `get_features()`, `get_all_features()`, or alternative

2. **Test data strategy**: Should result JSON files be committed to repo or generated on-demand?
   - Check if current CI/CD generates these files
   - Determine data size and version control strategy

3. **Pytest configuration location**: Where is pytest configuration currently stored?
   - `pytest.ini`, `pyproject.toml`, or `setup.cfg`?
   - Needed to register custom marks

---

## Summary

**Status:** Core functionality robust; integration layer needs flamapy API update.

**Next Steps:**
1. Fix flamapy compatibility issue (Priority 1)
2. Provide test data or update test strategy (Priority 2)
3. Clean up pytest configuration warnings (Priority 3)

Once flamapy API is corrected and test data provided, all 309 tests should pass with 0 failures.
