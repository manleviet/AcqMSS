---
title: "Unify assumption-based solving across all checker modes"
description: "All checkers use assumption IDs; non-incremental only differs by fresh solver per call"
status: completed
priority: P1
effort: 8h
branch: main
tags: [refactoring, unified-assumptions, checker-interface, type-safety]
created: 2026-02-13
revised: 2026-02-13
completed: 2026-02-13
---

# Unified Assumption-Based Solving

## Problem
Two parallel data pipelines: incremental uses `List[int]` (assumption IDs), non-incremental uses `List[List[List[int]]]` (clause lists). This causes:
- `_is_incremental` branching in CONGEN, GenerateNE, ACQMSS, Reduce
- Polymorphic `neg_c_map`: `Dict[int, int]` vs `Dict[str, List[List[int]]]`
- Duplicate task classes and task preparation classes
- SAT4JChecker excluded from CONGEN usage

## Solution
**All checkers use assumption IDs.** The ONLY difference between modes is solver lifecycle:
- **Incremental**: 1 persistent solver, uses PySAT `assumptions=` param
- **Non-incremental**: Fresh solver per `is_consistent()` call, same assumption logic
- **SAT4J**: Fresh process per call, assumptions encoded as unit clauses in CNF

This eliminates all `_is_incremental` branching. `neg_c_map` is naturally `Dict[int, int]`.

## Previous Approach (Superseded)
Original plan used "synthetic IDs" as a parallel lookup layer (`id_to_clauses`, `clauses_to_id`, `id_to_neg_clauses`). That was a band-aid. The new approach goes to the root by unifying the data representation entirely.

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Modify checker interface + implementations | COMPLETE | [phase-01](phase-01-checker-interface.md) |
| 2 | Unify task classes and task preparation | COMPLETE | [phase-02](phase-02-task-unification.md) |
| 3 | Simplify algorithms (remove _is_incremental) | COMPLETE | [phase-03](phase-03-algorithm-simplification.md) |
| 4 | Update QuAcq | COMPLETE | [phase-04](phase-04-quacq.md) |
| 5 | Update diagnosis operations | COMPLETE | [phase-05](phase-05-diagnosis-operations.md) |
| 6 | Tests and verification | COMPLETE | [phase-06](phase-06-tests.md) |

## Key Dependencies
- Phase 1 unblocks all others
- Phase 2 must precede phase 3
- Phases 3, 4, 5 can run in parallel after phase 2
- Phase 6 after all code changes

## Research Reports
- [Non-incremental mapping analysis](research/researcher-01-non-incremental-mapping.md)
- [QuAcq & GenerateNE analysis](research/researcher-02-quacq-generate-ne.md)

## Validation Log

### Session 1 -- 2026-02-13 (Original Plan)
Superseded by unified assumption approach.

### Session 2 -- 2026-02-13 (Plan Revision)
**Trigger:** Architecture analysis revealed unified assumption IDs is cleaner than synthetic ID lookup layer.

#### Key Decisions
1. **NonIncrementalPySATChecker** accepts `set_kb` + `assumptions`, creates fresh solver per call with same assumption logic as incremental
2. **SAT4JChecker** accepts `set_kb` + `assumptions`, uses unit clauses `[a]`/`[-a]` to encode assumptions in CNF file
3. **add_clause() + add_assumption()** added to checker interface for GenerateNE's dynamic clause addition
4. **One task preparation path** produces assumption-based output for all modes
5. **neg_c_map is naturally Dict[int, int]** -- no synthetic IDs, no side maps needed
