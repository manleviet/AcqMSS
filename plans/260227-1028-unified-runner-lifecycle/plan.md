---
title: "Unified Runner Lifecycle Refactoring"
description: "Unify ConGenRunner/InteractiveRunner lifecycle, extract BaseRunner/BaseRunResult, single CV function"
status: complete
priority: P1
effort: 3h
branch: main
tags: [refactoring, runners, evaluation, DRY]
created: 2026-02-27
completed: 2026-02-27
---

# Unified Runner Lifecycle Refactoring

## Goal

Unify ConGenRunner and InteractiveRunner to follow identical resource lifecycle (build once, run many, cleanup once). Extract shared base classes. Enable single polymorphic CV evaluation pipeline.

## Context

- Brainstorm: `plans/reports/brainstorm-260227-1028-unified-runner-lifecycle.md`
- Reusability analysis: `plans/reports/Explore-260227-1124-interactive-reusability.md`
- Both runners share ~70% structural overlap; `_run_cv_loop` already duck-types with `getattr` hacks

## Key Design Decisions

1. **BaseRunner ABC** — shared `__init__`, `run()`, `cleanup()`, `feature_ids` property
2. **BaseRunResult dataclass** — 9 shared fields + `to_dict()` + `get_performance_metrics()`
3. **InteractiveRunner** — move oracle/model to `__init__()` (safe per reusability analysis)
4. **PerformanceMetrics.n_mss** — becomes `Optional[int] = None`
5. **run() signature** — optional examples for both; each subclass validates own requirements
6. **Single CV function** — `_run_cv_loop` already exists; formalize with BaseRunner type

## Phases

| Phase | File | Status | Progress | Description |
|-------|------|--------|----------|-------------|
| 01 | [phase-01-base-run-result.md](phase-01-base-run-result.md) | Complete | 100% | Extract BaseRunResult dataclass |
| 02 | [phase-02-performance-metrics.md](phase-02-performance-metrics.md) | Complete | 100% | Make n_mss optional in PerformanceMetrics |
| 03 | [phase-03-base-runner.md](phase-03-base-runner.md) | Complete | 100% | Extract BaseRunner ABC |
| 04 | [phase-04-interactive-lifecycle.md](phase-04-interactive-lifecycle.md) | Complete | 100% | Align InteractiveRunner to build-once |
| 05 | [phase-05-unified-cv.md](phase-05-unified-cv.md) | Complete | 100% | Clean up CV loop, remove getattr hacks |
| 06 | [phase-06-test-and-verify.md](phase-06-test-and-verify.md) | Complete | 100% | Run all tests, verify pipeline |

## Success Criteria

- Both runners follow identical lifecycle (build once, run many, cleanup once)
- Single `_run_cv_loop` works with BaseRunner type (no getattr hacks)
- `PerformanceMetrics.n_mss` is `Optional[int] = None`
- All existing tests pass (`PYTHONPATH=. pytest tests/ -v`)
- `extract_results.py` works with both result types
