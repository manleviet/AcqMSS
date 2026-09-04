---
title: "Unified CV Output JSON"
description: "Consolidate CV pipeline output into single JSON file per experiment run"
status: completed
priority: P1
effort: 6h
branch: main
tags: [refactor, pipeline, output-format]
created: 2026-02-26
---

# Unified CV Output JSON

## Overview

Refactor the CV pipeline to consolidate output from 45+ files per model into a single unified JSON file per (model x strategy x mode). Currently `run_cv.py` produces 1 CV summary + N fold KBs + 1 intersected KB, and `run_compare.py` adds N fold evals + 1 intersected eval. This plan merges everything into one self-contained file.

## Phases

| # | Phase | Status | Est |
|---|-------|--------|-----|
| 1 | [Enrich CrossValidationResult with descriptions](phase-01-enrich-cv-result.md) | completed | 1.5h |
| 2 | [Refactor run_cv.py to emit unified JSON](phase-02-refactor-run-cv.md) | completed | 1h |
| 3 | [Refactor run_compare.py to read/write unified JSON](phase-03-refactor-run-compare.md) | completed | 2h |
| 4 | [Update extract_results.py for unified format](phase-04-update-extract-results.md) | completed | 1h |
| 5 | [Tests and cleanup](phase-05-tests-cleanup.md) | completed | 0.5h |

## Key Decisions

- **Bias loaded once per model** in `run_cv.py` to resolve constraint IDs to descriptions at CV time
- `kb_constraints` in folds/intersected become `[{"id": "c_12", "description": "f1 => f2"}, ...]`
- `evaluation` and `summary` fields are `null` after `run_cv.py`; populated by `run_compare.py`
- `save_cv_kb_files()` removed from public API; replaced by unified JSON serialization
- `run_compare.py` reads/writes same file (idempotent overwrite of eval fields)
- `ConGenResultData.from_dict()` classmethod added (no file I/O) for in-memory fold data

## File Impact Summary

| File | Action |
|------|--------|
| `conacq/eval/cross_validation.py` | Modify `CrossValidationFoldResult.to_dict()` + `CrossValidationResult.to_dict()` to include descriptions |
| `conacq/eval/report.py` | Remove `save_cv_kb_files()`; add `generate_unified_cv_dict()` |
| `conacq/eval/result_loader.py` | Add `ConGenResultData.from_dict()` classmethod |
| `conacq/eval/kb_comparator.py` | Add `to_enriched_dict()` on `ComparationResult` for id+description TP/FP/FN |
| `conacq/eval/__init__.py` | Update exports |
| `apps/run_cv.py` | Load bias, pass to unified dict builder, write single JSON |
| `apps/run_compare.py` | Rewrite to read unified JSON, compare folds+intersected, write back |
| `apps/extract_results.py` | Update `load_cv_result()` to read from unified format |
| `conacq/eval/config.py` | Add `find_cv_files()` to find `*_cv_*.json` files |
