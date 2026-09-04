# Phase 2: Update Callers

## Context Links

- Depends on: [Phase 1](phase-01-update-cross-validation.md)
- Plan: [plan.md](plan.md)

## Overview

- **Priority**: P2
- **Status**: complete
- **Description**: Update all call sites to pass required `seed: int` parameter to the refactored CV functions.

## Key Insights

- Only 2 app files call CV functions; no test files call them directly
- `run_congen_eval.py` already passes `seed=seed` where seed defaults to 42 from config -- **no change needed**
- `run_interactive_eval.py` passes `seed=seed` where seed can be `None` from config -- **must ensure a default**
- `acqmss/eval/__init__.py` re-exports both functions -- no signature change needed there

## Requirements

### Functional
- All callers must pass a valid `int` for `seed`
- `run_interactive_eval.py` must provide a default seed when config omits it

### Non-functional
- Existing config files should work without modification (provide defaults in code)

## Architecture

No changes.

## Related Code Files

| File | Action | Details |
|------|--------|---------|
| `apps/run_congen_eval.py` | Verify | Already passes `seed=seed` (default 42) -- no change |
| `apps/run_interactive_eval.py` | Modify | Ensure `seed` is never `None` when calling CV |
| `apps/conf/run_interactive_eval_config.toml` | Optional | Add `seed = 42` if not present |

## Implementation Steps

### 1. Update `apps/run_interactive_eval.py` (line 328)

Current code (line 328):
```python
seed = general.get('seed', None)
```

Change to:
```python
seed = general.get('seed', 42)
```

This ensures seed is always an `int`. Matches behavior of `run_congen_eval.py` (line 125).

### 2. Verify `apps/run_congen_eval.py`

Line 125: `seed = eval_config.get('seed', 42)` -- already provides default 42. No change needed.

Line 233-239: passes `seed=seed` to `n_fold_cross_validation`. Already correct.

### 3. (Optional) Add seed to config TOML

In `apps/conf/run_interactive_eval_config.toml`, consider adding:
```toml
seed = 42
```

This is optional since the code default handles it, but explicit config is clearer.

### 4. Verify no other callers

Grep confirmed no other files call `n_fold_cross_validation` or `n_fold_cross_validation_interactive` besides these two apps and the `__init__.py` re-export.

## Todo List

- [x] Change `seed` default from `None` to `42` in `run_interactive_eval.py` line 328
- [x] Verify `run_congen_eval.py` still works (seed already defaults to 42)
- [x] (Optional) Add `seed = 42` to `apps/conf/run_interactive_eval_config.toml`
- [x] Run full test suite: `PYTHONPATH=. pytest tests/ -v`

## Success Criteria

- `PYTHONPATH=. pytest tests/ -v` -- all tests pass
- Both app scripts can run without errors when config omits `seed`
- No `TypeError: seed must be int` errors from CV functions

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Config files in user's data dirs may rely on `seed=None` behavior | Low | Default 42 is safe; old `None` behavior was non-reproducible anyway |
| Changing default seed alters results | Expected | This is the intended improvement -- results become reproducible |

## Security Considerations

None.

## Next Steps

- Run tests to verify correctness
- Consider adding a test for CV fold reproducibility (given same seed, same folds)
