---
phase: 13
title: C7 labeler template + algorithm twins
status: completed
priority: P2
effort: 1-2d
dependencies:
  - 11
---

# Phase 13: C7 — labeler template base + algorithm-twin parameterisation

## Overview
Two pure DRY/cohesion wins. (1) The 5 labelers repeat ~200 lines of the same 4 methods + a near-identical `*Parameters.__str__`; `identify_new_node_parameters` is the same `copy→remove→append` in each. Fold into a template base. (2) Algorithm twins share the core, differing only by test-case + checker-method: `quickxplain` vs `quickxplain_with_testcases` (`_qx` split/recursion), and `wipeoutr_fm` vs `wipeoutr_t` (same redundancy loop, different test-set formula).

## Safety-net
Labelers/algorithms run under HSDAG diagnosis tests (test_diagnosis) but verify coverage of each twin's distinct path before parameterising; add cases if a branch is uncovered.

## Requirements
- Functional: a labeler template base implementing the shared 4 methods + `*Parameters` `__str__`; subclasses supply only the diff. Twins collapse to one parameterised function each (test-case + checker-method as params).
- Non-functional: framework-isolated; outputs identical for every diagnosis/conflict algorithm.

## Architecture
- `labeler.py` base gains the template methods; `fastdiag_labeler`/`quickxplain_labeler`/`kbdiag_labeler`/`quickxplain_with_testcases_labeler` override only specifics.
- `quickxplain` core parameterised by optional `test_case` + checker method; `wipeoutr` core parameterised by test-set formula + loop form.

## Related Code Files (verified)
- Modify: `explanation/operations/algorithms/hsdag/labeler/labeler.py` (base) + `fastdiag_labeler.py` (:53-66), `quickxplain_labeler.py` (:52-64), `kbdiag_labeler.py` (:64-82), `quickxplain_with_testcases_labeler.py` (:125-162)
- Modify: `explanation/operations/algorithms/quickxplain.py` (:61-101) + `quickxplain_with_testcases.py` (:136-190; also the `find_conflict_set` return-type smell :132-133)
- Modify: `explanation/operations/algorithms/wipeoutr_fm.py` (:43-98) + `wipeoutr_t.py` (:50-116)

## Implementation Steps
1. Confirm test coverage of each twin's distinct branch; add safety-net cases if missing.
2. Build labeler template base; collapse the 5 labelers to specifics-only.
3. Parameterise the qx and wipeoutr cores; delete the twin duplication.
4. Fix the qxtc `find_conflict_set` return-type inconsistency while there.
5. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [x] Labeler template base: get_type/get_initial_parameters hoisted (identify_new_node_parameters genuinely differs per labeler — kept per-labeler, verified)
- [x] qx/qxtc and wipeoutr_fm/_t: **documented intentional-separate** (user-ratified 260622) — not merged. Each twin carries a cross-ref comment stating the reason (different loop structure / distinct metric-key decorators). Behavior + metric-key preservation > DRY here.
- [x] qxtc return type consistent (docstring fixed)
- [x] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **Preserve BOTH twin metric keys (else C2 silently zeroes them):** the `@measure_time`/`@count_calls` keys differ — qx (`qx_calls`/`qx_runtime`) vs qxtc (`qx_with_testcases_calls`/`_runtime`); `wipeoutr_fm_*` vs `wipeoutr_t_*`. C2's aggregate registry reads these BY NAME. The merged function MUST emit both (param-selected label), not collapse to one.
- **wipeoutr twins are structurally different algorithms:** `wipeoutr_fm` = `for` loop + in-place `remove`; `wipeoutr_t` = `while ... pop()` + nested candidate loop + early-return. If unifying changes iteration order / removal semantics, KEEP the loop bodies separate and parameterise ONLY the test-set formula + checker method. Safety-net: assert exact `(redundant, non_redundant)` ID lists for both on an order-sensitive FM (multiple mutually-redundant constraints).
- **Labeler arity differs:** qxtc labeler calls `find_conflict_set` (returns `test_case, conflict_set`; unwraps single-element list :104/:182-183); plain qx labeler calls `find_conflict` (single return). The template base MUST preserve both call shapes.
- **Owns the test_diagnosis migration (SEQ-1):** convert `@parameterized.expand`→`@pytest.mark.parametrize` preserving EVERY `ENABLED_TESTS`/`ENABLED_PARAMS` combination (no dropped params = no weakened matrix); update qx/wipeoutr/labeler imports in-stage.

## Deviations (260621) — FOR USER RATIFICATION at Phase C checkpoint
- **Labeler base = partial (2 methods, not 4).** Only `get_type`+`get_initial_parameters` hoisted. `identify_new_node_parameters` + `*Parameters.__str__` left per-labeler — VERIFIED genuinely different (qx skips the C→B append; kbdiag adds set_tcp/set_neg_tv + a distinct constructor; different assertion class each). The brief's "same copy→remove→append" was an oversimplification; folding would be conditional-laden anti-DRY. Independent code-review agreed.
- **Algorithm twins NOT merged (qx/qxtc + wipeoutr_fm/_t kept separate).** wipeoutr per red-team (structurally different). qx/qxtc: the `_qx` recursion is ~identical, BUT the distinct metric keys live in `@measure_time`/`@count_calls` decorators; sharing `_qx` while preserving BOTH key sets (red-team C2 requirement) forces converting decorators → manual param-selected timer/counter calls on diagnosis-critical recursion — risk to correctness + the C2 metric contract outweighs the ~15-line gain. Both my analysis and the independent reviewer recommend keep-separate (same "behavior-preservation > DRY" the red-team invoked for wipeoutr).
- **Net C7 delivery:** labeler `get_type`/`get_initial_parameters` dedup + test_diagnosis pytest migration (206 cases preserved) + qxtc docstring fix. The twin-parameterisation DRY win was NOT achieved. **User: ratify keep-separate, or request the qx/qxtc merge (doable post-checkpoint; independent of C2's files).**

## Risk Assessment
- Diagnosis correctness is critical → keep the parameterisation behavior-preserving; rely on test_diagnosis + any added branch cases; assert identical diagnoses pre/post on multiple FMs.
