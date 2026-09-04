---
title: "Oracle use_incremental pass-through"
description: "Pass use_incremental from config through BaseRunner to Oracle for fair algorithm benchmarking"
status: complete
priority: P1
effort: 1h
branch: main
tags: [oracle, benchmarking, fairness, refactoring]
created: 2026-02-27
---

# Oracle use_incremental Pass-Through

## Problem
`BaseRunner.__init__()` hardcodes `use_incremental=False` for Oracle. For fair comparison between ConGen and Interactive algorithms, Oracle must use the configured value.

## Context
- Brainstorm: [brainstorm report](../reports/brainstorm-260227-1111-oracle-use-incremental.md)
- No technical constraint forcing `use_incremental=False` — Oracle's KB is fixed after build, only assumptions change
- `run_cv.py` iterates `solver_modes` but never passes `is_incremental` to Interactive CV path

## Phases

| # | Phase | Status | Files |
|---|-------|--------|-------|
| 1 | [Runner + Oracle plumbing](phase-01-runner-oracle-plumbing.md) | complete | base_runner.py, congen_runner.py, interactive_runner.py |
| 2 | [InteractiveModel use_incremental](phase-02-interactive-model.md) | complete | interactive_model.py |
| 3 | [CV + Config integration](phase-03-cv-config-integration.md) | complete | cross_validation.py, run_cv.py, run_interactive_config.toml |
| 4 | [Tests](phase-04-tests.md) | complete | tests/test_interactive.py |

## Dependencies
- Phase 2 depends on Phase 1 (InteractiveRunner passes use_incremental to model)
- Phase 3 depends on Phase 1 (CV functions accept use_incremental)
- Phase 4 depends on all
