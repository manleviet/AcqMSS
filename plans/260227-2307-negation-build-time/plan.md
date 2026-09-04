---
title: "Move Negation to Build Time"
description: "Make ConGenModel/QuAcqModel prepare() idempotent by computing negation at build time"
status: complete
priority: P2
effort: 2h
branch: main
tags: [refactor, idempotent, model-lifecycle]
created: 2026-02-27
completed: 2026-02-27
---

# Move Negation to Build Time

## Problem
`ConGenTaskPreparation.prepare()` and `QuAcqTaskPreparation.prepare()` compute `negated_constraint_map` inside `prepare()`, writing to model state each run. DiagnosisModel/FMOracleModel compute negation at build time — `prepare()` is read-only and idempotent.

## Decision
Option B (KISS): Move negation to build time. Keep oracle param in `prepare()`.
See: [brainstorm report](../reports/brainstorm-260227-2316-negation-build-time-refactor.md)

## Phases

| # | Phase | Status | Effort | Files |
|---|-------|--------|--------|-------|
| 1 | [ConGen negation to build time](phase-01-congen-negation-build-time.md) | complete | 45min | 3 files |
| 2 | [QuAcq negation to build time](phase-02-quacq-negation-build-time.md) | complete | 30min | 2 files |
| 3 | [Tests & verify](phase-03-tests-verify.md) | complete | 30min | 0 files |

## Success Criteria
- All existing tests pass
- `prepare()` no longer writes to `negated_constraint_map`
- ConGen CV multi-run works identically
- Pattern consistent with DiagnosisModel
