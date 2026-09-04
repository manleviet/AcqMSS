---
title: "DiscriminatingGenerator ConsistencyChecker DI Refactor"
description: "Refactor DiscriminatingGenerator to use ConsistencyChecker via DI pattern like FindScope/FindC"
status: complete
priority: P2
effort: 1h
branch: main
tags: [refactoring, di-pattern, quacq, consistency-checker]
created: 2026-02-28
---

# DiscriminatingGenerator → ConsistencyChecker DI Refactor

## Context
- [Brainstorm Report](../reports/brainstorm-260228-0709-discriminating-generator-checker-refactor.md)
- [QuAcq Documentation](../../docs/quacq.md)

## Problem
`DiscriminatingGenerator` uses raw PySAT `Solver` directly while `FindScope`/`FindC` use injected `ConsistencyChecker`. Inconsistent DI pattern, duplicates solver management.

## Solution
Full DI pattern: `__init__(checker, model, root_assumption)`. `generate()` builds assumption list, calls `checker.is_consistent()` + `get_model()` + `model.model_to_config()`. Shares same solver instance.

## Implementation Phases

| # | Phase | Status | Files |
|---|-------|--------|-------|
| 1 | [Add get_constraint_vars to QuAcqModel](phase-01-model-method.md) | complete | quacq_model.py |
| 2 | [Rewrite DiscriminatingGenerator](phase-02-rewrite-generator.md) | complete | discriminating_generator.py |
| 3 | [Update construction sites](phase-03-update-callers.md) | complete | quacq_runner.py, __init__.py, test_quacq.py |

## Key Constraints
- `generate()` signature unchanged for callers: `(c_i, c_j, learned_kb, scope)`
- `FindC._narrow_with_generator()` needs NO changes
- Return type unchanged: `Optional[Dict[str, bool]]`

## Success Criteria
- All existing tests pass
- No raw PySAT import in discriminating_generator.py
- DI pattern consistent with FindScope/FindC
