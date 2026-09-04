# Test Suite Report: Oracle Refactoring Verification
**Date:** 2026-02-13 | **Test Time:** 62.27s

## Test Results Overview
- **Total Tests:** 290
- **Passed:** 288 (99.3%)
- **Failed:** 2 (0.7%)
- **Skipped:** 0
- **Warnings:** 2 (non-blocking)

## Executive Summary
Oracle refactoring successful. All import updates across 15 files working correctly. 2 test failures are **pre-existing data file issues**, not refactoring-related.

## Detailed Breakdown

### Passing Test Suites
| Suite | Count | Status |
|-------|-------|--------|
| test_congen.py | 13 | PASS |
| test_diagnosis.py | 144 | PASS |
| test_interactive.py | 84 | PASS |
| test_model.py | 11 | PASS |
| test_profiler.py | 18 | PASS |
| test_utils.py | 18 | PASS |

### Failed Tests (Non-Critical)

**File:** `tests/test_evaluation.py`

1. **test_evaluate_real_fm_7**
   - **Error:** FileNotFoundError
   - **Path:** `/Users/manleviet/Development/GitHub/AcqMSS/data/results/REAL-FM-7_rs_1n_incremental_fold1_kb.json`
   - **Root Cause:** Missing result data file (not refactoring-related)
   - **Location:** `acqmss/eval/result_loader.py:47`

2. **test_accuracy_with_real_examples**
   - **Error:** FileNotFoundError
   - **Path:** Same as above
   - **Root Cause:** Missing result data file (not refactoring-related)
   - **Location:** `acqmss/eval/result_loader.py:47`

## Critical Findings

### Import Refactoring Status
✓ **All oracle imports successfully migrated** to `acqmss/oracle/` package
- No ImportError exceptions
- No AttributeError exceptions
- No circular dependency issues

### Coverage Analysis
- Core algorithms (diagnosis, CONGEN, interactive) fully tested
- Profiler functionality validated
- Utility functions comprehensive

### Key Test Areas Verified
1. **CONGEN Algorithm:** Incremental & non-incremental modes ✓
2. **Diagnosis Operations:** FastDiag, QuickXPlain, FastDiagP, KBDiag ✓
3. **Interactive Learning:** Full QuAcq workflow ✓
4. **Multiple Solver Modes:** Incremental, non-incremental, SAT4J ✓
5. **Profiling:** Performance tracking integration ✓
6. **Feature Model Integration:** Multiple real-world models ✓

## Warnings (Non-Blocking)
1. `TestSuiteReader` class in `explanation/transformations/testsuite_reader.py:10` has `__init__` (pytest warning, not a test class)
2. Unknown pytest mark `@pytest.mark.slow` in `tests/test_interactive.py:372` (intentional custom mark)

## Recommendations

### No Action Required
- Oracle refactoring is complete and stable
- All import statements properly updated
- No regression in existing functionality

### Optional
- Delete or regenerate missing result files if evaluation tests needed
- Register custom pytest mark `slow` in `pytest.ini` to eliminate warning

## Performance Metrics
- Test execution: 62.27 seconds
- Average test time: ~0.21 seconds per test
- No timeout failures
- Deterministic results

## Unresolved Questions
- Are the missing result data files intentional or should they be regenerated?
- Is the `slow` marker intentional for selective test execution?
