---
title: "Move result resolution logic from ConGenRunner to ConGenModel"
description: "Extract assumption ID resolution into ConGenModel.resolve_result(), remove bg_clauses from ConGenResult"
status: complete
priority: P3
effort: 1h
branch: main
tags: [refactor, encapsulation, DRY]
created: 2026-02-25
---

# Resolve Result Refactoring

## Problem

ConGenRunner reaches into ConGenModel internals (`constraint_map`, `description_provider`) to resolve assumption IDs → names → clauses. This violates encapsulation.

Additionally, `ConGenResult.bg_clauses` duplicates BG data that ConGenModel already owns via `task.set_b`.

## Changes

### Phase 1: ConGenModel + ConGenResult refactoring

| File | Change |
|---|---|
| `conacq/algorithms/acqmss/congen_model.py` | Add `_resolve_ids()` helper + `resolve_result()` method |
| `conacq/algorithms/acqmss/congen.py` | Remove `bg_clauses` field from `ConGenResult`, remove `bg_clauses` construction in `acquire()` |
| `conacq/runners/congen_runner.py` | Replace lines 241-255 with `model.resolve_result(result)` |
| `tests/test_congen.py` | Remove `result.bg_clauses` assertions (3 occurrences) |

### Phase 2: Test & verify

Run full test suite, fix any regressions.

## Phases

- [phase-01-implement.md](phase-01-implement.md) — Implementation (45min)
- Phase 2: Test & verify (15min) — inline, no separate doc needed

## Key Decisions

- `ConGenRunResult.bg_clauses` **stays** — downstream consumers (cross_validation, result_loader, kb_comparator) use it
- `ConGenResult.bg_clauses` **removed** — model now owns this resolution
- Return plain tuple `(bg_clauses, kb_clauses, kb_names, redundant_names)`
