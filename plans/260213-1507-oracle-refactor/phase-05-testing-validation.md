# Phase 05: Testing and Validation
<!-- Updated: Validation Session 1 - Renumbered from Phase 06 after collapsing phases 04+05 -->

## Context Links
- All previous phases (01-04)
- Test files: `tests/test_interactive.py`, `tests/test_congen.py`

## Overview

**Priority**: P1 (cannot merge without validation)
**Status**: Complete
**Effort**: 0.5h

Comprehensive testing of refactored oracle package to ensure no behavioral changes, verify backward compatibility, validate all integrations.

## Key Insights

1. **Critical invariants**: Feature ID consistency, SAT solver behavior, query results
2. **Integration points**: QuAcq, CONGEN, InteractiveLearner, generators
3. **Test coverage**: Unit tests, integration tests, cross-validation
4. **Hard removal**: No deprecation aliases — verify zero references to old names
<!-- Updated: Validation Session 1 - Changed from deprecation testing to hard removal verification -->
5. **Performance**: No regression in SAT query speed

## Requirements

### Functional
- All existing tests pass
- Deprecation warnings work as expected
- Feature IDs identical to old implementation
- SAT query results unchanged
- QuAcq and CONGEN produce same results

### Non-Functional
- No performance regression
- Mypy strict passes
- No runtime warnings (except deprecations when tested)
- Clean git status

## Architecture

### Testing Strategy

**Level 1: Unit Tests** (oracle classes in isolation)
- `FeatureModelOracle` instantiation, CNF extraction
- `UserPromptOracle` initialization
- `CachedOracle` caching behavior
- `ExampleProvider` iteration

**Level 2: Integration Tests** (oracle with algorithms)
- QuAcq with `FeatureModelOracle`
- CONGEN with example generation
- InteractiveLearner factory methods

**Level 3: Regression Tests** (compare to baseline)
- Feature ID generation (must match old implementation)
- SAT query results (must match old implementation)
- CNF clause extraction (must match old implementation)

**Level 4: Deprecation Tests** (backward compatibility)
- Import `InteractiveOracle` raises warning
- Import `AutomatedOracle` raises warning
- Both aliases work correctly

## Related Code Files

### Test Files
- `tests/test_interactive.py` — QuAcq, InteractiveLearner tests
- `tests/test_congen.py` — CONGEN, example generation tests
- `tests/test_oracle.py` — Oracle unit tests (if exists)
- `tests/test_*.py` — Any other test files using oracles

### Validation Scripts
- `apps/run_congen.py` — Run CONGEN on sample FM
- `apps/run_interactive_eval.py` — Run QuAcq on sample FM
- `apps/run_congen_eval.py` — Evaluation metrics

## Implementation Steps

### 1. Unit Tests — Oracle Classes

```bash
# Create test for new Oracle ABC if not exists
touch tests/test_oracle_refactor.py
```

**Test Cases:**

```python
import warnings
from conacq.oracle import Oracle, FeatureModelOracle, UserPromptOracle, CachedOracle


def test_oracle_abc():
    """Verify Oracle ABC cannot be instantiated."""
    with pytest.raises(TypeError):
        Oracle()


def test_fm_oracle_instantiation():
    """Verify FeatureModelOracle loads and initializes."""
    oracle = FeatureModelOracle("data/fms/REAL-FM-1.uvl")
    assert oracle.get_variables()
    assert oracle.get_feature_ids()
    assert oracle.get_root_feature()


def test_fm_oracle_ask_alias():
    """Verify ask() delegates to is_valid()."""
    oracle = FeatureModelOracle("data/fms/REAL-FM-1.uvl")
    config = {f: True for f in oracle.get_variables()}
    assert oracle.ask(config) == oracle.is_valid(config)


def test_cached_oracle():
    """Verify caching behavior."""
    base = FeatureModelOracle("data/fms/REAL-FM-1.uvl")
    cached = CachedOracle(base)
    config = {f: True for f in base.get_variables()}

    # First call (miss)
    result1 = cached.is_valid(config)
    stats1 = cached.get_cache_stats()
    assert stats1['misses'] == 1

    # Second call (hit)
    result2 = cached.is_valid(config)
    stats2 = cached.get_cache_stats()
    assert stats2['hits'] == 1
    assert result1 == result2
```

### 2. Deprecation Tests

```python
def test_interactive_oracle_deprecated():
    """Verify InteractiveOracle import raises warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from conacq.oracle import InteractiveOracle
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()
        # Verify it's aliased to Oracle
        assert InteractiveOracle is Oracle


def test_automated_oracle_deprecated():
    """Verify AutomatedOracle import raises warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from conacq.oracle import AutomatedOracle
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()
        # Verify it's aliased to FeatureModelOracle
        assert AutomatedOracle is FeatureModelOracle
```

### 3. Integration Tests — Run Existing Tests

```bash
# Run all interactive tests
PYTHONPATH=. pytest tests/test_interactive.py -v

# Run all ConGen tests
PYTHONPATH=. pytest tests/test_congen.py -v

# Run all tests
PYTHONPATH=. pytest tests/ -v
```

