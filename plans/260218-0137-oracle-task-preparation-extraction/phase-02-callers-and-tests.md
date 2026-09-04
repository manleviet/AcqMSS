# Phase 02: Update Callers & Tests

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-core-refactoring.md)

## Overview
- **Priority**: High
- **Status**: complete
- **Description**: Update callers and tests for `with_configuration` return type change (list → FMOracleModel)

## Related Code Files
- **Modify**: `conacq/oracle/fm_oracle.py` — `FeatureModelOracle.is_valid()`
- **Modify**: `tests/test_oracle_model.py` — return type assertions

## Implementation Steps

### Step 1: Update `FeatureModelOracle.is_valid()` (fm_oracle.py:80-82)
Current:
```python
self._oracle_model.with_configuration(assignments)
return self._checker.is_consistent(self._oracle_model.get_c())
```
- `with_configuration` now returns `self` (FMOracleModel) not list
- Current code already calls `get_c()` separately — **no change needed** (return value unused)
- Verify no other callers depend on return value

### Step 2: Update test `test_config_to_active_assumptions` (test_oracle_model.py:41-44)
Current:
```python
active = model.with_configuration({"f1": True, "f2": False})
assert model._pos_assignment_to_assumption["f1"] in active
assert model._neg_assignment_to_assumption["f2"] in active
```
Update to:
```python
model.with_configuration({"f1": True, "f2": False})
active = model.get_c()
assert model._pos_assignment_to_assumption["f1"] in active
assert model._neg_assignment_to_assumption["f2"] in active
```

### Step 3: Update test `test_checker_integration_sat` (test_oracle_model.py:61-62)
Current:
```python
active = model.with_configuration({"f1": True, "f2": True})
assert checker.is_consistent(active) is True
```
Update to:
```python
model.with_configuration({"f1": True, "f2": True})
assert checker.is_consistent(model.get_c()) is True
```

### Step 4: Update test `test_checker_integration_unsat` (test_oracle_model.py:72-73)
Same pattern as Step 3.

### Step 5: Run tests
```bash
PYTHONPATH=. pytest tests/test_oracle_model.py -v
PYTHONPATH=. pytest tests/ -v  # full suite
```

## Todo
- [x] Verify `FeatureModelOracle.is_valid()` — likely no change needed
- [x] Update `test_config_to_active_assumptions`
- [x] Update `test_checker_integration_sat`
- [x] Update `test_checker_integration_unsat`
- [x] Run tests and verify all pass

## Success Criteria
- All tests pass
- No caller depends on `with_configuration` returning a list
- Fluent chaining works: `model.with_configuration(cfg).get_c()`
