---
title: "Remove DescriptionProvider from QuAcq.learn()"
description: "Refactor QuAcq to resolve constraint names in runner layer, matching ConGen pattern"
status: completed
priority: P3
effort: 1h
branch: main
tags: [refactor, quacq, separation-of-concerns]
created: 2026-02-28
---

# Remove DescriptionProvider from QuAcq.learn()

## Problem

QuAcq passes `DescriptionProvider` into `learn()` and resolves names inside `_build_result()`. This violates SRP — the algorithm shouldn't handle presentation. ConGen pattern is cleaner: algorithm returns raw IDs, runner resolves names via `model.resolve_kb()`.

## Context

- Brainstorm: `plans/reports/brainstorm-260228-0131-quacq-description-provider-refactor.md`
- `QuAcqModel.resolve_kb()` already exists (line 120 of quacq_model.py)
- Runner already calls `resolve_kb()` at line 200 of quacq_runner.py for clauses
- 4 test call sites pass `description_provider=` to `learn()`

## Phases

| Phase | Description | Status | File |
|-------|------------|--------|------|
| 01 | Remove from algorithm | completed | [phase-01](phase-01-remove-from-algorithm.md) |
| 02 | Update runner to resolve names | completed | [phase-02](phase-02-update-runner.md) |
| 03 | Update tests and docs | completed | [phase-03](phase-03-update-tests.md) |

## Key Observations

1. `resolve_kb()` already on QuAcqModel — no new method needed
2. Runner already calls `resolve_kb()` for clauses — just also use returned names
3. `_build_result()` fallback (`str(id)`) confirms provider was always optional
4. `__init__.py` docstring example includes `description_provider=` — update needed
