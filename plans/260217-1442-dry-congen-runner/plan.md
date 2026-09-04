---
title: "Extract runners into acqmss/runners/ and DRY apps/run_congen.py"
description: "Move ConGenRunner + InteractiveRunner to own package, refactor run_congen.py to reuse ConGenRunner"
status: pending
priority: P2
effort: 1h
branch: refactor/dry-congen-runner
tags: [refactor, DRY, runners]
created: 2026-02-17
---

# Extract Runners & DRY run_congen.py

## Problem

1. `ConGenRunner` and `InteractiveRunner` live in `acqmss/eval/` but they're **execution harnesses**, not evaluation logic
2. `apps/run_congen.py:process_model()` **duplicates** ConGenRunner logic inline (build model → prepare → create checker → run ConGen → cleanup)

## Phases

| # | Phase | Status | Files |
|---|-------|--------|-------|
| 1 | [Move runners to acqmss/runners/](phase-01-move-runners.md) | pending | 6 files |
| 2 | [Refactor run_congen.py to use ConGenRunner](phase-02-dry-run-congen.md) | pending | 1 file |

## Key Dependencies

- `performance_metrics.py` stays in `acqmss/eval/` (shared by evaluator, report, etc.)
- Runners import `PerformanceMetrics` — relative import changes to absolute
- `cross_validation.py` imports both runners — update to new location
- Backward compat: `from acqmss.eval import ConGenRunner` still works via re-export

## Validation

```bash
PYTHONPATH=. pytest tests/ -v
PYTHONPATH=. python -c "from acqmss.eval import ConGenRunner, InteractiveRunner"
PYTHONPATH=. python -c "from acqmss.runners import ConGenRunner, InteractiveRunner"
```
