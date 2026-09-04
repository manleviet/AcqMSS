---
title: "Part 4 ConsistencyChecker for Pruning"
description: "Add feature assignment assumptions to BGData, replace violates_clauses with SAT-based pruning"
status: complete
priority: P2
effort: 2h
branch: main
tags: [quacq, checker, refactoring, sat]
created: 2026-02-28
completed: 2026-02-28
---

# Part 4 ConsistencyChecker for Pruning

## Problem

`_prune_rejecting_constraints` uses `violates_clauses()` (pure Boolean eval) -- misses implied violations only detectable through SAT solving with BG knowledge (Part 4 feature assignment assumptions).

## Approach

Extend BGData with Part 4 data (assignment_clauses, assignment_assumptions, pos/neg maps). Thread these through QuAcqTask -> QuAcqModel -> checker. Replace `violates_clauses()` with `checker.is_consistent()`.

## Phases

| # | Phase | File(s) | Status |
|---|-------|---------|--------|
| 1 | [BGData Part 4 fields](phase-01-bgdata-part4-fields.md) | `bg_data.py` | complete |
| 2 | [Oracle extract Part 4](phase-02-oracle-extract-part4.md) | `fm_oracle_model.py` | complete |
| 3 | [QuAcqTask Part 4](phase-03-quacq-task-part4.md) | `task_preparation.py` | complete |
| 4 | [QuAcqModel combined KB](phase-04-quacq-model-combined-kb.md) | `quacq_model.py` | complete |
| 5 | [Prune with checker](phase-05-prune-with-checker.md) | `quacq.py` | complete |
| 6 | [Runner params](phase-06-runner-params.md) | `quacq_runner.py` | complete |
| 7 | [Tests](phase-07-tests.md) | `test_quacq.py` | complete |

## Key Dependencies

- Phase 1 -> 2 -> 3 -> 4 -> 5 (strictly sequential data flow)
- Phase 6 depends on Phase 5 (learn() signature change)
- Phase 7 depends on all above

## Pre-existing Bug (Working Tree)

`_run_oracle_mode` (quacq_runner.py:248) calls `QuAcq.for_oracle(learn_oracle, ...)` without `checker` as first arg. Must be fixed in Phase 6.

`_learn_params_from_task` still contains `set_kb`/`assumptions` keys removed from `learn()` signature. Must be fixed in Phase 6.
