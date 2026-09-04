# Phase 03: Update cross_validation.py Caller

## Context Links

- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-refactor-runner.md)

## Overview

- **Priority**: High
- **Status**: complete
- **Description**: Update `n_fold_cross_validation_interactive()` signature and call site in `run_cv.py` to use new file-path-based `InteractiveRunner` constructor.

## Key Insights

- `n_fold_cross_validation_interactive()` currently takes `bias_clauses` + `feature_ids` as params → passed to old `InteractiveRunner` constructor
- New runner loads bias internally → these params removed
- `run_cv.py` currently pre-loads `bias.to_constraint_map()` + `bias.feature_ids` → no longer needed for interactive path
- `_run_cv_loop` line 410 passes `variables=feature_ids` → change to `variables=runner.feature_ids` (matches ConGen pattern at line 348: `variables=runner.model.variables`)

## Related Code Files

| File | Action |
|------|--------|
| `conacq/eval/cross_validation.py` | Remove `bias_clauses`/`feature_ids` params, update runner construction |
| `apps/run_cv.py` | Remove `bias_clauses`/`feature_ids` args from call |
| `conacq/eval/__init__.py` | No change (re-exports function name unchanged) |

## Implementation Steps

### 1. Update `n_fold_cross_validation_interactive()` signature

**Remove**: `bias_clauses`, `feature_ids` parameters

**Before** (line 358-372):
```python
def n_fold_cross_validation_interactive(
        positive_examples, negative_examples, n_folds,
        bias_clauses, feature_ids,  # REMOVE
        fm_path, bias_path, seed, solver_name='glucose4',
        max_queries=1000, query_mode='example_only',
        shuffle_each_fold=True, fold_data=None, shuffle_bias=False
) -> CrossValidationResult:
```

**After**:
```python
def n_fold_cross_validation_interactive(
        positive_examples, negative_examples, n_folds,
        fm_path, bias_path, seed, solver_name='glucose4',
        max_queries=1000, query_mode='example_only',
        shuffle_each_fold=True, fold_data=None, shuffle_bias=False
) -> CrossValidationResult:
```

### 2. Update runner construction (line 400-408)

**Before**:
```python
runner = InteractiveRunner(
    bias_clauses=bias_clauses, feature_ids=feature_ids,
    fm_path=fm_path, bias_path=bias_path,
    solver_name=solver_name, max_queries=max_queries, query_mode=query_mode
)
```

**After**:
```python
runner = InteractiveRunner(
    bias_path=bias_path, fm_path=fm_path,
    solver_name=solver_name, max_queries=max_queries, query_mode=query_mode
)
```

### 3. Update `_run_cv_loop` call (line 409-417)

Change `variables=feature_ids` → `variables=runner.feature_ids`:

```python
return _run_cv_loop(
    runner=runner, variables=runner.feature_ids,  # CHANGED
    ...
)
```

### 4. Update `run_cv.py` call site (line 162-176)

**Remove** `bias_clauses=bias.to_constraint_map()` and `feature_ids=bias.feature_ids`:

```python
cv_result = n_fold_cross_validation_interactive(
    positive_examples=pos,
    negative_examples=neg,
    n_folds=actual_n_folds,
    fm_path=model_config.oracle,
    bias_path=model_config.bias,
    seed=seed,
    solver_name=solver_name,
    max_queries=max_queries,
    query_mode=query_mode,
    fold_data=fold_data,
    shuffle_bias=shuffle_bias
)
```

### 5. Check if `bias` loading in `run_cv.py` still needed

Currently `run_cv.py` loads `bias` (line ~120) for:
- `bias.to_constraint_map()` → interactive CV (REMOVED)
- `bias.feature_ids` → interactive CV (REMOVED)
- Description resolution in result output

If bias is only used for description resolution, keep loading. Otherwise simplify.

## Todo List

- [ ] Remove `bias_clauses`/`feature_ids` from `n_fold_cross_validation_interactive()` signature
- [ ] Update runner construction in `cross_validation.py`
- [ ] Change `variables=feature_ids` → `variables=runner.feature_ids`
- [ ] Update call site in `run_cv.py` — remove extra args
- [ ] Update docstring for `n_fold_cross_validation_interactive()`
- [ ] Check if `bias` load in `run_cv.py` can be simplified

## Success Criteria

- `python -m apps.run_cv apps/conf/run_cv_config.toml -v` with `algorithm=interactive` works
- Same CV results (mean accuracy, KB) as before refactoring
- Signature matches ConGen version pattern: `(pos, neg, n_folds, bias_path, fm_path, ...)`

## Risk Assessment

- **Low**: Other callers of `n_fold_cross_validation_interactive()` — only `run_cv.py` uses it
- **Low**: `conacq/eval/__init__.py` re-exports — function name unchanged, only signature changes

## Next Steps

→ Phase 04: Test + verify both modes
