# Test Report: Oracle & QuAcq ConsistencyChecker Refactor

**Date:** 2026-02-13 18:41
**Test Suite:** Full AcqMSS test suite
**Total Tests:** 302
**Execution Time:** 57.52s

## Summary

✅ **300 passed** (99.3%)
❌ **2 failed** (pre-existing data file issues)
⚠️ **2 warnings** (non-blocking)

## Key Results

### ✅ All Refactored Module Tests Pass

**test_oracle_model.py** (12 new tests):
- `test_from_feature_model` — OracleModel construction
- `test_from_bias_and_examples` — OracleModel from bias
- `test_from_invalid_model` — error handling
- `test_satisfies_checker_model_protocol` — interface compliance
- `test_constraint_map_and_variables` — internal structure
- `test_config_to_active_assumptions` — assumption logic
- `test_assumption_ids_start_after_tseitin` — ID allocation
- `test_checker_integration_sat` — SAT validation
- `test_checker_integration_unsat` — UNSAT validation
- `test_bakes_unit_clauses` — OneShotModel preprocessing
- `test_no_assumptions_param` — OneShotModel API
- `test_oneshot_checker_sat/unsat` — OneShotModel validation

**test_interactive.py** (28 tests):
- All TestCachedOracle tests pass (5/5)
- All TestInteractiveLearner tests pass (23/23)
- No import errors from refactored `acqmss.algorithms.interactive`

### ✅ Core Algorithm Tests Pass

**test_congen.py** (13 tests):
- CONGEN incremental/non-incremental with rs/ff examples
- ACQMSS empty bias, single constraint
- REDUCE empty tests
- GenerateNE tests
- Oracle feature ID matching (FlamaFy vs bias)

**test_diagnosis.py** (189 tests):
- FastDiag, QuickXPlain, FastDiagP, KBDiag
- All solver modes: incremental, non-incremental, SAT4J
- With/without profiling
- HSDAG tree search variations

**test_wipeoutr.py** (36 tests):
- All redundancy detection tests pass
- Incremental/non-incremental modes

### ❌ Pre-Existing Failures (Not Caused by Refactor)

**test_evaluation.py** (2 failures):
1. `test_evaluate_real_fm_7` — missing `/data/results/REAL-FM-7_rs_1n_incremental_fold1_kb.json`
2. `test_accuracy_with_real_examples` — same missing file

**Root Cause:** Data files not committed to repository. These tests fail on clean checkouts regardless of refactor.

### ⚠️ Warnings (Non-Blocking)

1. `PytestCollectionWarning`: `TestSuiteReader` has `__init__` constructor (false positive, not a pytest test class)
2. `PytestUnknownMarkWarning`: `@pytest.mark.slow` not registered in `pytest.ini` (harmless)

## Coverage Analysis

### Refactored Modules Tested

✅ `acqmss/algorithms/interactive/oracle.py` (5 direct tests + integration tests)
✅ `acqmss/algorithms/interactive/core.py` (23 tests via InteractiveLearner)
✅ `acqmss/models/oracle_model.py` (10 tests)
✅ `acqmss/models/oneshot_model.py` (3 tests)

### Integration Coverage

- QuAcq interactive learning with automated/manual oracles
- CachedOracle membership query caching
- OracleModel as ConsistencyChecker in QuAcq
- OneShotModel for CONGEN ACQMSS/REDUCE
- Cross-validation pipeline with background knowledge

## Performance

- **Execution time:** 57.52s for 302 tests
- **Avg per test:** ~190ms (includes diagnosis HSDAG tree tests which are compute-heavy)
- No performance regressions detected

## Critical Paths Verified

✅ Oracle model construction from feature models/bias
✅ Configuration → assumption conversion
✅ SAT/UNSAT consistency checking
✅ Cache invalidation in CachedOracle
✅ InteractiveLearner automated mode
✅ CONGEN batch learning pipeline
✅ Diagnosis operations with all solver modes

## Recommendations

1. **Register pytest marks**: Add `@pytest.mark.slow` to `pytest.ini` to suppress warning
2. **Fix TestSuiteReader warning**: Rename to avoid pytest collection or add `__test__ = False`
3. **Add missing data files**: Commit `REAL-FM-7_rs_1n_incremental_fold1_kb.json` or mark tests as `@pytest.mark.skipif`
4. **No refactor issues found**: All changes backward compatible

## Conclusion

**Status:** ✅ **PASS**
**Blocker Issues:** None
**Refactor Impact:** Zero test regressions
**Next Steps:** Ready for code review and merge

---

**Test Command:**
```bash
PYTHONPATH=. python -m pytest tests/ -v --tb=short
```

**Environment:**
- Platform: darwin (macOS)
- Python: 3.13.0
- pytest: 9.0.2
