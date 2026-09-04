---
title: "Add test assertions for root constraint in BG"
description: "Verify root_feature_id propagation through ConGen, QuAcq, and evaluator"
status: complete
priority: P2
effort: 1h
branch: main
tags: [tests, root-constraint, bg, verification]
created: 2026-02-12
---

# Test Root BG Verification

## Problem

Commit 08b4d39 added root constraint to BG but no tests verify the new behavior. Tests pass only because changes are backward-compatible (Optional defaults).

## Phases

- [Phase 1](./phase-01-test-congen-root.md) — CONGEN: Verify set_b and bg_clauses
- [Phase 2](./phase-02-test-interactive-root.md) — QuAcq: Verify task.background
- [Phase 3](./phase-03-test-evaluator-bg.md) — Evaluator: Verify BG union in clause eval

## Success Criteria

- New assertions verify root in set_b (both modes)
- New assertions verify background=[root_id] in InteractiveTask
- New test verifies evaluator includes bg_clauses in clause comparison
- All tests pass (existing + new)
