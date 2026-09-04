---
title: "Refactor ConGenTaskPreparation.prepare()"
description: "Extract long prepare() method into focused helpers, remove dead code, add guards"
status: complete
priority: P2
effort: 3h
branch: main
tags: [refactoring, code-quality, task-preparation]
created: 2026-02-15
---

# Refactor ConGenTaskPreparation.prepare()

## Problem

`prepare()` in `task_preparation.py` is ~190 lines with inlined NE generation logic, ~20 lines of commented-out code, duplicated combine/negate NE blocks, and missing guard clauses. `ConGenModel.prepare()` in `congen_model.py` has ~80 lines of commented-out code.

## Scope

| File | Current Lines | Target |
|------|--------------|--------|
| `acqmss/algorithms/task_preparation.py` | ~351 | ~250 (delegate to GenerateNE, dead code removal) |
| `acqmss/algorithms/generate_ne.py` | ~120 | ~140 (modified to match inline behavior) |
| `acqmss/algorithms/congen_model.py` | TBD | Remove ~80 lines commented code |

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Refactor GenerateNE & extract helpers](phase-01-extract-helpers.md) | complete | 60min |
| 2 | [Cleanup dead code & add guards](phase-02-cleanup-and-guards.md) | complete | 20min |
| 3 | [Add unit tests for extracted methods](phase-03-add-unit-tests.md) | skipped | — |
| 4 | [Run tests & verify](phase-04-test-verify.md) | complete | 15min |

## Key Constraint

Must preserve **exact SAT encoding behavior** — same assumption IDs, same clause structure, same output. Tests must pass without modification.

## Dependencies

- None (pure refactoring, no feature changes)
