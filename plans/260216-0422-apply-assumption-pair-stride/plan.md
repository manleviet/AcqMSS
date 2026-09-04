---
title: "Apply _ASSUMPTION_PAIR_STRIDE constant"
description: "Replace magic number 2 with named constant across task preparation modules"
status: complete
priority: P3
effort: 30m
branch: main
tags: [refactor, constants, task-preparation]
created: 2026-02-16
---

# Apply `_ASSUMPTION_PAIR_STRIDE` Constant

## Summary

Replace all occurrences of magic number `2` used as assumption pair stride with `_ASSUMPTION_PAIR_STRIDE` constant. Currently defined only in `acqmss/oracle/fm_oracle_model.py`; needs to be shared across 3 files.

## Current State

- Constant defined in `acqmss/oracle/fm_oracle_model.py:19`, used on lines 116, 242
- `acqmss/algorithms/task_preparation.py:255` uses `step = 2` (used on lines 258, 261, 263)
- `explanation/models/task_preparation.py:387` uses `step = 2 if has_negated_forms else 1`
- `explanation/models/task_preparation.py:528,530` uses literal `2` in range/division

## Design Decision

Move `_ASSUMPTION_PAIR_STRIDE` to `explanation/models/task_preparation.py` (the base module). Both `acqmss/oracle/fm_oracle_model.py` and `acqmss/algorithms/task_preparation.py` already import from it. No new cross-package dependencies introduced.

## Import Graph (verified)

```
explanation/models/task_preparation.py  <-- CONSTANT LIVES HERE (new)
    ^                    ^
    |                    |
acqmss/algorithms/       acqmss/oracle/
task_preparation.py      fm_oracle_model.py
(already imports)        (already imports)
```

## Phases

| Phase | File | Status |
|-------|------|--------|
| [Phase 1](phase-01-refactor-stride-constant.md) | Move constant + update all 3 files | Complete |

## Success Criteria

- No magic `2` remains for assumption pair stride in any of the 3 files
- All tests pass (`PYTHONPATH=. pytest tests/ -v`)
- No new cross-package dependencies
