---
title: "InteractiveRunner dual-mode support"
description: "Refactor InteractiveRunner to support both oracle-based and example-based modes, symmetric with ConGenRunner"
status: complete
priority: P2
effort: 2h
branch: main
tags: [refactoring, runner, interactive, symmetry]
created: 2026-02-26
completed: 2026-02-26
---

# InteractiveRunner Dual-Mode Support

## Problem

`InteractiveRunner` only supports example-pool mode (CV). `run_interactive.py` bypasses it, using `InteractiveLearner` directly with duplicate profiler/memory/save logic. `ConGenRunner` serves both standalone + CV — `InteractiveRunner` should too.

## Brainstorm Report

- [brainstorm-260226-1517-interactive-runner-dual-mode.md](../reports/brainstorm-260226-1517-interactive-runner-dual-mode.md)

## Phases

| Phase | Description | Status | File |
|-------|-------------|--------|------|
| 01 | Refactor InteractiveRunner + InteractiveRunResult | complete | [phase-01](phase-01-refactor-runner.md) |
| 02 | Update run_interactive.py to use InteractiveRunner | complete | [phase-02](phase-02-update-run-interactive.md) |
| 03 | Update cross_validation.py caller | complete | [phase-03](phase-03-update-cross-validation.md) |
| 04 | Test + verify both modes | complete | [phase-04](phase-04-test-verify.md) |

## Key Decisions

1. **Constructor**: file-path-based `(bias_path, fm_path)` — loads bias + creates oracle internally
2. **API**: single `run()` with `mode` param — `'automated'`/`'interactive'` or `'example_only'`/`'example_first'`
3. **Breaking change**: clean break, update all callers
4. **Oracle ownership**: learner creates its own oracle in oracle mode (KISS)
5. **New fields**: `bg_clauses`, `profiler_data` added to `InteractiveRunResult`
6. **Expose `variables`**: runner exposes `feature_ids` property for `_run_cv_loop` → `AccuracyCalculator`

## Dependencies

- `conacq.algorithms.interactive.InteractiveLearner` — facade (lazy import preserved)
- `conacq.oracle.FeatureModelOracle` — oracle for example mode validation
- `conacq.bias.BiasIO` — load bias from JSON
- `explanation.operations.algorithms.profiler` — `profiler_session`, `ProfilerPreset`
