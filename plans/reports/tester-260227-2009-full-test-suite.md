# Full Test Suite Report
**Date:** 2026-02-27
**Command:** `PYTHONPATH=. pytest tests/ -v`
**Duration:** 65.29s (after fix)

---

## Test Results Overview

| Metric | Count |
|--------|-------|
| Total collected | 340 |
| Passed | 340 |
| Failed | 0 |
| Skipped | 0 |
| Warnings | 2 |

**Overall Status: PASS**

---

## Failed Tests (Fixed)

Both failures were in `tests/test_evaluation.py::TestIntegration` — stale `RESULT_PATH` on line 31 pointing to `data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json` which no longer existed at that flat path. File was relocated to `data/results/old_results/` during an earlier pipeline refactor.

**Fix applied** (`tests/test_evaluation.py` line 31):
```python
# Before
RESULT_PATH = DATA_DIR / "results" / "REAL-FM-7_rs_1n_non-incremental_fold1_kb.json"
# After
RESULT_PATH = DATA_DIR / "results" / "old_results" / "REAL-FM-7_rs_1n_non-incremental_fold1_kb.json"
```

Both tests pass after fix.

---

## Warnings

| Warning | File | Description |
|---------|------|-------------|
| `PytestCollectionWarning` | `explanation/transformations/testsuite_reader.py:10` | `TestSuiteReader` has `__init__` constructor; pytest cannot collect it. Known/expected. |
| `PytestUnknownMarkWarning` | `tests/test_quacq.py:230` | `@pytest.mark.slow` is unregistered. Known/expected per CLAUDE.md. |

Both warnings are pre-existing and documented in CLAUDE.md as known issues.

---

## Test Files Summary

| File | Passed | Failed |
|------|--------|--------|
| `test_congen.py` | 18 | 0 |
| `test_diagnosis.py` | ~225 | 0 |
| `test_evaluation.py` | 22 | 2 |
| `test_oracle_model.py` | 7 | 0 |
| `test_profiler.py` | 11 | 0 |
| `test_quacq.py` | ~30 | 0 |
| `test_semantic_equivalence.py` | ~5 | 0 |
| `test_utils.py` | 8 | 0 |

---

## Coverage

Coverage not collected (not requested). No `--cov` flag used.

---

## Build Status

No build step for Python. Import resolution: OK (PYTHONPATH=. applied correctly).

---

## Critical Issues

None. All 340 tests pass.

---

## Recommendations

1. **Register `pytest.mark.slow`** in `pytest.ini` or `pyproject.toml` to silence persistent `PytestUnknownMarkWarning`.
