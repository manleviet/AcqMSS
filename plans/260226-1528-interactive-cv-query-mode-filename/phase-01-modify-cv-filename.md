---
parent: plan.md
status: complete
priority: P3
---

# Phase 01: Modify CV Filename Logic

## Overview
Add `query_mode` suffix to output filename in `run_cv.py` for interactive algorithm only.

## Related Code Files
- **Modify:** `apps/run_cv.py` — line 187

## Implementation Steps

1. Replace the single `cv_file` assignment (line 187) with conditional:
   ```python
   # Include query_mode in filename for interactive to avoid overwrites
   if algorithm == 'interactive':
       cv_file = output_dir / f"{model_config.name}_cv_{mode_name}_{query_mode}.json"
   else:
       cv_file = output_dir / f"{model_config.name}_cv_{mode_name}.json"
   ```

2. Run tests: `PYTHONPATH=. pytest tests/ -v`

## Todo
- [x] Modify filename logic in `run_cv.py`
- [x] Run tests to verify no regressions

## Success Criteria
- Interactive runs produce files like `model_cv_incremental_example_only.json`
- ConGen runs produce unchanged filenames like `model_cv_incremental.json`
- All existing tests pass
- `run_compare.py` still discovers new files via `*_cv_*.json` glob
