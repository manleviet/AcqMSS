# Phase 6: Clean Up FeatureModelOracle + Wrappers

## Context Links
- [Plan overview](plan.md)
- [Phase 1: Slim Oracle](phase-01-slim-oracle-and-fm-data.md)
- FeatureModelOracle: `acqmss/oracle/fm_oracle.py`
- UserPromptOracle: `acqmss/oracle/user_prompt.py`
- CachedOracle: `acqmss/oracle/cached.py`

## Overview
- **Priority**: P2
- **Status**: complete
- **Effort**: 1h

After phases 1-5, clean up remaining dead code. Remove unused methods from FeatureModelOracle. Verify UserPromptOracle and CachedOracle are minimal. Remove `get_constraint_descriptions()` if unused after GroundTruthData refactor.

## Key Insights
- After Phase 5, `get_constraint_descriptions()` is only needed by `GroundTruthData.from_fm_oracle()` path
- `get_leaf_features()` on FeatureModelOracle — check if used anywhere. Per research: only in fm_oracle.py, possibly unused
- `get_num_constraints()` — used by ConGenTaskPreparation (now from FMData after Phase 3), can stay as non-ABC concrete method
- `get_next_tseitin_var()` — used by ConGenModel.prepare(), stays as concrete method on FeatureModelOracle
- `__repr__` on FeatureModelOracle uses `get_feature_count()` which was removed from ABC — update to use `len(self._oracle_model.variables)`

## Requirements

### Functional
1. Remove `get_leaf_features()` if unused (YAGNI)
2. Remove `get_constraint_descriptions()` if only used by GroundTruthData (which now reads FM directly in `from_uvl()`)
3. Keep `get_constraint_descriptions()` if `from_fm_oracle()` still exists and is called
4. Update `__repr__` to not use removed methods
5. Verify CachedOracle only wraps `is_valid()` after Phase 1 changes

### Non-functional
- FeatureModelOracle should be clean and focused: Oracle ABC + FM-specific extensions
- No dead methods

## Related Code Files

### Modify
| File | Changes |
|------|---------|
| `acqmss/oracle/fm_oracle.py` | Remove dead methods, update `__repr__` |
| `acqmss/oracle/user_prompt.py` | Verify minimal (only `is_valid` + display logic) |
| `acqmss/oracle/cached.py` | Verify minimal (only `is_valid` caching) |

## Implementation Steps

### 1. Audit FeatureModelOracle methods

After phases 1-5, the method inventory should be:

| Method | Keep? | Reason |
|--------|-------|--------|
| `is_valid()` | YES | Oracle ABC |
| `get_features()` | YES | Used by `get_fm_data()` and possibly apps |
| `get_feature_ids()` | YES | Used by `get_fm_data()` |
| `get_fm_data()` | YES | New in Phase 1 |
| `complete_configuration()` | YES | Used by ExampleGenerator |
| `get_cnf_clauses()` | YES | Used by learner.from_examples, from_fm_oracle |
| `get_root_feature()` | YES | Used by `get_fm_data()` and from_fm_oracle |
| `get_num_constraints()` | YES | Used by `get_fm_data()` |
| `get_next_tseitin_var()` | YES | Used by ConGenModel.prepare() |
| `get_kb()` | YES | Used by ConGenTaskPreparation (Phase 4) |
| `get_assumptions()` | YES | Used by ConGenTaskPreparation (Phase 4) |
| `get_c()` | YES | Used by ConGenTaskPreparation (Phase 4) |
| `get_constraint_descriptions()` | MAYBE | Only if from_fm_oracle() path used |
| `get_leaf_features()` | CHECK | Grep for usage |
| `cleanup()` | YES | Resource management |
| `_model_to_config()` | YES | Internal helper |
| `fm` property | MAYBE | Lazy FM load for descriptions |

### 2. Check `get_leaf_features()` usage

```bash
grep -r "get_leaf_features" acqmss/ apps/ tests/
```

If no external usage, remove it.

### 3. Check `get_constraint_descriptions()` usage

After Phase 5, only `GroundTruthData.from_fm_oracle()` calls it. If `from_fm_oracle()` is rare/unused, consider removing both.

**Decision**: Keep `get_constraint_descriptions()` and `from_fm_oracle()`. The eval pipeline uses `from_fm_oracle()` when oracle already exists (e.g., ConGenRunner evaluation). KISS — don't remove working code.

### 4. Update `__repr__`

```python
def __repr__(self):
    return f"FeatureModelOracle(features={len(self._oracle_model.variables)})"
```

### 5. Verify UserPromptOracle

After Phase 1, should contain only:
- `__init__(features, verbose)` — stores features for display
- `is_valid(assignments)` — prompts user
- `get_query_count()` — own stat
- `__repr__`

No `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()`.

### 6. Verify CachedOracle

After Phase 1, should contain only:
- `__init__(base_oracle)` — wraps any Oracle
- `is_valid(assignments)` — cache wrapper
- `get_cache_stats()` — own stat
- `clear_cache()` — own management
- `__repr__`

No delegation of metadata/SAT methods.

### 7. Update module docstrings

Update docstrings in fm_oracle.py, user_prompt.py, cached.py to reflect slim Oracle interface.

## Todo List
- [x] Grep for `get_leaf_features` usage — remove if dead
- [x] Update `__repr__` in FeatureModelOracle
- [x] Verify UserPromptOracle is minimal
- [x] Verify CachedOracle is minimal
- [x] Update module docstrings
- [x] Update `acqmss/oracle/__init__.py` docstring

## Success Criteria
- No dead methods on FeatureModelOracle
- UserPromptOracle has only `is_valid()` + display logic
- CachedOracle has only `is_valid()` caching
- All `__repr__` methods work without removed ABC methods
- Clean module docstrings

## Risk Assessment
- **Risk**: Removing a method that's actually used somewhere not caught by grep
- **Mitigation**: Run full test suite after cleanup. Tests will catch missing methods.

## Next Steps
- Phase 7: Update tests
