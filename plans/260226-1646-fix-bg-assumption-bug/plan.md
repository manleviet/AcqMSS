---
title: "Fix BG assumption ID bug in QuAcq oracle-mode"
description: "BG assumption IDs misinterpreted as SAT literals in _find_conflict and QueryGenerator"
status: complete
priority: P1
effort: 2h
branch: main
tags: [bugfix, quacq, bg-handling, dry]
created: 2026-02-26
---

# Fix BG Assumption ID Bug in QuAcq Oracle-Mode

## Problem

`QuAcqTask.background` stores BG assumption IDs (e.g., `[5, 6]`). Two functions treat them as SAT variable literals via `isinstance(task.background[0], int)`, wrapping each as unit clause `[[aid]]`. This means BG constraints are **effectively ignored** in oracle-mode for:
- Query generation (`QueryGenerator._try_generate_for_constraint`)
- Conflict detection (`QuAcq._find_conflict`)

REDUCE path is unaffected (uses assumption IDs correctly via `set_bg`).

## Fix Strategy — Dual Storage

Add `background_clauses: List[List[int]]` to `QuAcqTask` containing raw BG clauses (no assumption guards). Keep `background: List[int]` for REDUCE. Update SAT-path consumers to prefer `background_clauses` when available.

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Add `background_clauses` field + populate in preparation | complete | [phase-01](phase-01-bg-clauses-field.md) |
| 2 | Fix BG handling in `_find_conflict` and `QueryGenerator` | complete | [phase-02](phase-02-fix-bg-consumers.md) |
| 3 | Extract shared duck-typing helpers (DRY) | complete | [phase-03](phase-03-extract-task-compat.md) |
| 4 | Narrow `_apply_reduce` exception handling | complete | [phase-04](phase-04-narrow-exceptions.md) |
| 5 | Tests | complete | [phase-05](phase-05-tests.md) |

## Key Dependencies

- Phase 2 depends on Phase 1 (field must exist before consumers use it)
- Phase 3 independent (DRY refactor, can parallel with 1-2)
- Phase 4 independent
- Phase 5 depends on all others

## Source

Code review: `plans/reports/code-reviewer-260226-1637-quacq-assumption-migration.md`
