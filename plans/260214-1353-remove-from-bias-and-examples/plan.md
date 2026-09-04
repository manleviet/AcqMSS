---
title: "Remove from_bias_and_examples, use ConGenModelBuilder"
description: "Replace all ConGenModel.from_bias_and_examples() calls with ConGenModelBuilder pattern (file-path based)"
status: complete
priority: P2
effort: 1.5h
branch: main
tags: [refactor, congen_root, builder-pattern]
created: 2026-02-14
---

# Remove `from_bias_and_examples`, Use `ConGenModelBuilder`

## Summary

Remove `ConGenModel.from_bias_and_examples()` classmethod. All callers migrate to `ConGenModelBuilder` (file-path entry points). Builder's `build()` inlines model construction. CV folds use `prepare()` for per-fold examples.

## Current Call Sites (source code only)

| Caller | File | Input Type |
|--------|------|------------|
| `ConGenModelBuilder.build()` | `congen_model_builder.py:138` | from file loading |
| `ConGenRunner.run()` | `congen_runner.py:156` | raw dicts from `__init__` params |
| `process_model()` | `apps/run_congen.py:131` | raw dicts from file loading |
| `create_checker_and_task()` | `tests/test_congen.py:85` | raw dicts from fixtures |

## Design Decisions

1. **Builder = file-path only** — no `from_bias_data()`, no raw-dict entry points
2. **Examples optional in builder** — CV builds model once, uses `prepare(pos, neg)` per fold
3. **ConGenRunner** accepts `bias_path`+`fm_path` instead of raw dicts; builds model once in `__init__`, calls `prepare()` per fold in `run()`
4. **`n_fold_cross_validation`** and `run_congen_eval.py` change signatures to pass paths

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Refactor builder's `build()`](phase-01-extend-builder.md) | complete | 20min |
| 2 | [Migrate callers](phase-02-migrate-callers.md) | complete | 50min |
| 3 | [Remove method + cleanup](phase-03-remove-and-cleanup.md) | complete | 20min |

## Key Dependencies

- `build()` must stop calling `from_bias_and_examples()` first (Phase 1)
- ConGenRunner API change affects `cross_validation.py` → `run_congen_eval.py` (Phase 2)
- Examples made optional in builder for CV use case (Phase 1)
- Bias shuffle in ConGenRunner: reorder `model.constraint_map` before `prepare()` (Phase 2)

## Risk

- **Medium**: ConGenRunner + CV API changes ripple to `run_congen_eval.py`
- Bias shuffle per fold needs reordering `model.constraint_map` before `prepare()` — verify this works
- Test coverage exists for all call sites
