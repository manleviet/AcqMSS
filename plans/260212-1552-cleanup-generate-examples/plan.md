---
title: "Clean up generate_examples.py and generator code"
description: "Remove redundancy in example generation code (~368 LOC to ~280 LOC, 24% reduction)"
status: completed
priority: P2
effort: 2h
branch: main
tags: [cleanup, refactor, example_generators, DRY]
created: 2026-02-12
---

# Cleanup: generate_examples.py & Generator Code

## Goal

Reduce ~810 total lines across 3 files by ~90 lines (24% reduction in generate_examples.py) via DRY refactoring. No behavior changes.

## Current State

| File | Lines | Issues |
|------|-------|--------|
| `apps/generate_examples.py` | 368 | ModelConfig dataclass unnecessary, strategy mapping verbose, thin wrapper function |
| `acqmss/testcases/generators/random_sampling.py` | 389 | `_generate_valid_config()` duplicated verbatim (49 lines x2) |
| `acqmss/testcases/generators/base.py` | 53 | Missing shared method |

## Phases

| # | Phase | Status | Effort | File(s) |
|---|-------|--------|--------|---------|
| 1 | [Extract _generate_valid_config to base](phase-01-extract-generate-valid-config.md) | completed | 30m | `random_sampling.py`, `base.py` |
| 2 | [Dict-based strategy mapping](phase-02-simplify-strategy-mapping.md) | completed | 20m | `generate_examples.py` |
| 3 | [Remove ModelConfig dataclass](phase-03-remove-model-config-dataclass.md) | completed | 20m | `generate_examples.py` |
| 4 | [Simplify generate_examples_for_strategy](phase-04-simplify-generate-examples-for-strategy.md) | completed | 30m | `generate_examples.py` |

## Dependencies

- Phase 1 is independent (generator package only)
- Phases 2-4 are independent of each other but all modify `generate_examples.py`
- Execute phases 2-4 sequentially to avoid merge conflicts

## Constraints

- No public API changes
- No behavior changes (identical output for same input)
- No existing generator tests to break (verified: none exist)
- Verbose/display output must remain functional

## Estimated Line Savings

| Change | Lines Saved |
|--------|-------------|
| Extract `_generate_valid_config` to base | ~49 lines in `random_sampling.py` |
| Dict-based strategy mapping | ~15 lines in `generate_examples.py` |
| Remove ModelConfig + parse_models | ~20 lines in `generate_examples.py` |
| Simplify/inline strategy dispatcher | ~10 lines in `generate_examples.py` |
| **Total** | **~94 lines** |

## Verification

After each phase: `PYTHONPATH=. python apps/generate_examples.py apps/conf/generate_examples_config.toml -v`
