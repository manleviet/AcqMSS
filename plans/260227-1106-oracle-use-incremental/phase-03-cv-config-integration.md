# Phase 3: CV + Config Integration

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-runner-oracle-plumbing.md)

## Overview
- Priority: P1
- Status: complete
- Wire `use_incremental` through CV functions and TOML config for interactive algorithm

## Key Insights
- `run_cv.py` iterates `solver_modes` (incremental/non-incremental) but **never passes `is_incremental` to interactive CV**
- `n_fold_cross_validation_interactive()` doesn't accept `use_incremental` param
- `InteractiveRunner` creation in CV function ignores solver mode entirely
- TOML config `solver_mode` already exists in `[evaluation]` — works for congen, needs wiring for interactive

## Related Code Files
- `conacq/eval/cross_validation.py` — add `use_incremental` to `n_fold_cross_validation_interactive()`
- `apps/run_cv.py` — pass `is_incremental` to interactive CV call
- `apps/conf/run_interactive_config.toml` — document use_incremental option
- `apps/run_interactive.py` — add use_incremental support (if applicable)

## Implementation Steps

1. **`n_fold_cross_validation_interactive()`** — add `use_incremental: bool = True` param, pass to InteractiveRunner
   ```python
   def n_fold_cross_validation_interactive(..., use_incremental: bool = True, ...):
       runner = InteractiveRunner(
           bias_path=bias_path, fm_path=fm_path,
           solver_name=solver_name, max_queries=max_queries,
           query_mode=query_mode, use_incremental=use_incremental)
   ```

2. **`apps/run_cv.py`** — pass `is_incremental` to interactive CV call (line ~162)
   ```python
   cv_result = n_fold_cross_validation_interactive(
       ..., use_incremental=is_incremental, ...)
   ```

3. **`apps/conf/run_interactive_config.toml`** — no change needed (standalone runner doesn't use solver_mode loop; CV config already has `solver_mode`)

## Todo
- [x] Add use_incremental param to n_fold_cross_validation_interactive()
- [x] Pass is_incremental in run_cv.py interactive branch
- [x] Verify run_interactive.py (standalone) — add if needed

## Success Criteria
- Interactive CV runs respect solver_mode config (incremental/non-incremental)
- Both algorithms benchmarked under same Oracle solver mode
- Existing CV config works without changes
