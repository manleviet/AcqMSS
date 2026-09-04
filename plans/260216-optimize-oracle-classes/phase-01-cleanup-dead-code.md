# Phase 1: Clean Up Dead Code & Unused Methods

## Context Links

- [Class Internals](research/researcher-01-class-internals.md) — dead code inventory
- [Callers & Dependencies](research/researcher-02-callers-dependencies.md) — unused method analysis
- [fm_oracle.py](../../conacq/oracle/fm_oracle.py) — 333 LOC, target file
- [fm_oracle_model.py](../../conacq/oracle/fm_oracle_model.py) — 259 LOC, target file

## Overview

- **Priority**: High (unblocks all other phases)
- **Status**: complete
- **Effort**: 30m
- **Description**: Remove ~100 lines of commented-out code and unused public methods from FeatureModelOracle and FMOracleModel. Fix step numbering inconsistency in OracleTaskPreparation.

## Key Insights

- 57 lines of commented code in `fm_oracle.py` (lines 58-116, 168-189) are superseded by FMOracleModel
- `get_c()` in FeatureModelOracle (line 121) never called externally — delegates to `_oracle_model.task.set_c`
- `get_c()` in FMOracleModel (line 84) never called externally — delegates to `task.set_c`
- `get_raw_fm_clauses()` (FMOracleModel line 96) never called externally (only via `FeatureModelOracle.get_cnf_clauses()`)
- `description_provider` property never accessed externally
- OracleTaskPreparation step numbering: "Step 1, Step 2, Step 4" — Step 3 missing

## Requirements

### Functional
- Remove all commented-out code blocks
- Deprecate unused public methods (prefix with `_` or remove)
- Fix step numbering in OracleTaskPreparation

### Non-Functional
- No behavioral changes
- All existing tests must pass unchanged

## Architecture

No architectural changes. Pure code cleanup.

## Related Code Files

### Files to Modify
- `acqmss/oracle/fm_oracle.py` — remove commented blocks, remove unused `get_c()`
- `acqmss/oracle/fm_oracle_model.py` — make `get_c()` internal, fix step numbering

### Files to Verify (tests)
- `tests/test_oracle_model.py` — ensure no tests call removed methods
- `tests/test_congen.py` — regression check
- `tests/test_interactive.py` — regression check

## Implementation Steps

### Step 1: Remove commented code from fm_oracle.py

Remove these blocks:

1. **Lines 58-77**: Old CNF/feature_ids approach (19 lines)
```python
# DELETE: Lines 58-77 (commented block starting with "# # Build ground truth CNF")
```

2. **Lines 79-116**: Unused method stubs (38 lines)
```python
# DELETE: Lines 79-116 (commented _extract_features, _extract_leaf_features, _build_feature_ids, _build_cnf)
```

3. **Lines 168-189**: Commented get_valid_configuration (22 lines)
```python
# DELETE: Lines 168-189 (commented get_valid_configuration method)
```

**Net effect**: -79 lines from fm_oracle.py

### Step 2: Remove unused get_c() from FeatureModelOracle

Remove `get_c()` method (lines 121-123 of fm_oracle.py):
```python
# DELETE:
def get_c(self) -> List:
    """Get the set of potentially faulty constraints."""
    return self._oracle_model.task.set_c
```

Verification: grep codebase for `oracle.get_c()` or `FeatureModelOracle.*get_c` — no external callers exist.

**Note**: Keep `get_kb()` and `get_assumptions()` — they belong to the CheckerModel protocol delegation pattern used by `_checker`.

### Step 3: Make FMOracleModel.get_c() internal

In `fm_oracle_model.py`, the `get_c()` method (line 84) is only called internally by `FeatureModelOracle.is_valid()` via `model.get_c()` at line 148 of fm_oracle.py.

Wait — `is_valid()` calls `self._checker.is_consistent(self._oracle_model.get_c())`. So `get_c()` IS used. Keep it but verify: is it truly needed, or can `is_valid()` call `self._oracle_model.task.set_c` directly?

Decision: **Keep `get_c()` as-is** since `is_valid()` uses it. It's a clean delegation method.

### Step 4: Fix OracleTaskPreparation step numbering

In `fm_oracle_model.py`, line 231:
```python
# BEFORE:
# Step 4: assign to set_c for consistency checks

# AFTER:
# Step 3: assign to set_c for consistency checks
```

### Step 5: Clean up the empty line at fm_oracle_model.py line 178

Remove the extra blank line between `FMOracleModel` and `OracleTaskPreparation` (line 178 has double blank).

### Step 6: Run tests

```bash
PYTHONPATH=. pytest tests/test_oracle_model.py tests/test_congen.py -v
```

## Todo List

- [ ] Remove commented block lines 58-77 in fm_oracle.py
- [ ] Remove commented block lines 79-116 in fm_oracle.py
- [ ] Remove commented block lines 168-189 in fm_oracle.py
- [ ] Remove unused `get_c()` from FeatureModelOracle
- [ ] Fix "Step 4" → "Step 3" in OracleTaskPreparation (line 231)
- [ ] Remove extra blank line at fm_oracle_model.py line 178
- [ ] Run test suite — all tests pass
- [ ] Verify fm_oracle.py reduced to ~250 LOC

## Success Criteria

- fm_oracle.py reduced from 333 to ~250 LOC
- No commented-out code blocks remain
- Step numbering is sequential (1, 2, 3)
- All tests pass with zero changes to test files

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Removing code that is actually referenced | Low | High | Grep for all method names before deletion |
| Test failures from removed get_c() | Low | Medium | Verified no external callers via grep |

## Security Considerations

None — pure cleanup, no logic changes.

## Next Steps

- Phase 2: Extract CTC description parser (depends on this phase for clean baseline)
