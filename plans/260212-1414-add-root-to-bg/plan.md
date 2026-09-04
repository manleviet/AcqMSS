---
title: "Add root constraint [1] to background knowledge (BG)"
description: "Fix root constraint missing from BG in ConGen/QuAcq, causing FN in clause eval"
status: complete
priority: P1
effort: 3h
branch: main
tags: [bugfix, root-constraint, bg, evaluation]
created: 2026-02-12
---

# Add Root Constraint [1] to Background Knowledge

## Problem

Root constraint [1] exists in Oracle CNF but NOT in BG in either pipeline:
- CONGEN: BG always [] (line 83 task_preparation.py)
- QuAcq: BG always [] (line 184 learner.py)

Original DiagnosisModel puts root in set_b (line 461, 466, 473, 478 explanation/models/task_preparation.py), but CONGENModel/InteractiveLearner bypass this.

**Impact**: Root [1] counted as false negative in clause-based eval.

## Solution Overview

Add root_feature_id parameter to from_bias_and_examples(), propagate through task preparation → set_b/background.

## Phases

- [Phase 1](./phase-01-congen-root-propagation.md) — CONGEN: Add root to set_b via task preparation
- [Phase 2](./phase-02-interactive-root-propagation.md) — QuAcq: Add root to InteractiveTask.background
- [Phase 3](./phase-03-evaluator-bg-union.md) — Evaluator: Include BG in KB when comparing (KB ∪ BG vs Oracle)

## Success Criteria

- All 285 tests pass
- REAL-FM-7 clause-based eval: FN for root [1] disappears
- BG properly included in both pipelines
- No impact on description-based eval (root has no description)

## Notes

Root ID typically 1, identified as feature with no parent in feature_ids dict. Must extract from FeatureModelOracle or flamapy FM structure.
