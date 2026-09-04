---
title: "Unified Shuffle-After-Prepare Refactor"
description: "Simplify both runners to shuffle set_c after prepare(), build model once in __init__"
status: completed
priority: P3
effort: 1h
branch: main
tags: [refactor, runners, shuffle, consistency]
created: 2026-02-28
---

# Unified Shuffle-After-Prepare Refactor

## Context
- Brainstorm: [brainstorm-260228-0006](../reports/brainstorm-260228-0006-unified-shuffle-after-prepare.md)

## Problem
- ConGenRunner shuffles `constraint_map` before `prepare()` + needs `_original_bias_constraint_order` snapshot — unnecessary complexity
- QuAcqRunner rebuilds model every `run()` (expensive negation recomputed each time)
- Two different shuffle patterns for identical goal

## Solution
Both runners: build model once in `__init__`, shuffle `task.set_c` after `prepare()` in `run()`.

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Simplify ConGenRunner shuffle | complete | [phase-01](phase-01-simplify-congen-shuffle.md) |
| 2 | Move QuAcqRunner build to init | complete | [phase-02](phase-02-quacq-build-to-init.md) |
| 3 | Test & verify | complete | [phase-03](phase-03-test-verify.md) |

## Key Files
- `conacq/runners/congen_runner.py`
- `conacq/runners/quacq_runner.py`
- `tests/test_congen.py`
- `tests/test_quacq.py`

## Success Criteria
- All existing tests pass
- Same seeds → same KB output (deterministic)
- Both runners use identical shuffle-after-prepare pattern
- `_original_bias_constraint_order` removed from ConGenRunner
- `_use_incremental` and `_feature_ids` removed from QuAcqRunner
