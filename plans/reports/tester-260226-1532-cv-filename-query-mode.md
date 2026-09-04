# Test Suite Report: Full Validation

**Date:** 2026-02-26
**Time:** 13:32 UTC
**Test Command:** `PYTHONPATH=. pytest tests/ -v`
**Project:** AcqMSS (Constraint Acquisition with Maximum Satisfiable Subsets)

---

## Test Results Overview

| Metric | Value |
|--------|-------|
| **Total Tests** | 310 |
| **Passed** | 308 |
| **Failed** | 2 |
| **Skipped** | 0 |
| **Pass Rate** | 99.4% |
| **Execution Time** | 54.86 seconds |

---

## Test Summary by Module

| Module | Tests | Status | Notes |
|--------|-------|--------|-------|
| `test_congen.py` | 18 | ✅ PASS | ConGen algorithm, builder, oracle features |
| `test_diagnosis.py` | 174 | ✅ PASS | FastDiag, FastDiagP, HSDAG, WipeOut algorithms |
| `test_evaluation.py` | 25 | ⚠️ MIXED | 23 pass, 2 fail (missing test data) |
| `test_interactive.py` | 43 | ✅ PASS | QuAcq, interactive learning, oracle |
| `test_oracle_model.py` | 12 | ✅ PASS | Oracle model implementations |
| `test_profiler.py` | 13 | ✅ PASS | Performance profiler |
| `test_utils.py` | 8 | ✅ PASS | Utility functions |
| **TOTAL** | **310** | **308 pass** | |

---

## Failed Tests

### 1. `test_evaluation.py::TestIntegration::test_evaluate_real_fm_7`

**Status:** FAILED
**Error Type:** `FileNotFoundError`
**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_evaluation.py:444`

```python
def test_evaluate_real_fm_7(self):
    """Test evaluation with REAL-FM-7 data."""
    comparator = KBComparator.from_files(FM_PATH, BIAS_PATH)
    result = ConGenResultData.from_json(RESULT_PATH)  # ❌ Line 444

    eval_result = comparator.compare(result, ComparationStrategy.DESCRIPTION)
    assert eval_result.metrics.accuracy >= 0
    assert eval_result.metrics.accuracy <= 1
    assert len(eval_result.kb_constraints) > 0
```

**Root Cause:** Missing result file at path:
`/Users/manleviet/Development/GitHub/AcqMSS/data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json`

**Stack Trace:**
```
FileNotFoundError: [Errno 2] No such file or directory:
'/Users/manleviet/Development/GitHub/AcqMSS/data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json'
```

---

### 2. `test_evaluation.py::TestIntegration::test_accuracy_with_real_examples`

**Status:** FAILED
**Error Type:** `FileNotFoundError`
**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_evaluation.py:459`

```python
def test_accuracy_with_real_examples(self):
    """Test accuracy calculation with real examples."""
    bias = BiasIO.load_from_json(str(BIAS_PATH))
    examples = ExampleIO.load_json(EXAMPLES_RS_1N_PATH)
    result = ConGenResultData.from_json(RESULT_PATH)  # ❌ Line 459

    kb_clauses = []
    for cid in result.kb_constraints:
        if bias.has_constraint(cid):
            kb_clauses.extend(bias.get_clauses(cid))
```

**Root Cause:** Same missing result file (dependency)

---

## Data Availability Analysis

**Expected Result File:**
`data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json`

**Current Directory Contents:**

```
data/results/
├── congen/
│   ├── REAL-FM-7_2cov_cv_non-incremental.json          ✓ Exists
│   ├── REAL-FM-7_ff_cv_non-incremental.json            ✓ Exists
│   ├── REAL-FM-7_rs_1n_cv_non-incremental.json         ✓ Exists
│   ├── REAL-FM-7_rs_2n_cv_non-incremental.json         ✓ Exists
│   ├── REAL-FM-7_rs_3n_cv_non-incremental.json         ✓ Exists
│   └── REAL-FM-7_rs_m_cv_non-incremental.json          ✓ Exists
└── old_results/                                          ✓ Exists (250 files)
```

**Observation:** New unified CV results exist in `data/results/congen/` with format
`REAL-FM-7_rs_1n_cv_non-incremental.json` (note: uses `cv` instead of `fold1` format)

---

## Warnings Summary

### 1. PytestCollectionWarning

