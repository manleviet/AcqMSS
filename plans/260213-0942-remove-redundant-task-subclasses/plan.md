---
title: "Remove Redundant Task Subclasses"
description: "Eliminate empty Incremental/NonIncremental task subclasses since both modes use identical assumption-based data"
status: complete
priority: P2
effort: 3h
branch: main
tags: [refactoring, task-hierarchy, clean-architecture]
created: 2026-02-13
---

# Remove Redundant Task Subclasses

## Problem

Six subclasses exist solely to differentiate incremental/non-incremental modes, but both modes now use identical assumption-based data. The only field they add (`assumptions: List`) is duplicated across each pair. One subclass (`NonIncrementalCONGENTask`) has dead fields (`clauses_to_name`, `name_to_clauses`) never read anywhere.

## Key Insight

Move `assumptions` field into `DiagnosisTask` (the root base). Since `TestCaseTask` and `CONGENTask` inherit from it, all descendants get `assumptions` automatically. Then the subclasses become truly empty and can be deleted. The `IncrementalTaskType` alias also becomes unnecessary.

## Scope

Remove 6 classes:
- `IncrementalDiagnosisTask`, `NonIncrementalDiagnosisTask` (explanation/models/task_preparation.py)
- `IncrementalTestCaseTask`, `NonIncrementalTestCaseTask` (explanation/models/task_preparation.py)
- `IncrementalCONGENTask`, `NonIncrementalCONGENTask` (acqmss/algorithms/task.py)

## Phase Plan

| # | Phase | Files | Status |
|---|-------|-------|--------|
| 1 | [Remove CONGEN task subclasses](phase-01-remove-congen-task-subclasses.md) | 3 files | complete |
| 2 | [Remove TestCase task subclasses](phase-02-remove-testcase-task-subclasses.md) | 2 files | complete |
| 3 | [Remove Diagnosis task subclasses](phase-03-remove-diagnosis-task-subclasses.md) | 2 files | complete |
| 4 | [Update tests](phase-04-update-tests.md) | 2 files | complete |
| 5 | [Cleanup exports and docs](phase-05-cleanup-exports-docs.md) | 5 files | complete |

## Recommended Execution Order

**Bottom-up (root-first)**: Phase 3 -> Phase 2 -> Phase 1 -> Phase 4 -> Phase 5

Rationale: Adding `assumptions` to `DiagnosisTask` (Phase 3) first means `TestCaseTask` and `CONGENTask` inherit it automatically, making Phases 2 and 1 pure deletion without any temporary workarounds.

## Dependencies

- Phase 3 should be done first (adds `assumptions` to root `DiagnosisTask`)
- Phase 2 depends on Phase 3 (`TestCaseTask` inherits `assumptions` from `DiagnosisTask`)
- Phase 1 depends on Phase 2 (`CONGENTask` inherits `assumptions` via `TestCaseTask`)
- Phase 4 depends on Phases 1-3
- Phase 5 depends on all prior phases

## Risks

- MRO (Method Resolution Order) complications if `CONGENTask` still inherits from `TestCaseTask` -- mitigated since we only remove leaves
- Dead field removal (`clauses_to_name`, `name_to_clauses`) -- confirmed unused outside `task_preparation.py`
