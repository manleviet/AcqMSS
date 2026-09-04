---
title: "QuAcqTask Inherits DiagnosisTask"
description: "Refactor QuAcqTask to inherit from DiagnosisTask, eliminating duplicate fields and aligning with task hierarchy"
status: completed
priority: P2
effort: 1h
branch: main
tags: [refactoring, interactive, task-hierarchy, DRY]
created: 2026-02-27
completed: 2026-02-27
---

# QuAcqTask Inherits DiagnosisTask

## Goal

Make `QuAcqTask` inherit from `DiagnosisTask` to eliminate duplicate fields (`set_kb`, `assumptions`, `negation_map`) and align with the existing task hierarchy (`DiagnosisTask → TestCaseTask → ConGenTask`).

## Context

- Brainstorm: `plans/reports/brainstorm-260227-0951-quacqtask-inherit-diagnosistask.md`
- DiagnosisTask: `explanation/models/task_preparation.py`
- QuAcqTask: `conacq/algorithms/interactive/quacq_task.py`

## Phases

| # | Phase | Status | Files |
|---|-------|--------|-------|
| 1 | [Refactor QuAcqTask class](phase-01-refactor-quacqtask.md) | completed | quacq_task.py, interactive_task_preparation.py |
| 2 | [Rename background → set_b across codebase](phase-02-rename-background.md) | completed | quacq.py, learner.py, _task_compat.py, query_generator.py, task.py |
| 3 | [Update tests](phase-03-update-tests.md) | completed | test_interactive.py |

## Key Decisions

- `bias: Set[int]` stays QuAcq-specific — NOT mapped to `set_c`
- `set_c` from parent stays empty/unused
- `background` renamed to `set_b` (inherited from DiagnosisTask)
- `background_clauses` stays QuAcqTask-specific (no parent equivalent)

## Success Criteria

- All tests pass (`PYTHONPATH=. pytest tests/ -v`)
- QuAcqTask inherits DiagnosisTask
- No duplicate field declarations for `set_kb`, `assumptions`, `negation_map`
- `prepare_kb()` still works with inherited fields
