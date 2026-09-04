---
parent: ./plan.md
status: complete
priority: P3
effort: 15m
---

# Phase 1: Create Package + Update Scripts

## Overview

Make `apps/` a Python package and update all script docstrings from `PYTHONPATH=. python apps/x.py` to `python -m apps.x`.

## Requirements

- Create `apps/__init__.py` (empty)
- Update docstring Usage sections in all 10 scripts
- Update comment headers in all TOML configs that reference the old pattern

## Related Code Files

### Create
- `apps/__init__.py`

### Modify (docstrings)
- `apps/run_congen.py`
- `apps/run_interactive.py`
- `apps/run_cv.py`
- `apps/run_compare.py`
- `apps/describe_kb.py`
- `apps/extract_results.py`
- `apps/generate_bias_config.py`
- `apps/generate_bias_files.py`
- `apps/generate_cv_folds.py`
- `apps/generate_examples.py`

### Modify (comment headers)
- `apps/conf/run_congen_config.toml`
- `apps/conf/run_interactive_config.toml`
- `apps/conf/run_cv_config.toml`
- `apps/conf/run_compare_config.toml`
- `apps/conf/describe_kb_config.toml`
- `apps/conf/generate_bias_config.toml`
- `apps/conf/generate_bias_files_config.toml`
- `apps/conf/generate_cv_folds_config.toml`
- `apps/conf/generate_examples_config.toml`
- `apps/conf/test_eval_config.toml`

## Implementation Steps

1. Create empty `apps/__init__.py`
2. For each script: find `PYTHONPATH=. python apps/X.py` in docstring, replace with `python -m apps.X`
3. For each TOML config: find `PYTHONPATH=. python apps/X.py` in comment, replace with `python -m apps.X`
4. Verify: `python -m apps.run_congen --help` works without PYTHONPATH

## Todo

- [ ] Create `apps/__init__.py`
- [ ] Update 10 script docstrings
- [ ] Update 10 TOML config comments
- [ ] Smoke test `python -m apps.run_congen --help`

## Success Criteria

- `python -m apps.run_congen --help` works without PYTHONPATH=.
- All docstrings show new pattern
- All TOML comments show new pattern
- Existing `PYTHONPATH=. python apps/x.py` still works (backward compat)

## Risk Assessment

- **Low**: No logic changes, only docstrings/comments + 1 empty file
