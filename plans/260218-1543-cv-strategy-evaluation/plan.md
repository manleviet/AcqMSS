---
title: "CV Strategy Evaluation"
description: "Add description/clause strategy evaluation to CV pipeline for fold KBs + intersected KB"
status: completed
priority: P1
effort: 2h
branch: main
tags: [feature, evaluation, pipeline]
created: 2026-02-18
---

# CV Strategy Evaluation

## Summary

Add strategy-based evaluation (description/clause) to `run_congen_eval.py` CV pipeline. After CV completes, evaluate each fold KB + intersected KB against oracle FM groundtruth using `Evaluator`. Results saved in `_cv_*.json` + separate eval file.

## Phases

| # | Phase | Status | Effort | File |
|---|-------|--------|--------|------|
| 1 | Add strategy evaluation to run_congen_eval.py | completed | 45m | [phase-01](phase-01-add-strategy-eval.md) |
| 2 | Extend extract_results.py with eval metrics | completed | 30m | [phase-02](phase-02-extend-extract-results.md) |
| 3 | Update docs | completed | 15m | [phase-03](phase-03-update-docs.md) |

## Key Decisions

- Evaluator created once per model, reused for all folds + intersected KB
- `ConGenResultData` built from fold `kb_constraints` with `bg_clauses=[]` (not stored per-fold, not needed for description/clause comparison)
- Strategy evaluation appended to existing CV JSON structure (backward compatible)
- Intersected KB evaluation saved to separate `*_intersected_eval.json`

## Dependencies

- Phase 2 independent of Phase 1 (can work on extract_results.py in parallel if CV JSON structure is agreed)
- Phase 3 after Phase 1-2

## API Reference

- `Evaluator.from_files(oracle_path, bias_path)` → creates evaluator
- `evaluator.evaluate(ConGenResultData, EvaluationStrategy)` → `EvaluationResult`
- `EvaluationResult.to_dict()` → serializable metrics dict
- `CrossValidationFoldResult.kb_constraints` → `List[str]` of constraint IDs per fold
- `CrossValidationResult.intersected_kb` → `List[str]` of shared constraint IDs