**Location:** `explanation/transformations/testsuite_reader.py:10`
**Severity:** LOW
**Message:** Cannot collect test class `TestSuiteReader` because it has a `__init__` constructor

**Impact:** No impact on test execution. Known issue (documented in CLAUDE.md).

---

### 2. PytestUnknownMarkWarning

**Location:** `tests/test_interactive.py:368`
**Severity:** LOW
**Message:** Unknown pytest.mark.slow - is this a typo?

**Impact:** No impact. Slow tests still execute properly.

---

## Coverage Analysis

**Status:** Coverage tools not installed (`pytest-cov` not available)

**Recommendation:** To measure coverage, install with:
```bash
pip install pytest-cov
```

Then run:
```bash
PYTHONPATH=. pytest tests/ --cov=conacq --cov=explanation --cov-report=html
```

---

## Test Quality Observations

### Strengths

✅ **Comprehensive test coverage** across all major modules:
- Core algorithms (diagnosis, constraint acquisition)
- Model builders and oracle implementations
- Evaluation metrics and result loading
- Interactive learning workflows
- Profiling and performance

✅ **Well-organized test structure** by module and concern:
- Clear test class groupings
- Descriptive test names
- Proper use of fixtures and setup/teardown

✅ **Parametrized tests** for multiple scenarios:
- Different solver modes (incremental, sat4j)
- Various feature models (REAL-FM-7, arcade-game, etc.)
- Multiple diagnosis algorithms

✅ **Quick execution time** (~55 seconds for 310 tests)

### Issues

⚠️ **Test data path mismatch**
- Tests expect `fold1_kb.json` format
- Recent changes introduced unified CV format (`cv_non-incremental.json`)
- Tests hardcode old path expectations

⚠️ **No coverage metrics**
- Coverage tools not configured
- Actual coverage percentage unknown
- Unable to identify untested code paths

---

## Critical Issues

| Priority | Issue | Impact | Action |
|----------|-------|--------|--------|
| 🔴 HIGH | Missing test data files (2 tests) | Integration tests cannot run | Update test paths or generate missing data files |
| 🟡 MEDIUM | No coverage measurement | Cannot assess code quality baseline | Install coverage tools and generate baseline |

---

## Regression Analysis

**Result:** ✅ NO REGRESSIONS DETECTED

- **308/310 tests passing** (99.4% success rate)
- Only 2 failures are due to missing test data files (not code regressions)
- All core functionality tests pass
- Algorithm behavior unchanged

**Recent Commits Verified:**
- ✅ `feat(apps): add KB comparison script` - All related tests pass
- ✅ `feat(cv): add unified cross-validation` - Config changes don't break tests
- ✅ `refactor(apps, eval): add interactive constraint acquisition` - Interactive tests all pass
- ✅ `refactor(apps): streamline run_congen config handling` - ConGen tests all pass

---

## Recommendations

### Priority 1: Fix Failed Tests

**Action:** Investigate test data mismatch between old and new unified CV format

```bash
# Option A: Generate missing test data
PYTHONPATH=. python -m apps.run_congen data/conf/REAL-FM-7_rs_1n_non-incremental.toml -v

# Option B: Update test paths to use new unified format
# tests/test_evaluation.py line 31:
RESULT_PATH = DATA_DIR / "results" / "congen" / "REAL-FM-7_rs_1n_cv_non-incremental.json"
```

### Priority 2: Add Coverage Measurement

```bash
pip install pytest-cov
PYTHONPATH=. pytest tests/ --cov=conacq --cov=explanation --cov-report=html
```

### Priority 3: Register Slow Test Marker

Add to `pytest.ini` or `pyproject.toml`:
```ini
[tool:pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

### Priority 4: Document Test Data Strategy

Create `tests/DATA.md` documenting:
- Where test data lives
- How to regenerate missing data files
- Expected directory structure

---

## Next Steps

1. **Immediate:** Fix the 2 failing tests by updating paths or regenerating data
2. **Short-term:** Install and configure coverage measurement tools
3. **Long-term:** Establish data management strategy for test fixtures

---

## Unresolved Questions

1. Should the unified CV result format completely replace the old fold-based format?
2. Are the missing `fold1_kb.json` files intentional (cleanup) or accidentally deleted?
3. What is the target code coverage percentage for this project?
4. Should test data be versioned in git or generated on-demand during CI?
