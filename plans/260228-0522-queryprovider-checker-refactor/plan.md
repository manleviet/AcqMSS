---
title: "QueryProvider ConsistencyChecker Refactor"
description: "Replace ad-hoc solver usage in QueryProvider with ConsistencyChecker"
status: complete
priority: P2
effort: 2h
branch: main
tags: [refactor, query-provider, checker, DRY]
created: 2026-02-28
completed: 2026-02-28
---

# QueryProvider ConsistencyChecker Refactor

## Problem

`QueryProvider._satisfies_formula()` and `_try_generate_for_constraint()` create fresh PySAT solvers per call, duplicating solver management already handled by `ConsistencyChecker`.

## Goal

Replace ad-hoc solver usage with `ConsistencyChecker` passed from `QuacqRunner`, achieving DRY, better incremental perf, and unified SAT profiling.

## Phases

| # | Phase | File | Status | Est |
|---|-------|------|--------|-----|
| 1 | [Add get_model() to ConsistencyChecker](phase-01-checker-get-model.md) | `checker.py` | complete | 20m |
| 2 | [Refactor QueryProvider](phase-02-refactor-query-provider.md) | `query_provider.py` | complete | 30m |
| 3 | [Update QuAcq.learn() call sites](phase-03-update-quacq-callsites.md) | `quacq.py` | complete | 20m |
| 4 | [QuacqRunner passes checker+model](phase-04-runner-passes-checker.md) | `quacq_runner.py` | complete | 15m |
| 5 | [Update tests](phase-05-update-tests.md) | `test_quacq.py` | complete | 25m |

## Key Constraints

- `is_consistent(set_c)` enables set_c, disables rest in assumption universe
- `get_model()` only valid after `is_consistent()` returns True
- Condition 2 (`violates_clauses`) stays as boolean eval -- DO NOT convert to SAT
- NonIncremental must cache model before `solver.delete()`
- Part 4 assignment assumptions already in checker universe

## Dependencies

- Phase 2 depends on Phase 1 (needs `get_model()`)
- Phase 3 depends on Phase 2 (new signatures)
- Phase 4 depends on Phase 3 (new QueryProvider constructor)
- Phase 5 spans all phases

## Bonus Cleanup

Linter removed `background_clauses`, `negated_clauses`, and `root_assumption` from `QuAcq.learn()` signature since they became unused after the refactor. This was DRY improvement beyond the original plan scope.
