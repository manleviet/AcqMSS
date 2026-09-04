# Phase 1: Run Baseline Tests

## Context
- **Parent plan**: [plan.md](plan.md)
- **Dependencies**: None
- **Docs**: [codebase-summary](../../docs/codebase-summary.md), [code-standards](../../docs/code-standards.md)

## Overview
- **Priority**: P1
- **Status**: completed
- **Description**: Execute all 301 tests to establish pass/fail baseline after commit 012a9db

## Key Insights
- 301 tests collected across 8 test files
- Tests use `@parameterized.expand` with incremental/non-incremental modes
- `ENABLED_TESTS`/`ENABLED_PARAMS` dicts control test execution
- Some tests marked `@pytest.mark.slow`

## Requirements
- Run full test suite with verbose output
- Capture stdout/stderr for failure analysis
- Record pass/fail/error/skip counts per test file

## Implementation Steps

1. Run full test suite: `PYTHONPATH=. pytest tests/ -v --tb=long 2>&1`
2. If too many failures, run per-file to isolate:
   - `tests/test_oracle_model.py` - directly tests changed FMOracleModel
   - `tests/test_congen.py` - tests ConGen pipeline including NE generation
   - `tests/test_interactive.py` - tests QuAcq with FeatureModelOracle
   - `tests/test_diagnosis.py` - tests diagnosis algorithms (should be unaffected)
   - `tests/test_evaluation.py` - tests CV pipeline
   - `tests/test_bias_module.py`, `tests/test_profiler.py`, `tests/test_utils.py`
3. Save raw output to `reports/baseline-test-results.md`

## Expected Failure Areas

| Test File | Expected Impact | Reason |
|-----------|----------------|--------|
| test_oracle_model.py | HIGH | Tests updated but `with_configuration()` API changed |
| test_congen.py | MEDIUM | NE generation refactored, field names changed |
| test_interactive.py | MEDIUM | FeatureModelOracle rewritten, 1 test commented out |
| test_diagnosis.py | LOW | Only minor import changes in explanation layer |
| test_evaluation.py | MEDIUM | CV pipeline uses ConGenModelBuilder |
| test_bias_module.py | NONE | No changes to bias module |
| test_profiler.py | NONE | No changes to profiler |
| test_utils.py | NONE | No changes to utils |

## Results
- **Baseline execution**: 233 failed, 60 passed, 8 errors out of 301 tests
- All tests executed without collection errors
- Raw output captured and analyzed in Phase 2

## Todo
- [x] Run `PYTHONPATH=. pytest tests/ -v --tb=long`
- [x] Record pass/fail/error/skip counts
- [x] Save results to report file

## Success Criteria
- All 301 tests executed (no collection errors) ✓
- Raw results captured for Phase 2 analysis ✓
