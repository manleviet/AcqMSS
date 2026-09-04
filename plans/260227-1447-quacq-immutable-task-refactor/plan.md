---
title: "Refactor QuAcqTask to Immutable-Task Pattern"
description: "Move mutable state (learned_kb, bias, query tracking) from QuAcqTask into QuAcq algorithm, use set_c for bias"
status: pending
priority: P2
effort: 2h
branch: main
tags: [refactoring, quacq, architecture]
created: 2026-02-27
---

# Refactor QuAcqTask to Immutable-Task Pattern

## Goal

QuAcqTask currently holds mutable fields (`bias`, `learned_kb`, `n_queries`, `query_history`) that the QuAcq algorithm mutates during learning. This violates the immutable-task pattern used by ConGenTask/DiagnosisTask, where tasks are immutable inputs and algorithms produce separate outputs.

## Approach

1. Remove mutable fields and mutation methods from QuAcqTask
2. Store the initial bias constraint IDs in the inherited `set_c` field (matching ConGenTask)
3. Move mutable state (remaining_bias, learned_kb, n_queries, query_history) into QuAcq algorithm as local variables
4. Thread mutable state through FindScope/FindC as parameters instead of task mutation
5. Update QuAcqResult to carry all output state; update consumers to read from result

## Phases

| Phase | Description | Status | Effort |
|-------|------------|--------|--------|
| [Phase 1](phase-01-make-task-immutable.md) | Make QuAcqTask immutable: remove mutable fields, use set_c | pending | 45m |
| [Phase 2](phase-02-internalize-state-in-algorithm.md) | Move mutable state into QuAcq algorithm and thread through FindScope/FindC | pending | 45m |
| [Phase 3](phase-03-update-consumers-and-tests.md) | Update runner, CV, tests; verify all tests pass | pending | 30m |

## Key Insight

`task.bias` (set of int) maps directly to `set_c` (list of int) from DiagnosisTask. ConGenTask already uses `set_c` for bias assumption IDs. After refactoring, both tasks use `set_c` identically.

## Files Changed

- `conacq/algorithms/quacq/task_preparation.py` — QuAcqTask + QuAcqTaskPreparation
- `conacq/algorithms/quacq/quacq.py` — QuAcq + QuAcqResult
- `conacq/algorithms/quacq/findscope.py` — Thread remaining_bias param
- `conacq/algorithms/quacq/findc.py` — Thread remaining_bias + record_query callback
- `conacq/example_generators/query_generator.py` — Read set_c instead of bias
- `conacq/runners/quacq_runner.py` — Read from result, not task
- `tests/test_quacq.py` — Update assertions
