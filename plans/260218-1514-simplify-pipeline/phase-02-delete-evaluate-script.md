# Phase 2: Delete `evaluate_congen_results.py`

**Parent**: [plan.md](plan.md) | **Depends on**: Phase 1
**Priority**: High | **Status**: pending | **Effort**: 10m

## Overview

Delete `evaluate_congen_results.py` and its config. This script is entirely redundant — `_cv_*.json` already contains all metrics it computes, and no paper table consumes its output.

## Related Code Files

- `apps/evaluate_congen_results.py` — DELETE
- `apps/conf/evaluate_congen_config.toml` — DELETE
- `data/kb_eval/` — output directory (keep existing results, just stop generating new)

## Implementation Steps

1. Delete `apps/evaluate_congen_results.py`
2. Delete `apps/conf/evaluate_congen_config.toml`
3. Verify no other script imports from `evaluate_congen_results.py`
4. Run tests: `PYTHONPATH=. pytest tests/ -v`

## Todo

- [ ] Delete script
- [ ] Delete config
- [ ] Verify no imports
- [ ] Tests pass

## Success Criteria

- Files deleted
- No broken imports
- Tests pass
