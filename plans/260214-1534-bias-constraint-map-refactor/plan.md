---
title: "Move bias-to-constraint-dict conversion into Bias class"
description: "Centralize repeated {c.id: c.clauses} conversion pattern into Bias methods, eliminating DRY violations across 4 call sites"
status: completed
priority: P3
effort: 1h
branch: main
tags: [refactor, bias, DRY]
created: 2026-02-14
---

# Move Bias-to-Constraint-Dict Conversion into Bias Class

## Summary

The pattern `{c.id: c.clauses for c in bias.constraints}` (and its variant with Tseitin negation) is repeated inline in 4 locations. This refactoring centralizes the conversion as methods on the `Bias` class.

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Add methods to Bias class](./phase-01-add-bias-methods.md) | completed | 20min |
| 2 | [Update callers](./phase-02-update-callers.md) | completed | 20min |
| 3 | [Test & verify](./phase-03-test-verify.md) | completed | 20min |

## Key Design Decision

Two conversion patterns exist:
- **Simple**: `{c.id: c.clauses}` — used in `ConGenModelBuilder`
- **With negation**: builds both `constraint_map` + `negated_constraint_map` via `negate_cnf_tseitin()` — used in `InteractiveLearner` (2 places)

**Proposed methods/properties on `Bias`:**
1. `to_constraint_map()` — simple dict mapping `{c.id: c.clauses}`
2. `feature_ids` property — `Dict[str, int]` mapping `{f.name: f.id}`
3. `id_to_feature` property — `Dict[int, str]` reverse mapping `{f.id: f.name}`
4. `max_variable_id` property — max `abs(literal)` across all clauses + feature IDs
5. `to_constraint_maps_with_negation(tseitin_start)` — returns `(constraint_map, negated_map, next_tseitin_var)`

Note: Method 5 introduces `negate_cnf_tseitin` dependency from `explanation.operations.algorithms.utils` into the bias module. No circular dependency risk (explanation doesn't import from bias).

**Important**: `feature_ids` from `bias.features` and `oracle.get_feature_ids()` must match (same SAT variable IDs). Callers that intentionally use oracle as source of truth (e.g., `_build_task_from_bias`) should keep using oracle.

## Files Modified

| File | Change |
|------|--------|
| `acqmss/bias/data_structures.py` | Add 5 methods/properties to Bias class |
| `acqmss/algorithms/congen_model_builder.py` | Replace inline conversion (line 118) |
| `acqmss/algorithms/interactive/learner.py` | Replace inline conversions (lines 134-135, 138-150, 176-185) |
| `tests/test_interactive.py` | Replace inline conversion (lines 55-64) |
| `tests/test_congen.py` | Replace `{f.name: f.id for f in bias.features}` (line 308) |

## Dependencies

- `explanation.operations.algorithms.utils.negate_cnf_tseitin` (existing function)

## Risk

Low — pure refactoring, no behavior change. All existing tests should pass unchanged.
