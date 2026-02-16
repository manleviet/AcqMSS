---
title: "Bias Package Internal Refactoring"
description: "Extract helper methods, constants, and add caching to 3 oversized bias files"
status: complete
priority: P2
effort: 2h
branch: main
tags: [refactoring, bias, code-quality]
created: 2026-02-16
---

# Bias Package Internal Refactoring

## Objective

Improve code health of `acqmss/bias/` package by extracting helper methods from 3 oversized files, extracting magic numbers as constants, and caching constraints for statistics reuse. No new files, no public API changes.

## Context

- Brainstorm: `plans/reports/brainstorm-260216-1425-bias-package-improvements.md`
- Package: 6 files, 1,157 LOC total. 3/6 exceed 200 LOC threshold.
- Tests: `tests/test_bias_module.py`, `tests/test_bias_module_1.py` (script-based), plus integration via `tests/test_congen.py`

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Refactor bias_generator.py](phase-01-refactor-bias-generator.md) | complete | 50m |
| 2 | [Refactor config_loader.py](phase-02-refactor-config-loader.md) | complete | 30m |
| 3 | [Refactor bias_io.py](phase-03-refactor-bias-io.md) | complete | 30m |
| 4 | [Run tests and verify](phase-04-test-and-verify.md) | complete | 10m |

## Constraints

- NO new files (internal extraction only)
- NO public API changes (all new methods are private `_`-prefixed)
- NO logging migration (keep `print()` statements)
- ALL existing tests must pass
- Preserve feature ID ordering (flamapy tree traversal)

## Success Criteria

- [ ] All 3 files closer to 200 LOC (or below)
- [ ] No method >50 LOC
- [ ] Magic numbers extracted as named constants
- [ ] `get_statistics()` uses cached constraints
- [ ] All tests pass: `PYTHONPATH=. pytest tests/ -v`
