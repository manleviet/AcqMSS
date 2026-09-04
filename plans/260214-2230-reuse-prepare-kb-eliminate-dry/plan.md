---
title: "Reuse prepare_kb to eliminate DRY violation"
description: "Replace _prepare_bias_constraints with prepare_kb + post-processing for bidirectional maps"
status: completed
priority: P3
effort: 1h
branch: main
tags: [refactor, dry, task-preparation]
created: 2026-02-14
---

# Reuse prepare_kb — Eliminate DRY Violation

## Problem

`_prepare_bias_constraints` (acqmss) and `prepare_kb` (explanation) share ~80% identical logic for assumption-guarded clause creation. DRY violation.

## Approach: Option B

Reuse `prepare_kb` from explanation module. Build bidirectional maps (`assumption_to_constraint`, `constraint_to_assumption`) in post-processing using sequential ID pattern.

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Replace `_prepare_bias_constraints` with `prepare_kb` + post-processing | completed | [phase-01](phase-01-replace-with-prepare-kb.md) |
| 2 | Verify & test | completed | [phase-02](phase-02-verify-and-test.md) |

## Key Files

- `acqmss/algorithms/task_preparation.py` — remove `_prepare_bias_constraints`, update `ConGenTaskPreparation.prepare()`
- `explanation/models/task_preparation.py` — source of `prepare_kb` (no changes)

## Dependencies

- `ConGenTask` inherits `TestCaseTask` → `DiagnosisTask` — has all fields `prepare_kb` needs
- `prepare_kb` already imported indirectly via explanation.models.task_preparation

## Risks

- If `prepare_kb` ID assignment order changes, post-processing loop breaks silently → mitigate with assertion in test
