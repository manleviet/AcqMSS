---
title: "Add task_input parameter to prepare() for model reuse"
description: "Enable DiagnosisModel and ConGenModel reuse by accepting optional task_input in prepare()"
status: completed
priority: P3
effort: 30m
branch: main
tags: [refactor, api, diagnosis, congen_root]
created: 2026-02-14
---

# Add task_input Parameter to prepare() for Model Reuse

## Problem

`DiagnosisModel` holds expensive FM transformation data (`constraint_map`, `variables`, `negated_constraint_map`, `next_tseitin_var`) that is immutable after creation. However, `prepare()` reads from private `_task_input` with no public way to change it after `build()`. This forces users to rebuild the entire model (including FM transformation) when only the configuration changes.

`ConGenModel` already has public `task_input` but adding the parameter for API consistency.

`OracleModel` — no change needed (already has `config_to_active_assumptions` pattern).

## Solution

Add optional `task_input` parameter to `prepare()` on both models. Default `None` preserves all existing behavior.

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Add prepare() reuse support](phase-01-add-prepare-reuse.md) | Completed | 20m |

## Key Design Decisions

- **Backward compatible**: Default `None` means all existing callers unchanged
- **DiagnosisModelBuilder.build()** calls `prepare()` without args — no change needed
- **Checker staleness**: After re-`prepare()`, old checker holds stale KB refs. Document in docstrings.
- **No change to OracleModel**: Already optimal via `config_to_active_assumptions()`

## Files to Modify

1. `explanation/models/pysat_diagnosis_model.py` — `DiagnosisModel.prepare()`
2. `acqmss/algorithms/congen_model.py` — `ConGenModel.prepare()`
