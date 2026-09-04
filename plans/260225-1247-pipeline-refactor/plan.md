---
title: "Pipeline Scripts Refactor"
description: "Refactor 4 monolithic pipeline scripts into 6 focused SRP scripts"
status: completed
priority: P2
effort: 6h
branch: main
tags: [refactor, pipeline, scripts, SRP]
created: 2026-02-25
---

# Pipeline Scripts Refactor

## Context
- Brainstorm: [brainstorm-260225-1219-pipeline-refactor](../reports/brainstorm-260225-1219-pipeline-refactor.md)

## Goal
Refactor 4 scripts → 6 scripts with clear single responsibility:

| Script | Responsibility |
|:---|:---|
| `run_congen.py` | ConGen learning → KB files (fix bg_clauses) |
| `run_interactive.py` | QuAcq learning → KB files (NEW) |
| `run_cv.py` | Unified N-fold CV (NEW) |
| `run_compare.py` | KB vs GroundTruth comparison (NEW) |
| `describe_kb.py` | KB IDs → human-readable (NEW) |
| `extract_results.py` | Results → paper tables (refactor) |

## Design Principles
- KB files: IDs only + bg_clauses (no descriptions)
- Compare always requires bias
- Enrichment only at presentation layer

## Phases

| # | Phase | Status | Effort |
|:--|:------|:-------|:-------|
| 01 | [Fix save_kb_result + shared config](phase-01-fix-save-and-shared-config.md) | completed | 45m |
| 02 | [Create run_compare.py + describe_kb.py](phase-02-compare-and-describe.md) | completed | 1h |
| 03 | [Create run_cv.py](phase-03-unified-cv.md) | completed | 1.5h |
| 04 | [Create run_interactive.py + simplify run_congen.py](phase-04-learning-scripts.md) | completed | 1h |
| 05 | [Refactor extract_results.py](phase-05-refactor-extract-results.md) | completed | 45m |
| 06 | [Cleanup + end-to-end test](phase-06-cleanup-and-test.md) | completed | 1h |

## Success Criteria
- All 6 scripts work independently
- `PYTHONPATH=. pytest tests/ -v` passes
- KB output format consistent (IDs + bg_clauses)
- extract_results.py generates Tables 7,9,10,11
- Old scripts removed
