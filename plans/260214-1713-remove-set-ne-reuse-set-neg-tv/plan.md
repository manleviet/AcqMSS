---
title: "Remove set_ne, reuse set_neg_tv from parent TestCaseTask"
description: "Eliminate redundant ConGenTask.set_ne by reusing inherited TestCaseTask.set_neg_tv"
status: complete
priority: P2
effort: 2h
branch: main
tags: [refactor, DRY, task-hierarchy]
created: 2026-02-14
---

# Remove set_ne, Reuse set_neg_tv

## Problem

`ConGenTask.set_ne` duplicates `TestCaseTask.set_neg_tv`. Both hold negated negative example/test case assumption IDs (`List[int]`). ConGenTask docstring incorrectly says `set_neg_tv` has "no use."

## Solution

1. Remove `set_ne` field from `ConGenTask`
2. Update `merge_ne_into_task()` to write to `set_neg_tv`
3. Rename `set_ne` param to `set_neg_tv` in ConGen, AcqMSS, Reduce APIs
4. Update all callers: `task.set_ne` -> `task.set_neg_tv`
5. Remove redundant `get_ne()` from ConGenModel (existing `get_neg_tv()` suffices)
6. Update docs (CLAUDE.md, code-standards, system-architecture)

## Phases

| # | Phase | Status | Files |
|---|-------|--------|-------|
| 1 | [Update ConGenTask & merge function](phase-01-update-congen-task.md) | complete | 3 files |
| 2 | [Update algorithm params & callers](phase-02-update-generate-ne-consumers.md) | complete | 7 files |
| 3 | [Update tests & documentation](phase-03-update-tests-and-docs.md) | complete | 5 files |

## Key Insight

`ConGenModel.get_neg_tv()` already exists and returns `task.set_neg_tv`. After this refactor, `get_ne()` is removed and `get_neg_tv()` serves both CONGEN and diagnosis use cases.

## Dependencies

- No external dependencies
- Pure rename refactor; no behavioral changes
- Tests must pass in both incremental and non-incremental modes

## Reports

- [Impact Analysis](reports/impact-analysis.md)
