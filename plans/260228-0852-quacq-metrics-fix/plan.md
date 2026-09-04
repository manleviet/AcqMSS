---
title: "Fix QuAcq Performance Metrics Pipeline Crash"
description: "Add QuAcq-specific fields to PerformanceMetrics/AggregatedPerformanceMetrics so QuAcqRunResult.get_performance_metrics() stops crashing and CV aggregation preserves all metrics."
status: complete
priority: P1
effort: 2h
branch: main
tags: [bugfix, quacq, metrics, cross-validation]
created: 2026-02-28
completed: 2026-02-28
---

# Fix QuAcq Performance Metrics Pipeline Crash

## Problem

`QuAcqRunResult.get_performance_metrics()` passes 16 QuAcq-specific kwargs that `PerformanceMetrics` doesn't accept -> TypeError crash at runtime. Even if fixed, `AggregatedPerformanceMetrics` and `aggregate_metrics()` silently drop QuAcq fields during CV aggregation.

## Root Cause

PerformanceMetrics was designed for ConGen only. QuAcq metrics added to runner result but never to the dataclass pipeline.

## Phases

| # | Phase | Status | Files Modified |
|---|-------|--------|---------------|
| 1 | [Extend PerformanceMetrics](phase-01-extend-performance-metrics.md) | complete | `conacq/eval/performance_metrics.py` |
| 2 | [Extend AggregatedPerformanceMetrics + aggregate_metrics()](phase-02-extend-aggregated-metrics.md) | complete | `conacq/eval/performance_metrics.py` |
| 3 | [Fix CV fold serialization](phase-03-fix-cv-fold-serialization.md) | complete | `conacq/eval/cross_validation.py` |
| 4 | [Test and verify](phase-04-test-and-verify.md) | complete | `tests/test_evaluation.py` |

## Key Constraints

- All new fields default to 0/0.0 -- ConGen path unaffected
- No restructuring; just extend existing dataclasses
- Follow existing pattern: float for runtimes (ms), int for call counts
- `_stat4()` helper already exists for mean/std/min/max computation

## Affected Files

1. `conacq/eval/performance_metrics.py` -- PerformanceMetrics, AggregatedPerformanceMetrics, aggregate_metrics()
2. `conacq/runners/quacq_runner.py` -- QuAcqRunResult.get_performance_metrics() (already correct, just needs the dataclass to accept its kwargs)
3. `conacq/eval/cross_validation.py` -- CrossValidationFoldResult.to_dict()
4. `tests/test_evaluation.py` -- Add QuAcq metrics tests
