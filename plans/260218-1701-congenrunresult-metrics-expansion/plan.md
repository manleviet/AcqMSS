---
status: pending
created: 2026-02-18
branch: main
---

# Plan: ConGenRunResult Metrics Expansion

## Overview

Add 8 profiler metrics as first-class fields across the full pipeline.

## Phases

| # | Phase | Status |
|---|---|---|
| 1 | Update PerformanceMetrics + AggregatedPerformanceMetrics + aggregate_metrics() | pending |
| 2 | Update ConGenRunResult + ConGenRunner.run() | pending |
| 3 | Update InteractiveRunResult defaults | pending |
| 4 | Update tests | pending |
| 5 | Run tests + verify | pending |

## Key Files

- `conacq/eval/performance_metrics.py`
- `conacq/runners/congen_runner.py`
- `conacq/runners/interactive_runner.py`
- `tests/test_evaluation.py`

## Context

- Brainstorm: `plans/reports/brainstorm-260218-1701-congenrunresult-metrics-expansion.md`
