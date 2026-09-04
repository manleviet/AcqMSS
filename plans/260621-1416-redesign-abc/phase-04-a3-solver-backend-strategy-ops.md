---
phase: 4
title: A3 solver-backend strategy ops
status: completed
priority: P1
effort: 1-2d
dependencies:
  - 1
---

# Phase 4: A3 — solver-backend strategy on operations

## Overview
Fold the SAT4J/PySAT operation variants into one operation parameterised by a solver-backend strategy (PySAT-incremental / PySAT-nonincremental / SAT4J), deleting the `*_sat4j.py` clones where `prepare_hsdag`/`set_result_messages` are byte-identical. This is the op-layer unification; C1 later formalises the layer below it (the backend port).

## Requirements
- Functional: single diagnosis op + single conflict op selecting backend behavior via a strategy arg/enum; outputs identical for each backend.
- Non-functional: framework-isolated in `explanation/operations/`; no behavior change per backend.

## Architecture
- A lightweight backend-strategy parameter on the diagnosis/conflict ops; the only real difference (solver backend wiring) becomes data, not a cloned class.
- Note: this is a precursor to C1's `SolverBackend` port — keep the strategy seam clean so C1 can promote it to a formal port without rework.

## Related Code Files (verified)
- Delete: `explanation/operations/pysat_diagnosis_sat4j.py`, `explanation/operations/pysat_conflict_sat4j.py`
- Modify: `explanation/operations/pysat_diagnosis.py`, `explanation/operations/pysat_conflict.py` (absorb backend selection)
- Modify: callers selecting the sat4j variants (grep for the deleted class names before deleting)
- Add/extend ops tests within this stage

## Implementation Steps
1. Diff each `*_sat4j.py` vs its PySAT sibling; identify the exact backend-specific delta.
2. Add a backend-strategy parameter to the base ops; implement the SAT4J branch as a strategy value.
3. Re-point all callers; delete the 2 clone files.
4. `PYTHONPATH=. pytest tests/ -v` → green (ensure SAT4J path still exercised by a test; add one if missing).

## Success Criteria
- [ ] `pysat_*_sat4j.py` deleted; no duplicated `prepare_hsdag`/`set_result_messages`
- [ ] One diagnosis op + one conflict op cover all backends via strategy
- [ ] SAT4J behavior covered by a test
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **Real caller added to file list:** `explanation/operations/pysat_explanation_builder.py` instantiates the sat4j ops via `for_diagnosis_sat4j()`/`for_conflict_sat4j()` (:19/:22/:193/:202 + docstring :170). Re-point these to the new strategy arg.
- **Clones are NOT byte-identical:** `pysat_diagnosis_sat4j.py` carries an extra `_create_checker(self, task)`. Diff INCLUDING that before folding; preserve its behavior in the strategy.
- **Green-gate guard (SEQ-1):** `test_diagnosis.py` drives the SAT4J path (params `sat4j_with_profiling`/`sat4j_no_profiling` :111-152) through `pysat_explanation_builder`. Before deleting the clones, CONFIRM a test exercises the `for_*_sat4j` builder path (not just `CheckerFactory.create_sat4jchecker`), then **update test_diagnosis sat4j params/imports IN THIS STAGE** — else the full suite is red at end of A3.

## Risk Assessment
- SAT4J path may be under-tested → add a characterization test before deleting clones.
- Strategy seam must anticipate C1 — design it as "backend selection", not a one-off if/else, to avoid C1 rework.
