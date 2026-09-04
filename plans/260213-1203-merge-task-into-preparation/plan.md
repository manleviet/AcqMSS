---
title: "Merge task.py into task_preparation.py"
description: "Consolidate ConGenTask dataclass into task_preparation module"
status: complete
priority: P3
effort: 15m
branch: main
tags: [refactor, consolidation]
created: 2026-02-13
---

# Merge task.py into task_preparation.py

## Rationale

`task.py` (42 lines) contains only `CONGENTask` dataclass. `task_preparation.py` (178 lines) already imports it. Merging yields ~220 lines — within guideline. Both share same concern: CONGEN task data + preparation.

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Merge and update imports | complete | [phase-01](phase-01-merge-and-update-imports.md) |

## Affected Files

- `acqmss/algorithms/task.py` — DELETE
- `acqmss/algorithms/task_preparation.py` — ADD `CONGENTask` class
- `acqmss/algorithms/__init__.py` — update import source
- `acqmss/algorithms/congen.py` — update import source
- `acqmss/algorithms/model.py` — update import source

## Success Criteria

- All tests pass
- No broken imports
- `task.py` deleted
- `__init__.py` still exports `CONGENTask`
