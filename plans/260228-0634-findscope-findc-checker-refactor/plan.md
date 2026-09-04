---
title: "FindScope/FindC ConsistencyChecker Refactor"
description: "Replace violates_clauses with checker.is_consistent in FindScope/FindC for correctness"
status: complete
priority: P2
effort: 2h
branch: main
tags: [refactoring, correctness, quacq]
created: 2026-02-28
---

# FindScope/FindC ConsistencyChecker Refactor

## Problem

`FindScope._prune_rejecting_partial` and `FindC.run` use `violates_clauses()` (pure Boolean eval) — misses implied violations detectable only via SAT solving with full KB. `QuAcq._prune_rejecting_constraints` already uses `checker.is_consistent()` correctly.

## Approach

Inject `ConsistencyChecker` + `QuAcqModel` into FindScope/FindC (same DI pattern as QuAcq). Replace `violates_clauses` with `checker.is_consistent([root] + config_assumptions + [c_id])`. Remove scope filter (`c_vars.issubset(R)`) from FindScope — SAT handles unassigned vars.

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Inject checker into FindScope/FindC](phase-01-inject-checker-into-findscope-findc.md) | complete | 45min |
| 2 | [Update QuAcq callsites](phase-02-update-quacq-callsites.md) | complete | 30min |
| 3 | [Update tests](phase-03-update-tests.md) | complete | 45min |

## Key Decisions

- Share QuAcq's existing checker instance (no overhead)
- Add `root_assumption: int` + `model: QuAcqModel` to both `run()` signatures
- Remove `violates_clauses`/`get_constraint_vars` imports from FindScope/FindC
- Remove `c_vars.issubset(R)` scope filter (SAT solver handles free vars)
- Pattern: `checker.is_consistent([root] + model.config_to_assumptions(e) + [c_id])`

## Files Modified

- `conacq/algorithms/quacq/findscope.py` (Phase 1)
- `conacq/algorithms/quacq/findc.py` (Phase 1)
- `conacq/algorithms/quacq/quacq.py` (Phase 2)
- `tests/test_quacq.py` (Phase 3)

## Risk

- Low: same proven pattern as `_prune_rejecting_constraints`
- Monitor SAT call count in FindScope recursive binary search
- No external API change; internal DI only

## Dependencies

- ConsistencyChecker and QuAcqModel already exist
- `model.config_to_assumptions()` already proven in QuAcq._prune_rejecting_constraints

## Brainstorm Report

- [brainstorm-260228-0620-findscope-findc-checker-refactor.md](../reports/brainstorm-260228-0620-findscope-findc-checker-refactor.md)
