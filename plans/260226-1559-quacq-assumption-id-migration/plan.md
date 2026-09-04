---
title: "QuAcq Assumption ID Migration"
description: "Migrate QuAcq from string constraint IDs to assumption IDs for ConGen symmetry"
status: completed
priority: P1
effort: 8h
branch: main
tags: [refactoring, quacq, congen, symmetry]
created: 2026-02-26
---

# QuAcq Assumption ID Migration

## Problem
ConGen uses `int` assumption IDs throughout; QuAcq uses `str` constraint IDs.
QuAcq._reduce_kb() builds temporary assumption IDs, calls REDUCE, maps back to strings.
Goal: migrate QuAcq to assumption IDs for symmetry, enabling direct REDUCE reuse.

## Approach
Parallel structure (Option B from brainstorm): new QuAcqTask, InteractiveModel,
InteractiveTaskPreparation. Keep old InteractiveTask/InteractiveLearner as deprecated.

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Create QuAcqTask, InteractiveModel, InteractiveTaskPreparation](phase-01-create-quacq-task-and-model.md) | completed | 2h |
| 2 | [Update QuAcq algorithm](phase-02-update-quacq-algorithm.md) | completed | 1.5h |
| 3 | [Update FindScope + FindC](phase-03-update-findscope-findc.md) | completed | 1h |
| 4 | [Update InteractiveResult + InteractiveRunner](phase-04-update-result-and-runner.md) | completed | 1h |
| 5 | [Update eval pipeline](phase-05-update-eval-pipeline.md) | completed | 0.5h |
| 6 | [Update tests](phase-06-update-tests.md) | completed | 1.5h |
| 7 | [Deprecate old classes](phase-07-deprecate-old-classes.md) | completed | 0.5h |

## Dependencies
- Phase 2,3 depend on Phase 1
- Phase 4 depends on Phase 2,3
- Phase 5 depends on Phase 4
- Phase 6 depends on Phase 1-5
- Phase 7 depends on Phase 6 (all tests pass)

## Key Reusable Infrastructure
- `prepare_kb()` from `explanation/models/task_preparation.py`
- `negate_cnf_tseitin()` from `explanation/operations/algorithms/utils.py`
- `Reduce.reduce()` from `conacq/algorithms/acqmss/reduce.py`
- `DescriptionProvider` from `explanation/models/task_preparation.py`
- `BGData` from `conacq/oracle/bg_data.py`
- `NonIncrementalPySATChecker` from `explanation/operations/algorithms/checker.py`

## Success Criteria
- QuAcq produces identical KB results (by name, via DescriptionProvider)
- REDUCE called directly without conversion layer
- All tests pass in both modes
- No string constraint IDs in QuAcq pipeline
- Shared infrastructure used by both algorithms
