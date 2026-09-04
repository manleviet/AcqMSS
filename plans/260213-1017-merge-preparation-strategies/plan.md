---
title: "Merge Redundant Preparation Strategy Classes"
description: "Merge 6 duplicated Incremental/NonIncremental strategy pairs into 3 classes, extract shared base"
status: complete
priority: P1
effort: 2h
branch: main
tags: [refactoring, DRY, task-preparation]
created: 2026-02-13
---

# Merge Redundant Preparation Strategy Classes

## Problem

After removing redundant task dataclass subclasses, 6 preparation strategy classes remain as copy-paste pairs:
- `IncrementalDiagnosisTaskPreparation` = `NonIncrementalDiagnosisTaskPreparation` (~185 lines each)
- `IncrementalTestCaseTaskPreparation` = `NonIncrementalTestCaseTaskPreparation` (~140 lines each)
- `IncrementalCONGENTaskPreparation` = `NonIncrementalCONGENTaskPreparation` (~190 lines each)

Each pair differs only in `mode_name` property. ~400+ lines of pure duplication.

`IncrementalKBPreparator` has static methods duplicated in `NonIncrementalDiagnosisTaskPreparation`.

## Solution

Merge each pair → 3 classes. Then extract shared KB/config preparation into base class.

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Merge explanation strategies + integrate KBPreparator](phase-01-merge-explanation-strategies.md) | complete | 45m |
| 2 | [Merge CONGEN strategies](phase-02-merge-congen-strategies.md) | complete | 30m |
| 3 | [Update references, tests, docs](phase-03-update-references.md) | complete | 45m |

## Execution Order

Phase 1 → 2 → 3 (sequential — Phase 2 depends on Phase 1's base class, Phase 3 depends on both)

## Key Design Decision

After merge, `DiagnosisTaskPreparation` and `TestCaseTaskPreparation` both use `IncrementalKBPreparator.prepare_kb()`. Instead of keeping `IncrementalKBPreparator` as separate utility:
- Move `prepare_kb()` and `prepare_configuration()` into a shared base class
- Both `DiagnosisTaskPreparation` and `TestCaseTaskPreparation` inherit from it
- Rename to `KBPreparator` (drop "Incremental" prefix — it serves both modes)

## Files Changed

- `explanation/models/task_preparation.py` — main changes (895→~500 lines)
- `acqmss/algorithms/task_preparation.py` — merge CONGEN pair (357→~200 lines)
- `acqmss/algorithms/__init__.py` — update exports
- `acqmss/eval/congen_runner.py` — update references
- `apps/run_congen.py` — update references
- `tests/test_congen.py` — update references
- `tests/test_diagnosis.py` — update references (if any)
