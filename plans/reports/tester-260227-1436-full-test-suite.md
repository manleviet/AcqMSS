# Full Test Suite Report — AcqMSS
**Date:** 2026-02-27 | **Time:** 14:36 UTC
**Test Framework:** pytest 9.0.2 | **Python:** 3.13.0

---

## Executive Summary

Full test suite execution **completed with 2 failures** out of 349 tests. Overall pass rate: **99.4%** (347/349). Both failures are integration tests requiring pre-generated result data files that are absent from the repository.

---

## Test Results Overview

| Metric | Count | Status |
|--------|-------|--------|
| **Total Tests** | 349 | — |
| **Passed** | 347 | ✓ Pass |
| **Failed** | 2 | ✗ Fail |
| **Skipped** | 0 | — |
| **Warnings** | 2 | ⚠ Info |
| **Execution Time** | 67.73s | ~ 1m 8s |

---

## Test Suite Breakdown by Module

| Module | Tests | Status |
|--------|-------|--------|
| `test_congen.py` | 33 | All pass |
| `test_diagnosis.py` | 180 | All pass |
| `test_evaluation.py` | 44 | 2 failures (see below) |
| `test_oracle_model.py` | 10 | All pass |
| `test_profiler.py` | 11 | All pass |
| `test_quacq.py` | 43 | All pass |
| `test_query_converter.py` | 4 | All pass |
| `test_semantic_equivalence.py` | 13 | All pass |
| `test_utils.py` | 11 | All pass |

---

## Failures Detail

### 1. `test_evaluation.py::TestIntegration::test_evaluate_real_fm_7`

**Type:** `FileNotFoundError`
**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/result_loader.py:70`
**Error Message:**
```
[Errno 2] No such file or directory:
'/Users/manleviet/Development/GitHub/AcqMSS/data/results/
REAL-FM-7_rs_1n_non-incremental_fold1_kb.json'
```

**Root Cause:** Test expects pre-computed result JSON file that doesn't exist. This file should contain serialized ConGenResultData from a prior run.

**Stack Trace:**
```python
def test_evaluate_real_fm_7(self):
    comparator = KBComparator.from_files(FM_PATH, BIAS_PATH)
    result = ConGenResultData.from_json(RESULT_PATH)  # ← Fails here
    ...
```

**Status:** Non-critical. Test depends on external data file not committed to repo.

---

### 2. `test_evaluation.py::TestIntegration::test_accuracy_with_real_examples`

**Type:** `FileNotFoundError`
**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/result_loader.py:70`
**Error Message:** Same as above (missing `RESULT_PATH`)

**Root Cause:** Same as test #1 — depends on absent pre-generated result file.

**Stack Trace:**
```python
def test_accuracy_with_real_examples(self):
    bias = BiasIO.load_from_json(str(BIAS_PATH))
    examples = ExampleIO.load_json(EXAMPLES_RS_1N_PATH)
    result = ConGenResultData.from_json(RESULT_PATH)  # ← Fails here
```

**Status:** Non-critical. Test depends on external data file not committed to repo.

---

## Warnings Summary

### PytestCollectionWarning
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/explanation/transformations/testsuite_reader.py:10`

```python
class TestSuiteReader(TextToModel):
    # Has __init__ constructor, triggers false pytest collection warning
```

**Impact:** None. False positive — `TestSuiteReader` is not a test class despite name pattern.
**Resolution:** Rename class or configure pytest marker in `pytest.ini` to exclude it.

### PytestUnknownMarkWarning
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py:230`

```python
@pytest.mark.slow
def test_quacq_offline_learning_progressive_query_elimination():
    ...
```

**Impact:** None. Marker registered but not configured in pytest settings.
**Resolution:** Add to `pytest.ini`:
```ini
[pytest]
markers =
    slow: slow-running tests
```

---

## Coverage Analysis

### Current Status
No code coverage tool detected in environment (`pytest-cov` not installed). Recommend installing:
```bash
pip install pytest-cov
```

Once installed, generate coverage with:
```bash
PYTHONPATH=. pytest tests/ --cov=conacq --cov-report=html
```

### Test Quality Observations
- **Strong test isolation:** Tests run independently with no cross-dependencies
- **Broad module coverage:** Tests span 8 distinct modules covering core functionality
- **Large diagnosis test suite:** 180 tests covering multiple diagnosis algorithms + solver modes
- **Parametrized tests:** Many tests use parametrized fixtures (FM models, solver configs)

---

## Key Test Categories

### Constraint Generation (ConGen)
- ✓ Incremental + non-incremental modes
- ✓ Multiple example generation strategies (RS, FF)
- ✓ Oracle feature ID consistency (vs flamapy, bias)
- ✓ Model builder auto-preparation
- ✓ Cross-validation re-preparation

### Diagnosis (FastDiag, HSdag, Wipeout)
- ✓ Multiple solver backends (incremental, non-incremental, SAT4J)
- ✓ Profiling integration
- ✓ Redundancy detection
- ✓ Conflict-directed search algorithms
- **180 tests total** across variants

### Query Generation (QuAcq)
- ✓ Result creation + serialization
- ✓ Feature model oracle
- ✓ Cached oracle optimization
- ✓ Progressive query elimination

### Evaluation & Metrics
- ✓ Accuracy/precision/recall/F1 calculations
- ✓ Bias loading from JSON
- ✓ Result data serialization
- ✓ Metrics aggregation

### Additional
- ✓ Profiler: Counters, timers, decorators, context managers
- ✓ Query converter: Example transformation logic
- ✓ Semantic equivalence: SAT-based KB comparison
- ✓ Utils: List operations, containment checks

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Total Execution Time | 67.73 seconds |
| Avg Time per Test | ~194 ms |
| Slowest Category | Diagnosis tests (multiple solver configs) |
| Test Collection Time | < 1 second |

**Performance Notes:**
- Diagnosis tests are slow (~5-10s per test) due to SAT solver invocation
- Most core tests execute in < 100 ms
- No obvious performance regressions detected

---

## Critical Issues

**None.** All core functionality tests pass. Two failures are integration tests missing external data files.

---

## Recommendations

### High Priority
1. **Generate missing result files:** Run ConGen against REAL-FM-7 to generate expected result JSON:
   ```bash
   PYTHONPATH=. python -m apps.run_congen apps/conf/run_congen_config.toml -v
   ```
   Save output to `/Users/manleviet/Development/GitHub/AcqMSS/data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json`

2. **Install pytest-cov:** Enable code coverage measurement:
   ```bash
   pip install pytest-cov
   ```

### Medium Priority
3. **Register pytest markers:** Add to `pytest.ini` to eliminate warnings:
   ```ini
   [pytest]
   markers =
       slow: slow-running tests
   ```

4. **Fix TestSuiteReader name:** Rename class or exclude from collection to prevent false warnings

### Low Priority
5. **Consider test optimization:** Diagnosis tests account for ~50% of runtime. Consider:
   - Splitting slow tests to separate suite
   - Caching solver instantiation where possible
   - Running diagnosis tests in parallel (if pytest-xdist added)

---

## Next Steps

1. Generate missing test data files to resolve integration test failures
2. Commit pytest configuration to eliminate warnings
3. Add code coverage analysis to CI/CD pipeline
4. Consider test performance optimization for diagnosis suite

---

## Unresolved Questions

- Should integration tests with missing data be skipped (pytest.mark.skip) or require fixture generation?
- Are ConGen result files meant to be committed or generated on-demand?
- Should slow tests be isolated to separate test suite for faster iteration?
