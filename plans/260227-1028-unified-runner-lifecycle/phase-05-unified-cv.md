# Phase 05: Clean Up CV Loop and Remove getattr Hacks

## Context
- Parent: [plan.md](plan.md)
- Depends on: Phase 01, 03, 04

## Overview
- **Priority**: Medium
- **Status**: Complete
- **Progress**: 100%
- **Description**: Update `_run_cv_loop` to use BaseRunner type hints; remove getattr hacks; simplify wrapper functions

## Key Insights
- `_run_cv_loop` already works polymorphically via duck typing
- Uses `getattr(run_result, 'n_mss', 0)`, `getattr(run_result, 'redundant_constraints', [])` etc.
- With BaseRunResult, shared fields are guaranteed — no getattr needed for those
- Runner-specific fields (n_mss, redundant_constraints, n_queries) still need conditional access
- `n_fold_cross_validation` and `n_fold_cross_validation_interactive` are thin wrappers

## Requirements
- Type `runner` param as `BaseRunner` in `_run_cv_loop`
- Type `run_result` as `BaseRunResult`
- Remove getattr for fields on BaseRunResult (guaranteed present)
- Keep getattr for truly optional runner-specific fields (n_mss, redundant_constraints)
- `variables` param extracted from `runner.feature_ids` inside _run_cv_loop (not passed separately)
- Consider merging wrapper functions or keeping for backward compat

## Related Code Files
- **Modify**: `conacq/eval/cross_validation.py`
- **Modify**: `conacq/eval/__init__.py` (if exports change)

## Implementation Steps

1. Import BaseRunner, BaseRunResult in cross_validation.py
2. Type `_run_cv_loop(runner: BaseRunner, ...)` — remove `variables` param (use `runner.feature_ids`)
3. Remove `getattr` for fields in BaseRunResult (bg_clauses, profiler_data, etc.)
4. Keep `getattr` for ConGen-specific fields (n_mss, redundant_constraints)
5. Update `CrossValidationFoldResult.n_mss` to `Optional[int] = None`
6. Update `n_fold_cross_validation()` — no longer pass `variables=runner.model.variables`
7. Update `n_fold_cross_validation_interactive()` — no longer pass `variables=runner.feature_ids`
8. Consider: merge wrapper functions into one `n_fold_cv(runner, ...)` or keep separate for clarity

## Todo
- [x] Add BaseRunner type hint to _run_cv_loop
- [x] Remove variables param (use runner.feature_ids)
- [x] Remove getattr for BaseRunResult fields
- [x] Update CrossValidationFoldResult.n_mss to Optional
- [x] Update wrapper functions
- [x] Verify callers (run_cv.py)
- [x] Add try/finally cleanup() in wrapper functions

## Completion Summary
- _run_cv_loop typed with BaseRunner, BaseRunResult type hints
- variables param removed (uses runner.feature_ids internally)
- getattr removed for shared BaseRunResult fields (guaranteed present)
- getattr kept for runner-specific fields (n_mss, redundant_constraints)
- CrossValidationFoldResult.n_mss: Optional[int] = None
- n_fold_cross_validation() and n_fold_cross_validation_interactive() simplified
- try/finally cleanup() added to both wrapper functions (resource cleanup)
- All CV callers (apps/run_cv.py) verified working

## Success Criteria
- _run_cv_loop typed with BaseRunner
- No getattr for shared fields
- Wrapper functions still work for apps/run_cv.py callers
- All CV tests pass

## Risk Assessment
- **Backward compatibility**: run_cv.py calls n_fold_cross_validation and n_fold_cross_validation_interactive. Keep both functions but simplify internals.
