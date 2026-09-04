---
title: "Complete assumption stride constant extraction"
description: "Add _ASSUMPTION_SINGLE_STRIDE and replace remaining magic * 2 with _ASSUMPTION_PAIR_STRIDE"
status: completed
priority: P3
effort: 10m
branch: main
tags: [refactor, constants, task-preparation]
created: 2026-02-16
---

# Complete Assumption Stride Constant Extraction

## Summary

Full repo audit found 2 additional `* 2` usages with same assumption-pair semantic. Also add `_ASSUMPTION_SINGLE_STRIDE = 1`.

## Changes

| File | Line | Current | New |
|------|------|---------|-----|
| `explanation/models/task_preparation.py` | 31 | (after `_ASSUMPTION_PAIR_STRIDE`) | Add `_ASSUMPTION_SINGLE_STRIDE = 1` |
| `explanation/models/task_preparation.py` | 391 | `else 1` | `else _ASSUMPTION_SINGLE_STRIDE` |
| `acqmss/algorithms/task_preparation.py` | 118 | `(model.num_fm_constraints - 1) * 2` | `* _ASSUMPTION_PAIR_STRIDE` |
| `acqmss/algorithms/task_preparation.py` | 119 | `len(model.variables) * 2` | `* _ASSUMPTION_PAIR_STRIDE` |

## Success Criteria

- No magic `1` or `2` for assumption stride in task_preparation files
- All tests pass