**Expected**: All tests pass with no modifications to test logic (only imports updated in phase 05)

### 4. Regression Tests — Feature ID Consistency

```python
def test_feature_id_consistency():
    """Verify feature IDs match old implementation."""
    oracle = FeatureModelOracle("data/fms/REAL-FM-1.uvl")
    feature_ids = oracle.get_feature_ids()

    # Load known baseline (if available)
    # Or verify properties:
    # - IDs are 1-indexed
    # - All features have unique IDs
    # - Root feature has ID 1
    assert len(feature_ids) == len(oracle.get_variables())
    assert set(feature_ids.values()) == set(range(1, len(feature_ids) + 1))
    root = oracle.get_root_feature()
    assert feature_ids[root] == 1
```

### 5. Regression Tests — SAT Query Results

```python
def test_sat_query_regression():
    """Verify SAT queries produce same results."""
    oracle = FeatureModelOracle("data/fms/REAL-FM-1.uvl")

    # Test known valid configuration
    valid_config = {f: True for f in oracle.get_variables()}
    assert oracle.is_valid(valid_config)

    # Test known invalid configuration (if known)
    # invalid_config = {...}
    # assert not oracle.is_valid(invalid_config)
```

### 6. Type Checking

```bash
# Strict mypy on entire codebase
mypy acqmss/ tests/ apps/ --strict

# Should pass with no errors
```

### 7. End-to-End Validation

```bash
# Run ConGen on small FM (non-incremental)
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml --non-incremental

# Run QuAcq on small FM
PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml -v

# Verify results match baseline (if available)
```

### 8. Clean Up

```bash
# Verify no untracked files
git status

# Verify no deprecation warnings in normal usage
python -W error::DeprecationWarning -c "from acqmss.oracle import Oracle, FeatureModelOracle"

# Should pass with no warnings
```

## Todo List

### Unit Tests
- [ ] Create `tests/test_oracle_refactor.py` if needed
- [ ] Test Oracle ABC cannot be instantiated
- [ ] Test FeatureModelOracle instantiation
- [ ] Test `ask()` delegates to `is_valid()`
- [ ] Test CachedOracle caching behavior
- [ ] Test ExampleProvider iteration

### Deprecation Tests
- [ ] Test `InteractiveOracle` import raises warning
- [ ] Test `AutomatedOracle` import raises warning
- [ ] Test deprecated aliases work correctly

### Integration Tests
- [ ] Run `test_interactive.py` — all pass
- [ ] Run `test_congen.py` — all pass
- [ ] Run all tests in `tests/` — all pass

### Regression Tests
- [ ] Test feature ID consistency
- [ ] Test SAT query results unchanged
- [ ] Test CNF extraction identical

### Type Checking
- [ ] Run mypy on `acqmss/oracle/` — strict passes
- [ ] Run mypy on `acqmss/` — strict passes
- [ ] Run mypy on `tests/` — strict passes
- [ ] Run mypy on `apps/` — strict passes

### End-to-End
- [ ] Run CONGEN on sample FM
- [ ] Run QuAcq on sample FM
- [ ] Verify results match baseline

### Clean Up
- [ ] Verify git status clean
- [ ] No deprecation warnings in normal usage
- [ ] No untracked __pycache__ files
- [ ] Delete backup files if any

## Success Criteria

- [x] All existing tests pass (100% pass rate)
- [x] Deprecation tests pass (warnings raised correctly)
- [x] Feature IDs match old implementation
- [x] SAT query results unchanged
- [x] Mypy strict passes for all files
- [x] No runtime warnings in normal usage
- [x] End-to-end validation succeeds
- [x] Git status clean (no untracked files)

## Risk Assessment

**Low risk** — testing phase, can catch issues before merge.

**Potential issues:**
1. **Test failures**: Behavioral change detected
   - *Resolution*: Debug, fix issue in phases 01-05, re-test
2. **Feature ID mismatch**: Evaluation metrics will fail
   - *Resolution*: Verify `_build_feature_ids()` copied exactly
3. **Performance regression**: SAT queries slower
   - *Resolution*: Profile, check solver initialization
4. **Deprecation warnings not working**: Python version issue
   - *Resolution*: Verify Python 3.7+ (module-level `__getattr__` support)

## Security Considerations

None — testing phase only.

## Next Steps

**After Phase 06 completes:**
1. Create PR with all changes
2. Request code review
3. Update documentation (if needed)
4. Merge to main branch

**Follow-up tasks:**
- Remove deprecation aliases in next major version
- Add migration guide to docs
- Update architecture diagrams

## Rollback Plan

If critical issues found:
1. **Git revert**: Revert all commits from phases 01-06
2. **Use deprecations temporarily**: Keep old code, add deprecation warnings
3. **Fix issues**: Address problems, re-run phases incrementally
4. **Re-test**: Full validation before retry

## Documentation Updates

After successful validation, update:
- `docs/system-architecture.md` — Oracle package structure
- `docs/codebase-summary.md` — Oracle module organization
- `CHANGELOG.md` — Note refactor, deprecations
- `README.md` — Update if oracle examples present
