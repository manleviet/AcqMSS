---
title: "ConGenModelBuilder Auto-Prepare Enhancement"
description: "Add with_oracle() and auto-prepare in build() when oracle+examples present"
status: completed
priority: P2
effort: 1h
branch: main
tags: [refactoring, builder-pattern, congen]
created: 2026-02-18
---

# ConGenModelBuilder Auto-Prepare Enhancement

## Summary

Enhance `ConGenModelBuilder` to auto-prepare model inside `build()` when both oracle and examples are provided. Supports 3 API patterns: auto-prepare from file, auto-prepare from raw data, and CV build-once-prepare-per-fold.

## Brainstorm Report

- [brainstorm-260218-0929-congenmodelbuilder-auto-prepare.md](../reports/brainstorm-260218-0929-congenmodelbuilder-auto-prepare.md)

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Modify ConGenModelBuilder](phase-01-modify-builder.md) | completed | 30m |
| 2 | [Add tests & verify](phase-02-tests-and-verify.md) | completed | 30m |

## Key Design Decisions

- **Same return type**: `build()` always returns `ConGenModel`, no type bifurcation
- **Lazy load**: `with_examples()` stores path, file read in `build()`
- **Negative optional**: `_has_examples()` checks positive only
- **Last-call-wins**: `with_examples()` and `with_examples_data()` overwrite each other
- **Re-prepare allowed**: `prepare()` remains idempotent for CV

## Files Changed

- `conacq/algorithms/acqmss/congen_model_builder.py` — Main changes
- `tests/test_congen.py` — New test cases for auto-prepare patterns

## Backward Compatibility

- Existing `build()` without oracle → returns unprepared model (unchanged)
- `ConGenRunner` uses CV pattern → no changes needed
- Existing tests → pass without modification
