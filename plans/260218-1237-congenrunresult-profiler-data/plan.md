---
title: "Add profiler_data to ConGenRunResult"
description: "Capture full profiler snapshot in ConGenRunResult and propagate to CV fold JSON output"
status: complete
priority: P3
effort: 1h
branch: main
tags: [profiler, metrics, congen, runner]
created: 2026-02-18
---

# Add profiler_data to ConGenRunResult

## Summary

ConGen's profiler collects rich metrics (solver_time, redundancy_checks, gauges) but only 3 are extracted into results. Add `profiler_data: Dict[str, Any]` to capture full profiler snapshot and propagate to JSON output.

## Context

- Brainstorm: [brainstorm-260218-1237-congenrunresult-profiler-data.md](../reports/brainstorm-260218-1237-congenrunresult-profiler-data.md)
- Approach chosen: **C** — Enhance runner only, keep ConGenResult unchanged

## Design Decisions

1. **ConGenResult unchanged** — stays algorithm-only
2. **ConGenRunResult gets `profiler_data: Dict[str, Any]`** — flat dict from `profiler.to_dict()`
3. **Propagate to CrossValidationFoldResult** — nested under `performance.profiler` in JSON
4. **Existing typed fields kept** — backward compatible, profiler_data is additive
5. **PerformanceMetrics/AggregatedPerformanceMetrics NOT modified** — profiler_data is pass-through

## Phases

| # | Phase | Status | Files |
|---|-------|--------|-------|
| 1 | [Add profiler_data field and propagation](phase-01-add-profiler-data.md) | complete | `congen_runner.py`, `cross_validation.py` |
