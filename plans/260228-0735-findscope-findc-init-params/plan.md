---
title: "Move record_query & root_assumption to __init__"
description: "Refactor FindScope/FindC to accept invariant params at construction time"
status: completed
priority: P3
effort: 30m
branch: main
tags: [refactoring, quacq, DRY, KISS]
created: 2026-02-28
---

# Move record_query & root_assumption to __init__

## Problem
`record_query` and `root_assumption` are passed through `run()` method signatures but never change during instance lifetime. Both are threaded through recursive calls and sub-methods unnecessarily.

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Refactor FindScope & FindC + update caller | Complete | [phase-01](phase-01-refactor-init-params.md) |

## Files Modified
- `conacq/algorithms/quacq/findscope.py`
- `conacq/algorithms/quacq/findc.py`
- `conacq/algorithms/quacq/quacq.py`

## Success Criteria
- All existing tests pass unchanged
- `record_query` and `root_assumption` removed from all `run()` / `_narrow_with_generator()` / `_prune_rejecting_partial()` signatures
- Recursive `FindScope.run()` calls no longer thread these params
