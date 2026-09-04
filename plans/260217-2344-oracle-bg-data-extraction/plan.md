---
title: "Oracle BG Data Extraction for ConGen"
description: "Refactor ConGenTaskPreparation to extract BG data from Oracle via post-extraction dataclass, eliminating _prepare_bg, FMData dependency, and skip arithmetic"
status: complete
priority: P2
effort: 2h
branch: main
tags: [refactoring, oracle, congen, dry]
created: 2026-02-17
---

# Oracle BG Data Extraction for ConGen

## Context
- Brainstorm: [brainstorm report](../reports/brainstorm-260217-2344-oracle-bg-data-extraction.md)
- Explorer: [code analysis](../reports/code-explorer-260217-2344-oracle-bg-refactor.md)

## Problem
`ConGenTaskPreparation._prepare_bg` duplicates root BG logic Oracle already computes. Manual ID skip arithmetic is fragile and tightly coupled to Oracle's internal layout. `FMData` is passed to ConGenTaskPreparation only for 2 fields (`root_feature`, `num_constraints`) that Oracle already knows.

## Shared Assumption ID Layout
```
Part 1: Feature variable IDs (1..n)               <- FmToDiagPysat
Part 2: Tseitin vars (negated FM constraints)      <- FmToDiagPysat
Part 3: FM constraint assumptions (paired)         <- OracleTaskPreparation
Part 4: Variable assignment assumptions (paired)   <- OracleTaskPreparation
Part 5: Tseitin vars (negated bias constraints)    <- ConGenTaskPreparation
Part 6: Bias constraints (paired)                  <- ConGenTaskPreparation
Part 7: Positive test cases (paired)               <- ConGenTaskPreparation
Part 8: NE + negated NE                            <- ConGenTaskPreparation
```
Oracle owns Parts 1-4. ConGen owns Parts 5-8. ConGen needs Part 3's first pair + end-of-Part-4 ID.

## Implementation Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Create BGData + Oracle extraction](phase-01-bgdata-oracle-extraction.md) | complete | 45m |
| 2 | [Refactor ConGenTaskPreparation](phase-02-refactor-congen-task-preparation.md) | complete | 30m |
| 3 | [Document ID layout + cleanup](phase-03-document-and-cleanup.md) | complete | 20m |
| 4 | [Test and verify](phase-04-test-and-verify.md) | complete | 25m |

## Files Changed
- **New**: `conacq/oracle/bg_data.py`
- **Modified**: `fm_oracle_model.py`, `fm_oracle.py`, `task_preparation.py`, `congen_model.py`
- **Unchanged**: `fm_data.py`, `learner.py`, `congen_runner.py`, tests

## Key Risks
1. Root must be first entry in `constraint_map` — add assertion
2. `DescriptionProvider` needs bulk-read method for BGData descriptions
3. `congen_model.py:187-188` becomes dead code — remove
