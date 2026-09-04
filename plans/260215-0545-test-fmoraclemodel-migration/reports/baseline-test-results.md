# Baseline Test Results (Post-Migration 012a9db)

## Summary
- **Total**: 301 collected
- **Passed**: 60 (20%)
- **Failed**: 233 (77%)
- **Errors**: 8 (3%)
- **Duration**: ~8.4s

## Per-File Breakdown

| File | Passed | Failed | Errors | Total |
|------|--------|--------|--------|-------|
| test_congen.py | 3 | 10 | 0 | 13 |
| test_diagnosis.py | 0 | 204 | 0 | 204 |
| test_evaluation.py | 22 | 3 | 0 | 25 |
| test_interactive.py | 10 | 8 | 8 | 26 |
| test_oracle_model.py | 6 | 6 | 0 | 12 |
| test_bias_module.py | 9 | 0 | 0 | 9 |
| test_profiler.py | 4 | 0 | 0 | 4 |
| test_utils.py | 8 | 2 | 0 | 10 |

## Root Cause Summary (5 distinct issues)

### RC1: `use_incremental` → `_use_incremental` (204 diagnosis failures)
- `DiagnosisModel.use_incremental` property removed/renamed to `_use_incremental`
- `TaskPreparationFactory.create_diagnosis(self.use_incremental)` fails
- **Impact**: ALL 204 diagnosis tests

### RC2: `ConGenTask.e_neg_literals` removed (3 congen failures)
- Field commented out but still referenced in `task_preparation.py:187`
- **Impact**: 3 ConGen integration tests

### RC3: `FeatureModelOracle.get_feature_ids()` returns None (8 errors + 5 failures)
- `get_features()` returns None → `get_feature_ids()` returns None
- Missing `features` attribute on `FeatureModelOracle`
- **Impact**: 8 interactive task errors + 5 interactive learner failures

### RC4: `FMOracleModel` API changes (6 oracle_model failures)
- `with_configuration()` expects `Configuration` object, tests pass `dict`
- `task` property raises RuntimeError before `prepare()`
- `OneShotModel` doesn't implement `CheckerModel` protocol
- **Impact**: 6 oracle_model tests

### RC5: `FeatureModelOracle.fm` attribute missing (3 evaluation failures)
- `get_constraint_descriptions()` references `self.fm` which doesn't exist
- Called via `OracleData.from_uvl()` → `oracle.get_constraint_descriptions()`
- **Impact**: 2 evaluation tests + 1 FileNotFoundError (separate issue)

### Minor: `NEResult.assumption_ids` removed (1 failure)
- Field removed, test still asserts it
- **Impact**: 1 generate_ne test

### Minor: `oracle.feature_ids` → `oracle.get_feature_ids()` (6 failures)
- Property renamed to method
- **Impact**: 6 oracle feature ID tests
