---
title: "Move GenerateNE out of ConGen"
description: "Refactor to remove checker mutation by moving NE generation before ConGen"
status: completed
priority: P2
effort: 2h
branch: main
tags: [refactoring, congen_root, checker, clean-architecture]
created: 2026-02-13
---

# Move GenerateNE Out of CONGEN

## Goal

Eliminate `add_clause`/`add_assumption` from `ConsistencyChecker` by moving NE generation
to callers. CONGEN receives pre-computed NE via `task.set_ne` instead of generating it internally.

## Why

- `add_clause`/`add_assumption` mutate checker state, violating clean separation
- These methods are ONLY called from `GenerateNE`
- NE generation's QuickXPlain calls are unaffected by the added clauses (proven by assumption semantics)
- Removing mutation makes checker a pure read-only query interface

## New Flow

```
1. task_preparation -> base task (unchanged)
2. Caller: temp NonIncrementalPySATChecker(task.set_kb, task.assumptions)
3. Caller: GenerateNE.generate() -> NEResult with new_clauses + new_assumptions
4. Caller: merge NE data into task (set_kb, assumptions, set_ne, neg_c_map)
5. Caller: create final checker with complete data
6. CONGEN.acquire(task) -> uses task.set_ne directly (no GenerateNE call)
```

## Phases

| # | Phase | Status | Files |
|---|-------|--------|-------|
| 1 | [Modify GenerateNE](phase-01-modify-generate-ne.md) | completed | generate_ne.py |
| 2 | [Update Task and CONGEN](phase-02-update-task-and-congen.md) | completed | task.py, congen.py |
| 3 | [Update Callers](phase-03-update-callers.md) | completed | run_congen.py, congen_runner.py |
| 4 | [Cleanup Checker](phase-04-cleanup-checker.md) | completed | checker.py |
| 5 | [Update Tests](phase-05-update-tests.md) | completed | test_congen.py |

## Key Constraint

Phases MUST be implemented in order. Phase 4 (remove add_clause/add_assumption)
can only happen after phases 1-3 are complete.

## Success Criteria

- All existing tests pass with identical results
- `add_clause` and `add_assumption` removed from `ConsistencyChecker` and all subclasses
- `GenerateNE` no longer mutates checker
- CONGEN receives NE via `task.set_ne`
