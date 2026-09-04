---
title: "Extract Oracle from ConGenModel"
description: "Refactor ConGenModel to be pure data container; oracle injected at prepare() time"
status: complete
priority: P2
effort: 3h
branch: main
tags: [refactor, architecture, congen, oracle]
created: 2026-02-16
---

# Extract Oracle from ConGenModel

## Goal

Make `ConGenModel` a pure data container (bias constraints, variables, solver config). Oracle created externally, injected at `prepare()` time. FM-derived metadata (`num_fm_constraints`, `root_feature`) obtained from oracle during preparation -- never stored on model.

## Phases

| # | Phase | Status | Effort | Key Files |
|---|-------|--------|--------|-----------|
| 1 | Update Oracle API | complete | 30m | `fm_oracle.py`, `fm_oracle_model.py` |
| 2 | Refactor ConGenModel | complete | 45m | `congen_model.py`, `task_preparation.py` |
| 3 | Simplify Builder | complete | 30m | `congen_model_builder.py` |
| 4 | Update Runner & Tests | complete | 45m | `congen_runner.py`, `run_congen.py`, `test_congen.py` |
| 5 | Cleanup Dead Code | complete | 30m | `data_structures.py`, docs |

## Key Decisions

1. `prepare(oracle=oracle)` -- oracle passed as param, not stored on model
2. `next_tseitin_var` stays on model (needed by task prep), but initialized from oracle at prepare() time
3. `num_fm_constraints` and `root_feature` become local variables in `ConGenTaskPreparation.prepare()`, extracted from oracle
4. Builder factory methods simplified: `from_bias(path)` replaces `from_bias_and_fm_*()` pair
5. `ConGenRunner` creates oracle (already has FM path in config), passes to `model.prepare()`

## Dependencies

- No external dependency changes
- All changes internal to `acqmss/` package

## Risk

- **Medium**: `_prepare_bg()` uses `root_feature` and `variables` -- must get from oracle at prepare time
- **Low**: ID reservation formula uses `num_fm_constraints` -- must get from oracle's constraint_map length
