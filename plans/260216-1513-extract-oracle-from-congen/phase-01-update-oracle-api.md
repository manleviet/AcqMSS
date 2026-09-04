# Phase 1: Update Oracle API

## Context Links
- [plan.md](./plan.md)
- [fm_oracle.py](../../conacq/oracle/fm_oracle.py)
- [fm_oracle_model.py](../../conacq/oracle/fm_oracle_model.py)

## Overview
- **Date**: 2026-02-16
- **Description**: Expose FM metadata properties from `FeatureModelOracle` so callers can get `next_tseitin_var`, `num_fm_constraints`, and `root_feature` without accessing internal `FMOracleModel`.
- **Priority**: P2
- **Implementation Status**: Pending
- **Review Status**: Pending

## Key Insights
- `FeatureModelOracle` already has `get_root_feature()` (lazy-loads FM for it) and `get_num_constraints()` (delegates to `_oracle_model.constraint_map`).
- `next_tseitin_var` lives on `FMOracleModel` but not exposed through `FeatureModelOracle`.
- `num_fm_constraints` is just `len(oracle_model.constraint_map)` -- already available via `get_num_constraints()`.
- `root_feature` is available via `get_root_feature()` but requires lazy FM load. Could also be derived from variables (feature with id=1).
- ConGenTaskPreparation needs all three values; currently reads them from `ConGenModel` fields.

## Requirements

### Functional
- `FeatureModelOracle.get_next_tseitin_var() -> int` -- expose starting Tseitin variable ID
- Existing `get_num_constraints()` and `get_root_feature()` already satisfy needs

### Non-Functional
- No new dependencies
- No behavioral changes to existing oracle callers

## Architecture

```
FeatureModelOracle
  ├── get_root_feature() -> str          # existing (lazy FM load)
  ├── get_num_constraints() -> int       # existing (delegates to _oracle_model)
  └── get_next_tseitin_var() -> int      # NEW (delegates to _oracle_model)
```

## Related Code Files

### Files to Modify
| File | Change |
|------|--------|
| `acqmss/oracle/fm_oracle.py` | Add `get_next_tseitin_var()` method |

### Files Unchanged
| File | Reason |
|------|--------|
| `acqmss/oracle/fm_oracle_model.py` | `next_tseitin_var` already a public attribute |
| `acqmss/oracle/base.py` | No ABC change needed (concrete method on FeatureModelOracle) |

## Implementation Steps

1. **Add `get_next_tseitin_var()` to `FeatureModelOracle`**
   ```python
   def get_next_tseitin_var(self) -> int:
       """Get starting Tseitin variable ID from FM model."""
       return self._oracle_model.next_tseitin_var
   ```
   - Place after `get_num_constraints()` (line ~119)
   - Simple delegation, no lazy loading needed

2. **Verify existing methods are sufficient**
   - `get_root_feature()` returns `str` (root feature name) -- sufficient for `_prepare_bg()`
   - `get_num_constraints()` returns `int` (FM constraint count) -- sufficient for ID reservation

3. **Run tests to verify no regressions**
   ```bash
   PYTHONPATH=. pytest tests/test_congen.py -v
   ```

## Todo List
- [ ] Add `get_next_tseitin_var()` to `FeatureModelOracle`
- [ ] Run existing tests to verify no regressions

## Success Criteria
- `FeatureModelOracle` exposes all 3 FM metadata values needed by ConGenTaskPreparation
- All existing tests pass unchanged
- No new dependencies introduced

## Risk Assessment
- **Very Low**: Adding a simple getter; no behavioral change

## Security Considerations
- None -- pure read-only accessor

## Next Steps
- Phase 2 uses these accessors when refactoring `ConGenModel.prepare()` to accept oracle parameter
