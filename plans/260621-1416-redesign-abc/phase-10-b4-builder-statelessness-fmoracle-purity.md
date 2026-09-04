---
phase: 10
title: B4 builder statelessness + FMOracle purity
status: completed
priority: P1
effort: 1-2d
dependencies:
  - 1
  - 3
---

# Phase 10: B4 — kill builder.last_task + FMOracle purity

## Overview
Remove the `builder.last_task` public mutable side-channel (callers must currently "know" to read it after `build()`). Make `build()` return the KB and `prepare_task(...)` return the Task uniformly (already the R3 shape on the Diagnosis side — apply to ConGen/QuAcq). Finish the FMOracle purity fix: `FMOracleTaskPreparation.prepare()` currently mutates the passed-in model (`_pos_assignment_to_assumption`, `_neg_assignment_to_assumption`, `_base_set_c`, `_bg_data`) while advertising a fresh task — move those cached maps onto the returned Task/codec.

## Requirements
- Functional: no `last_task` attribute; `build()`→KB, `prepare_task()`→Task; FMOracle prep does not mutate the input model.
- Non-functional: depends on A2 (builders already share a base); conacq-side.

## Architecture
- Builders: drop `self.last_task`; callers call `prepare_task` explicitly (uniform contract).
- FMOracle prep: the 4 cached maps become fields on the returned Task (or codec), not back-written onto the model.

## Related Code Files (verified)
- Modify: `conacq/algorithms/acqmss/congen_model_builder.py` (last_task :26/:34/:57/:101/:125/:129), `conacq/algorithms/quacq/quacq_model_builder.py` (:23/:32/:50/:73), `conacq/algorithms/quacq/__init__.py` (:27)
- Modify: `conacq/runners/quacq_runner.py` (:179 last_task comment + usage), and any caller reading `.last_task`
- Modify: `conacq/oracle/fm_oracle_model.py` (prep mutation :193-217)

## Implementation Steps
1. Grep all `.last_task` readers; convert each to explicit `prepare_task`.
2. Remove `last_task` from both builders; unify `build()`/`prepare_task()` contracts.
3. Move FMOracle prep's 4 cached maps onto the returned Task/codec; stop mutating the model.
4. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] No `last_task` anywhere (grep clean)
- [ ] `build()`→KB, `prepare_task()`→Task uniform across ConGen/QuAcq/Diagnosis
- [ ] FMOracle prep is pure (no input-model mutation); cached maps on Task/codec
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621) — HIGHEST regression risk in the plan
- **Widen Related Code Files (were missing):** `conacq/oracle/fm_oracle.py` (reads `_oracle_model._base_set_c` :106/:192, codec :104/:178), `tests/test_oracle_model.py` (:67/:90/:110/:122), `tests/test_congen.py` (last_task :64-65/:295-297/:300-370), `tests/test_quacq.py` (:72/:270/:425), `conacq/algorithms/quacq/__init__.py` (:27).
- **Ordering cycle to resolve (collides with the working-tree codec fix):** today `prepare()` writes the maps to the model → `prepare_task()` reads them back to BUILD the codec → the landed fix made `_model_to_config` depend on `_base_task.codec`. Moving maps onto the Task REQUIRES restructuring so `prepare()` hands maps directly to codec construction WITHOUT the model round-trip, THEN re-point `fm_oracle.py` `_base_set_c`/codec reads to the Task/codec. This is a structural step, not a "re-verify".
- **Correctness guard:** assert `model_to_config` output byte-identical pre/post on ≥2 FMs (oracle path feeds every `complete_configuration` query).
- **last_task assertions REPLACED, never deleted:** each `assert builder.last_task is not None`/`len(set_kb)>0` becomes the equivalent assertion on the explicit `prepare_task()` return; target the A7 fixtures, not orphaned inline setup.

## Validate decision (260621)
- **Approach = FULL RESTRUCTURE (user).** `prepare()` hands the 4 cached maps directly to `prepare_task()`/codec with NO model round-trip — eliminating the `prepare()→model→codec` ordering cycle. Do not keep a model-write-then-copy fallback.

## Risk Assessment
- Hidden readers of `last_task` (e.g. in apps/tests) → grep apps/ + tests/ too before removal.
- FMOracle purity may interact with the codec-delegation fix already in the working tree → re-verify model_to_config still consistent after maps move.
