# Phase 7: Update Tests

## Context Links
- [Plan overview](plan.md)
- All phase files (1-6)
- Tests: `tests/test_congen.py`, `tests/test_interactive.py`

## Overview
- **Priority**: P1
- **Status**: complete
- **Effort**: 1h

Update all tests to work with the refactored Oracle interface. Remove tests that test removed ABC methods. Add tests for FMData. Ensure existing learning pipeline tests pass.

## Key Insights

### test_interactive.py — Oracle usage (lines from research)
- Line 52: `oracle.get_feature_ids()` → stays (method exists on FeatureModelOracle)
- Line 190: `oracle.get_feature_count()` → **REMOVED from ABC** → use `len(oracle.get_features())` or `oracle.get_fm_data().feature_count`
- Line 202: `oracle.get_features()` → stays (method exists on FeatureModelOracle)
- Line 215: `list(oracle.get_features())` → stays
- Line 323: `learner.oracle.get_root_feature()` → stays (method on FeatureModelOracle)
- Line 324: `learner.oracle.get_feature_ids()[root_name]` → stays

### test_congen.py — Oracle usage
- Line 70: `oracle.get_root_feature()` → stays (method on FeatureModelOracle)
- Line 308: `oracle.get_feature_ids() == dict(sat.variables)` → stays
- Line 322: `oracle.get_feature_ids() == bias_ids` → stays

### OracleData references in tests
- Check if any test uses `OracleData` → rename to `GroundTruthData`

### CachedOracle test
- Line 215-224: Tests `CachedOracle` with `is_valid()` and cache hits → works fine after refactoring
- If test calls `CachedOracle.complete_configuration()` → remove that test

## Requirements

### Functional
1. All tests pass with refactored Oracle
2. `get_feature_count()` calls replaced with `oracle.get_fm_data().feature_count` or `len(oracle.get_features())`
3. `OracleData` references renamed to `GroundTruthData`
4. New test: verify `FMData` fields populated correctly
5. New test: verify Oracle ABC has only `is_valid()` abstract method

### Non-functional
- Tests should be clean — no workarounds for old interface

## Related Code Files

### Modify
| File | Changes |
|------|---------|
| `tests/test_interactive.py` | Fix `get_feature_count()` call. Verify CachedOracle tests. Update OracleData refs. |
| `tests/test_congen.py` | Minimal changes (oracle methods still exist on FeatureModelOracle). |
| `tests/test_evaluation.py` | Update OracleData → GroundTruthData if referenced. |

### Create
| File | Purpose |
|------|---------|
| (inline in existing test files) | Add FMData validation assertions |

## Implementation Steps

### 1. Fix test_interactive.py

**Line 190 — `get_feature_count()`:**
```python
# Before
assert oracle.get_feature_count() > 0

# After
assert oracle.get_fm_data().feature_count > 0
```

**CachedOracle tests (lines 215-224):**
```python
# Verify CachedOracle only delegates is_valid()
# Remove any test that calls cached.get_features() or cached.complete_configuration()
```

**Verify learner creation** — `InteractiveLearner.from_files()` signature unchanged, so test code should work.

### 2. Fix test_congen.py

Minimal changes expected. `oracle.get_root_feature()` and `oracle.get_feature_ids()` still exist on FeatureModelOracle.

Verify `ConGenModel.prepare(oracle, ...)` still works as before.

### 3. Update test_evaluation.py

Search for `OracleData` references:
```bash
grep -n "OracleData" tests/test_evaluation.py
```
Replace with `GroundTruthData`.

### 4. Add FMData validation

Add to test_congen.py or test_interactive.py:
```python
def test_fm_data_populated(self):
    """Verify FMData contains correct FM metadata."""
    oracle = FeatureModelOracle(fm_path)
    fm_data = oracle.get_fm_data()

    assert isinstance(fm_data.features, set)
    assert len(fm_data.features) > 0
    assert isinstance(fm_data.feature_ids, dict)
    assert len(fm_data.feature_ids) == len(fm_data.features)
    assert fm_data.root_feature in fm_data.features
    assert fm_data.num_constraints > 0
    assert fm_data.next_tseitin_var > max(fm_data.feature_ids.values())
    assert fm_data.feature_count == len(fm_data.features)
```

### 5. Add Oracle ABC contract test

```python
def test_oracle_abc_minimal(self):
    """Verify Oracle ABC has only is_valid as abstract method."""
    import inspect
    from conacq.oracle.base import Oracle

    abstract_methods = {
        name for name, method in inspect.getmembers(Oracle)
        if getattr(method, '__isabstractmethod__', False)
    }
    assert abstract_methods == {'is_valid'}
```

### 6. Run full test suite

```bash
PYTHONPATH=. pytest tests/ -v
```

Fix any remaining failures iteratively.

## Todo List
- [x] Fix `get_feature_count()` in test_interactive.py
- [x] Remove/update CachedOracle tests that call removed methods
- [x] Update OracleData → GroundTruthData in all test files
- [x] Add FMData validation test
- [x] Add Oracle ABC minimal contract test
- [x] Run full test suite and fix failures
- [x] Verify all ENABLED_TESTS pass

## Success Criteria
- `PYTHONPATH=. pytest tests/ -v` passes all enabled tests
- No references to removed Oracle ABC methods in tests
- FMData validation test passes
- Oracle ABC contract test verifies exactly 1 abstract method

## Risk Assessment
- **Risk**: Tests coupled to Oracle ABC interface in ways not caught by grep
- **Mitigation**: Run tests early and often. Fix iteratively.
- **Risk**: Parameterized tests may mask failures in specific mode combinations
- **Mitigation**: Run with `-v` to see individual test results. Check ENABLED_PARAMS coverage.
- **Risk**: eval tests may use OracleData.from_oracle() path
- **Mitigation**: Grep and update all references before running tests.

## Unresolved Questions
1. Should CachedOracle be kept at all? After slimming, it only caches `is_valid()`. Still useful for query-heavy learning loops.
2. Are there integration tests in `apps/` that need updating? The apps themselves are not in tests/ but may have inline assertions.
