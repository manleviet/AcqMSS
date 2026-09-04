---
title: "Extract task preparation from FMOracleModel"
description: "Move set_c computation out of FMOracleModel into FMOracleTaskPreparation, cache base_set_c, return self from with_configuration"
status: complete
priority: P2
effort: 1h
branch: main
tags: [refactoring, oracle, separation-of-concerns]
created: 2026-02-18
---

# Extract Task Preparation from FMOracleModel

## Context
- Brainstorm: `plans/reports/brainstorm-260218-0137-oracle-task-preparation-extraction.md`
- Target: `conacq/oracle/fm_oracle_model.py`
- Caller: `conacq/oracle/fm_oracle.py`
- Tests: `tests/test_oracle_model.py`

## Problem
`FMOracleModel` mixes model state with task preparation logic. `_compute_base_set_c()` and set_c computation in `with_configuration()` are preparation concerns.

## Solution
1. Cache `base_set_c` during `prepare()` via direct model assignment
2. Remove `_compute_base_set_c()` entirely
3. Add `configuration` param to `prepare()`
4. `with_configuration()` returns `self` instead of `list`

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Core refactoring | complete | [phase-01](phase-01-core-refactoring.md) |
| 2 | Update callers & tests | complete | [phase-02](phase-02-callers-and-tests.md) |

## Files Modified
- `conacq/oracle/fm_oracle_model.py` — FMOracleModel + FMOracleTaskPreparation
- `conacq/oracle/fm_oracle.py` — FeatureModelOracle.is_valid (minor)
- `tests/test_oracle_model.py` — return type assertions

## Success Criteria
- All tests pass: `PYTHONPATH=. pytest tests/test_oracle_model.py -v`
- `_compute_base_set_c` removed
- `with_configuration` returns `FMOracleModel`
- `prepare(configuration=None)` signature works
