---
title: "Simplify ConGen Pipeline"
description: "Remove dead code paths, consolidate pipeline to 2 core scripts"
status: complete
priority: P2
effort: 2h
branch: main
tags: [refactor, cleanup, pipeline]
created: 2026-02-18
---

# Simplify ConGen Pipeline

## Summary

Consolidate 4-script pipeline to 2 core scripts + 1 dev utility. Remove dead code paths identified during analysis.

**Current**: `run_congen` → `run_congen_eval` (Option1 + Option2) → `evaluate_congen_results` → `extract_results`
**Target**: `run_congen_eval` (CV only) → `extract_results` (extended with fold metrics)

## Phases

| # | Phase | Status | Effort | File |
|---|-------|--------|--------|------|
| 1 | Clean `run_congen_eval.py` — remove Option 1 | complete | 30m | [phase-01](phase-01-clean-congen-eval.md) |
| 2 | Delete `evaluate_congen_results.py` + config | complete | 10m | [phase-02](phase-02-delete-evaluate-script.md) |
| 3 | Extend `extract_results.py` — read fold metrics | complete | 40m | [phase-03](phase-03-extend-extract-results.md) |
| 4 | DRY cleanup `extract_results.py` — abstract table format | complete | 30m | [phase-04](phase-04-dry-extract-results.md) |
| 5 | Update docs + configs | complete | 10m | [phase-05](phase-05-update-docs.md) |

## Key Decisions

- Keep `run_congen.py` as dev/debug tool (not in paper pipeline)
- `_cv_*.json` already contains precision/recall/F1 per fold — no need for separate evaluation
- `extract_results.py` becomes the single table generation entry point

## Dependencies

- Phase 2 depends on Phase 1 (clean eval before deleting related script)
- Phase 3-4 independent of Phase 1-2
- Phase 5 after all others
