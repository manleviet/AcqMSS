# Phase 02: Verify Callers + Exports

## Context Links

- Source: `acqmss/eval/__init__.py`
- Callers: `apps/run_congen_eval.py`, `apps/run_interactive_eval.py`
- Plan: [plan.md](plan.md)

## Overview

- **Priority**: P2
- **Status**: completed
- **Description**: Verify public API unchanged, exports correct, callers unaffected.

## Key Insights

- Public function signatures are **identical** before/after refactor
- `__init__.py` re-exports both functions — no changes needed
- Only 2 callers in `apps/`; no direct test calls to CV functions
- `_run_cv_loop()` is private — not exported

## Requirements

- No changes to `__init__.py` exports
- No changes to caller code in `apps/`
- `_run_cv_loop` must NOT appear in `__all__`

## Related Code Files

### Files to Verify (no changes expected)
- `acqmss/eval/__init__.py` — exports `n_fold_cross_validation`, `n_fold_cross_validation_interactive`
- `apps/run_congen_eval.py:234` — calls `n_fold_cross_validation()`
- `apps/run_interactive_eval.py:228` — calls `n_fold_cross_validation_interactive()`
- `docs/congen.md:364` — references `n_fold_cross_validation` in example

## Implementation Steps

### Step 1: Verify `__init__.py`

Confirm exports still include:
```python
from .cross_validation import (
    n_fold_cross_validation,
    n_fold_cross_validation_interactive,
    CrossValidationResult,
    CrossValidationFoldResult
)
```
No changes needed — `_run_cv_loop` is private, not exported.

### Step 2: Verify caller signatures match

`apps/run_congen_eval.py:234`:
```python
cv_result = n_fold_cross_validation(
    positive_examples=..., negative_examples=..., n_folds=...,
    bias_path=..., fm_path=..., seed=...,
    solver_name=..., is_incremental=...,
    fold_data=..., shuffle_bias=...
)
```
All params preserved in wrapper. OK.

`apps/run_interactive_eval.py:228`:
```python
cv_result = n_fold_cross_validation_interactive(
    positive_examples=..., negative_examples=..., n_folds=...,
    bias_clauses=..., feature_ids=...,
    fm_path=..., bias_path=..., seed=...,
    solver_name=..., max_queries=..., query_mode=...,
    fold_data=..., shuffle_bias=...
)
```
All params preserved in wrapper. OK.

### Step 3: Verify docs reference

`docs/congen.md:364` references `from acqmss.eval.cross_validation import n_fold_cross_validation` — unchanged.

## Todo List

- [ ] Confirm `__init__.py` needs no edits
- [ ] Confirm `apps/run_congen_eval.py` call site unchanged
- [ ] Confirm `apps/run_interactive_eval.py` call site unchanged
- [ ] Confirm `docs/congen.md` reference still valid

## Success Criteria

- Zero changes to files outside `acqmss/eval/cross_validation.py`
- All callers work without modification

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missed caller | Low | Grep confirmed only 2 callers + 1 doc ref |

## Next Steps

- Phase 03: Run tests + lint
