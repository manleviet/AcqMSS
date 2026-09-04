---
phase: 2
title: A1 unify assumption-slicer
status: completed
priority: P1
effort: 1d
dependencies:
  - 1
---

# Phase 2: A1 — unify assumption-slicer

## Overview
Collapse the 4 reimplementations of assumption-set slicing into one parameterised slicer in `explanation`. This is the most error-prone logic in the system (stride + section offsets); 4 copies = 4 places a stride bug hides. Unblocks B1 (the slicer becomes a public helper so `_ASSUMPTION_PAIR_STRIDE` never crosses the boundary).

## Requirements
- Functional: one slicer producing set_c / set_tc / set_tv / set_neg_tv slices, parameterised by stride (paired vs single) and section offsets; identical outputs to current per-call logic.
- Non-functional: lives in `explanation/` (framework-isolated); both stride constants (`_ASSUMPTION_PAIR_STRIDE=2`, `_ASSUMPTION_SINGLE_STRIDE`) handled by params, not duplicated.

## Architecture
- Single function/class in `explanation/models/task_preparation.py` (or a small new module under `explanation/models/`) taking `assumptions`, section boundaries, and a stride arg.
- The 4 current bodies become thin calls into it.

## Related Code Files (verified)
- Modify: `explanation/models/task_preparation.py` (`_assign_sets` :422 DiagnosisTask, :555 TestCaseTask; stride consts :34/:428; slices :567/:569)
- Modify: `conacq/algorithms/acqmss/task_preparation.py` (`_assign_sets` :223; slices :233/:236/:238)
- Modify: `conacq/algorithms/quacq/task_preparation.py` (`_assign_sets` :126; slice :129)
- Rewrite tests for affected prep within this stage (use A7 fixtures)

## Implementation Steps
1. Design the parameterised slicer signature covering all 4 call shapes (paired/single stride, with/without tc/tv sections).
2. Implement in `explanation/`; unit-test it directly (characterization against current outputs on ≥2 FMs).
3. Replace the 4 bodies with calls; conacq still imports the stride constant for now (boundary cleanup deferred to B1).
4. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] One slicer implementation; the 4 `_assign_sets` bodies delegate to it (no duplicated slice arithmetic)
- [ ] Both stride modes covered by params (no hardcoded `2` outside the constant)
- [ ] Slicer has direct unit tests
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **5th slice site (was missing):** add `conacq/oracle/fm_oracle_model.py` (imports `_ASSUMPTION_PAIR_STRIDE` :19; slices `range(0, assignments_start_index, _ASSUMPTION_PAIR_STRIDE)` :197-198) to the file list and route it through the unified slicer — otherwise "no duplicated slice arithmetic" / "stride const never crosses the boundary" is false (4th conacq leak).
- **Slicer takes stride as a plain `int` arg** → conacq call-sites pass `2` and STOP importing `_ASSUMPTION_PAIR_STRIDE` immediately (shrinks B1's leak-removal to zero). Constant stays internal to `explanation`.
- **Divergent semantics — not 4 shapes of one slicer.** DiagnosisTask `_assign_sets` (:422) has 5 branches (with_cf_in_c / test_case / has_negated_forms / variable step). Characterization MUST pin EXACT set_c/set_b/set_tc/set_tv/set_neg_tv for ALL 5 call sites across both stride modes AND both `with_cf_in_c` values AND the test_case/redundancy branches, BEFORE swapping.
- **Extra safety-net:** `conacq/algorithms/oracle_aware_task_preparation.py` (untested, consumed by both conacq preps) — characterize the caller integration outputs, not only the extracted helper.

## Risk Assessment
- Off-by-one / stride regression is the central hazard — mitigate with direct characterization tests BEFORE swapping callers, and assert exact set contents on multiple FMs (arcade-game + one large).
