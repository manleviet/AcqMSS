---
phase: 2
title: Unify FMOracleModel
status: completed
priority: P2
effort: 1h
dependencies:
  - 1
---

# Phase 2: Unify FMOracleModel.prepare_task (+ cut dead config path)

## Overview

Change `FMOracleModel.prepare_task(configuration=None)` → `prepare_task(task_input: TaskInput = None)`.
Red-team finding #8: the `configuration` apply-path is **provably dead** (every call-site is no-arg) AND a
`Configuration`-typed `TaskInput.configuration` can't even reproduce the old dict branch — so **cut the dead
path** rather than re-plumb it. FMOracleModel needs no oracle/snapshot (it IS the KB).

## Requirements

- Functional: `prepare_task(task_input=None)` returns the identical `DiagnosisTask` for the (only exercised)
  no-arg path — same set_kb, assumptions, base_set_c, codec, BGData.
- Non-functional: remove dead code; don't add plumbing for an unreachable branch.

## Architecture

`FMOracleModel.prepare_task` accepts `TaskInput` for signature uniformity but FMOracle consumes no per-task
input. The dead `configuration` branch in `FMOracleTaskPreparation.prepare` (the `hasattr(cfg,'elements')`
apply-path) is removed; `prepare(model)` no longer takes a configuration. The oracle's base task
(`FeatureModelOracle.__init__ :61`) and `build()` `:153` are both no-arg → unaffected.

## Related Code Files

- Modify: `conacq/oracle/fm_oracle_model.py` (`prepare_task` signature → TaskInput; assert/ignore any
  per-task fields; import `TaskInput`; drop the `configuration` arg threading into `FMOracleTaskPreparation`)
- Modify: `conacq/oracle/fm_oracle_model.py` `FMOracleTaskPreparation.prepare(model, configuration)` →
  `prepare(model)`; delete the `Step 3b: apply configuration` branch (`:224-233`) and the `configuration`
  param.
- Verify-only (already no-arg): `conacq/oracle/fm_oracle.py:61`, `tests/test_oracle_model.py`
  (`:17,25,39,85,98,106,118`), `tests/test_assumption_slicer.py` (`:415,425,438,448,459`)

## Implementation Steps

1. Import `TaskInput`; change signature `def prepare_task(self, task_input: 'TaskInput' = None) -> DiagnosisTask:`.
2. If `task_input` carries any set field (configuration/test_cases/…), that's a misuse → it is simply unused
   here (FMOracle is the KB); no behavior depends on it. Call `FMOracleTaskPreparation.prepare(self)`.
3. In `FMOracleTaskPreparation.prepare`: drop the `configuration` parameter and delete the Step-3b apply-config
   branch (dead — Phase-1 net + test_oracle_model prove the no-arg path is the only one used).
4. Update docstrings (params: task_input).
5. Green-gate full suite (expect Phase-1 count, unchanged).

## Success Criteria

- [ ] `FMOracleModel.prepare_task(task_input=None) -> DiagnosisTask`; no `configuration` param remains.
- [ ] Dead Step-3b branch removed; Phase-1 oracle safety-net still green (base task unchanged).
- [ ] Full suite green; count unchanged from end of Phase 1.

## Risk Assessment

- Risk: removing the config branch changes behavior IF some caller passed a config. Mitigation: grep proves
  none do (all no-arg); Phase-1 net covers the no-arg base-task path the oracle actually uses.

## Next Steps

Commit `refactor: FMOracleModel.prepare_task takes TaskInput; drop dead configuration path`; proceed to Phase 3.
