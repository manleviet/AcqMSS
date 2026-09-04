---
title: "Refactor ConGen: Remove DescriptionProvider from acquire()"
description: "Extract name resolution from ConGen algorithm to callers via utility function"
status: complete
priority: P2
effort: 1h
branch: main
tags: [refactoring, srp, congen_root, decoupling]
created: 2026-02-15
---

# Refactor ConGen: Remove DescriptionProvider from acquire()

## Summary

ConGen.acquire() currently mixes algorithm logic with presentation (name resolution via DescriptionProvider). This violates SRP and creates unnecessary coupling from `acqmss.algorithms` -> `explanation.models`. Refactor to return raw IDs only; callers resolve names externally via a simple utility function (Option A).

## Phases

| # | Phase | Status | Effort | File |
|---|-------|--------|--------|------|
| 1 | Simplify CONGENResult & acquire() | complete | 20min | [phase-01](phase-01-simplify-congen-and-result.md) |
| 2 | Update callers | complete | 25min | [phase-02](phase-02-update-callers.md) |
| 3 | Test & verify | complete | 15min | [phase-03](phase-03-test-and-verify.md) |

## Key Files

- `acqmss/algorithms/congen.py` — CONGENResult + ConGen.acquire() + save_result()
- `apps/run_congen.py` — CLI caller (line 131)
- `acqmss/eval/congen_runner.py` — CV runner (line 178, also uses kb_constraints as lookup keys)
- `tests/test_congen.py` — 3 test methods

## Architecture Decision

**Before:** ConGen.acquire(description_provider) -> CONGENResult(kb_constraints=["name1",...])
**After:** ConGen.acquire() -> CONGENResult(kb_assumption_ids=[1,2,...], redundant_ids=[3,...])
         + `resolve_congen_names(result, provider)` utility at caller boundary

## Risk

- `congen_runner.py:200` uses `result.kb_constraints` as keys into `constraint_map` — fragile pattern, needs careful migration to ID-based lookup
- `save_result()` currently outputs names — needs provider param or separate serialization helper

## Dependencies

None — self-contained refactoring.
