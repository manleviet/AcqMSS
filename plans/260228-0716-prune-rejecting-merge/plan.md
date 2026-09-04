---
title: "Extract shared prune_rejecting into sat_utils"
description: "Merge duplicate pruning logic from FindScope and QuAcq into single free function"
status: completed
priority: P3
effort: 30m
branch: main
tags: [refactor, dry, quacq]
created: 2026-02-28
completed: 2026-02-28
---

# Extract Shared `prune_rejecting` into `sat_utils.py`

## Context

`FindScope._prune_rejecting_partial` (findscope.py:79-105) and `QuAcq._prune_rejecting_constraints` (quacq.py:270-287) share identical core pruning loop. Extracting to `sat_utils.py` ensures single update point when pruning logic evolves.

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| [Phase 1](phase-01-extract-and-rewire.md) | Extract `prune_rejecting` to sat_utils, rewire both callers | Completed |

## Files Affected

- `conacq/algorithms/quacq/sat_utils.py` — add `prune_rejecting()`
- `conacq/algorithms/quacq/findscope.py` — thin wrapper calling shared function
- `conacq/algorithms/quacq/quacq.py` — thin wrapper calling shared function

## Success Criteria

- All existing tests pass (`PYTHONPATH=. pytest tests/ -v`)
- No behavior change — callers preserve decorators, logging, partial extraction
- Single source of truth for pruning loop logic
