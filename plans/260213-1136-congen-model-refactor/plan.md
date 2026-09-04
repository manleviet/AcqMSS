---
title: "Refactor ConGenModel to self-preparing pattern with BG support"
description: "Convert ConGenModel from dataclass to class with prepare() method (like DiagnosisModel) and replace root_feature_id with general background_knowledge field."
status: complete
priority: P2
effort: 3h
branch: main
tags: [refactor, congen_root-model, background-knowledge]
created: 2026-02-13
---

# Refactor CONGENModel

## Goal

Align CONGENModel with DiagnosisModel's "prepare once, use many" pattern. Add proper BG (background knowledge) support replacing the narrow `root_feature_id` field.

## Current State

- `CONGENModel` is a `@dataclass` with no `prepare()` method
- Callers manually create `CONGENTaskPreparation`, call `prepare(model)`, extract task
- BG is limited to `root_feature_id: Optional[int]` (single literal)
- 3 callers duplicate the prepare-then-GenerateNE flow: `run_congen.py`, `congen_runner.py`, `test_congen.py`

## Target State

- `CONGENModel` is a regular class with `prepare()` -> stores `_task` and `_description_provider`
- `task` / `description_provider` properties with RuntimeError guard (same as DiagnosisModel)
- `background_knowledge: List[int]` replaces `root_feature_id`
- Callers call `model.prepare(mode)` instead of external preparation
- GenerateNE stays outside prepare() (needs checker, a runtime dep)

## Phases

| # | Phase | Status | Effort | File |
|---|-------|--------|--------|------|
| 1 | Refactor CONGENModel class | complete | 1.5h | [phase-01](phase-01-refactor-congen-model.md) |
| 2 | Add BG support | complete | 0.5h | [phase-02](phase-02-add-bg-support.md) |
| 3 | Update callers & tests | complete | 1h | [phase-03](phase-03-update-callers.md) |

## Key Dependencies

- `CONGENTaskPreparation` stays as-is (strategy pattern), just called from inside model
- `PreparationOutput`, `DescriptionProvider` from `explanation.models.task_preparation` reused
- `CONGENTask` dataclass unchanged
- GenerateNE + merge_ne_into_task remain caller responsibility

## Risk

- Low: Pure refactor with clear reference pattern (DiagnosisModel)
- Breaking: All 3 callers must update simultaneously

## Files Modified

1. `acqmss/algorithms/model.py` -- Main refactor
2. `acqmss/algorithms/task_preparation.py` -- Use `background_knowledge`
3. `apps/run_congen.py` -- Use `model.prepare()`
4. `acqmss/eval/congen_runner.py` -- Use `model.prepare()`
5. `tests/test_congen.py` -- Use new API
6. `acqmss/algorithms/__init__.py` -- Update exports if needed
