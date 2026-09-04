---
phase: 17
title: C3 operation registry plugin seam
status: completed
priority: P2
effort: 2d
dependencies:
  - 4
  - 9
  - 11
  - 14
---

# Phase 17: C3 — operation registry / plugin seam

## Overview
Register operations (diagnosis / conflict / testcase / redundancy) by key so the redundancy ops stop inheriting-then-stubbing (`PySATRedundancyConstraints(PySATDiagnosis)` then `_create_labeler: pass` + `prepare_hsdag: pass` + overridden `execute` — an LSP violation). Aligns with the flamapy-plugin publish target. MANDATORY — do not defer (if it balloons, split + report).

## Safety-net
Requires oracle tests (cached/user_prompt/ground_truth) — already added in B3. If for any reason B3's safety-net is incomplete, complete it here BEFORE refactoring.

## Requirements
- Functional: an operation registry keyed by operation type; redundancy ops are first-class registered operations (no inherit-from-diagnosis-then-stub); `execute(task)` dispatch via registry.
- Non-functional: framework-isolated; extensibility seam for the plugin target; no behavior change.

## Architecture
- `explanation/operations/registry.py`: `register(key, factory)` + lookup; operations self-register (or registered centrally).
- Redundancy ops become standalone registered operations, not `PySATDiagnosis` subclasses.

## Related Code Files (verified)
- Create: `explanation/operations/registry.py`; update B1 surface to expose registry-based operation access
- Modify: `explanation/operations/pysat_redundancy_constraints.py` (class :14 inherits PySATDiagnosis; `_create_labeler` :36 pass; `prepare_hsdag` :39-40 pass; `execute` :42), `pysat_redundancy_testcases.py` (same pattern)
- Modify: callers selecting ops by string (`apps/run_cv.py:148-178`, `run_quacq.py:58-70`, `run_compare.py:34-51`) → registry lookup

## Implementation Steps
1. Confirm oracle safety-net (from B3) is present.
2. Build the operation registry; register diagnosis/conflict/testcase ops.
3. Convert redundancy ops to standalone registered operations (drop inherit-then-stub).
4. Re-point string-based op dispatch in apps to registry lookup.
5. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] Operation registry exists; ops resolved by key
- [ ] Redundancy ops no longer inherit-then-stub (no `prepare_hsdag: pass`)
- [ ] String-based op dispatch replaced by registry lookup
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **test_diagnosis green-gate (SEQ-1):** `test_diagnosis.py` drives redundancy ops via `PySATRedundancyTestCasesBuilder`/`PySATRedundancyConstraintsBuilder` (params :94-98). When the redundancy ops are converted to registered operations, UPDATE test_diagnosis's redundancy params/imports IN THIS STAGE — else the full suite is red at end of C3.

## Risk Assessment
- Most plugin-specific / least about current pain → highest balloon risk. If effort explodes, SPLIT (registry first, redundancy conversion second, apps dispatch third) and report — do NOT cut to "deferred".
