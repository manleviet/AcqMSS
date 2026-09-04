---
title: "Refactor ConGen workflow to match DiagnosisModel pattern"
description: "Create ConGenModelBuilder, move GenerateNE into prepare(), update acquire() signature, implement CheckerModel protocol"
status: completed
priority: P1
effort: 4h
branch: main
tags: [refactoring, congen_root, architecture, builder-pattern]
created: 2026-02-14
---

# Refactor ConGen Workflow

## Goal

Align ConGen workflow with DiagnosisModel pattern: builder creates model, `prepare()` handles all setup incl. GenerateNE, `acquire()` takes direct params instead of task object.

## Current Flow

```
ConGenModel.from_bias_and_examples() -> model.prepare() -> task
-> GenerateNE(temp_checker).generate() -> merge_ne_into_task(task)
-> Checker(task.set_kb, task.assumptions) -> ConGen(checker).acquire(task)
```

## Target Flow

```
ConGenModelBuilder.from_files().with_examples().use_incremental().build()
  -> build() calls prepare() internally (incl. GenerateNE)
-> CheckerFactory.create_from_model(model) -> ConGen(checker)
-> congen.acquire(set_b, set_bg, set_tc, set_ne)
```

## Phases

| # | Phase | Status | Est |
|---|-------|--------|-----|
| 1 | [Modify ConGenModel](phase-01-modify-congen-model.md) | completed | 1.5h |
| 2 | [Create ConGenModelBuilder](phase-02-create-congen-model-builder.md) | completed | 1h |
| 3 | [Update ConGen.acquire() signature](phase-03-update-acquire-signature.md) | completed | 30m |
| 4 | [Update callers](phase-04-update-callers.md) | completed | 45m |
| 5 | [Run tests and verify](phase-05-tests-verify.md) | completed | 15m |

## Key Constraints

- ConGenModel must implement CheckerModel protocol (structural subtyping)
- GenerateNE moves inside `prepare()`, no longer caller's responsibility
- ConGenTask keeps inheritance from TestCaseTask (DiagnosisTask)
- Both temp checker (GenerateNE) and final checker use CheckerFactory
- Backward compat: `from_bias_and_examples()` stays as alternative to builder

## Dependencies

- CheckerModel protocol already exists in `checker.py`
- CheckerFactory already exists in `checker.py`
- No new external dependencies
