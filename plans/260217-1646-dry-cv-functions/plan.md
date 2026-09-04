---
title: "DRY cross-validation CV loop"
description: "Extract shared CV loop from 2 nearly identical functions into _run_cv_loop()"
status: completed
priority: P2
effort: 1.5h
branch: refactor/dry-cv-functions
tags: [refactor, dry, cross-validation]
created: 2026-02-17
---

# DRY Cross-Validation CV Loop

## Problem

`acqmss/eval/cross_validation.py` (470 lines) has two functions sharing ~85% code:
- `n_fold_cross_validation()` — ConGenRunner (batch)
- `n_fold_cross_validation_interactive()` — InteractiveRunner (QuAcq)

Both share: fold gen, shuffle, apply_folds, runner.run(), accuracy calc, KB intersection, mean/std, aggregation.

Differ only in: runner creation, variables source for accuracy, fold result defaults (`n_mss`, `redundant_constraints`), log labels.

## Design Decision

**Callback approach** (KISS over Protocol):
- Extract `_run_cv_loop()` taking a runner object + `get_variables` callback
- Both runners already share `run(pos, neg, shuffle_seed)` interface
- Runner result duck-typing: both have `.kb_constraints`, `.kb_clauses`, `.get_performance_metrics()`, `.n_bias`, `.n_kb`
- Use `getattr(result, 'n_mss', 0)` and `getattr(result, 'redundant_constraints', [])` for optional fields
- No new Protocol/ABC needed

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Extract `_run_cv_loop()` + simplify wrappers | completed | [phase-01](phase-01-extract-cv-loop.md) |
| 2 | Update `__init__.py` exports + verify callers | completed | [phase-02](phase-02-verify-callers.md) |
| 3 | Test + lint | completed | [phase-03](phase-03-test-lint.md) |

## Target

File drops from 470 → ~250 lines. Public API unchanged. No new dependencies.

## Callers (2 total)

- `apps/run_congen_eval.py:234` — calls `n_fold_cross_validation()`
- `apps/run_interactive_eval.py:228` — calls `n_fold_cross_validation_interactive()`
- `acqmss/eval/__init__.py` — re-exports both
- No direct tests for CV functions (tested via integration)

## Key Risks

- Duck typing on runner results — if a field is missing, `getattr` silently defaults. Mitigated by existing test coverage on callers.
- Lazy import of `InteractiveRunner` in interactive CV — must remain in wrapper, not in shared loop.
