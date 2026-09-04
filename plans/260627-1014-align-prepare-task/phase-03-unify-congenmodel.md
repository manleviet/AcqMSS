---
phase: 3
title: OracleTaskData snapshot + ConGenModel
status: completed
priority: P2
effort: 4h
dependencies:
  - 2
---

# Phase 3: Frozen OracleTaskData snapshot + unify ConGenModel.prepare_task

## Overview

Introduce the **frozen `OracleTaskData` snapshot** mechanism (red-team #1 user decision: snapshot, NOT live
oracle), fold it onto the model at build via the `_post_negation_build` hook, and drop the `oracle` parameter
from `ConGenModel.prepare_task`. After this phase `ConGenModel.prepare_task(task_input) -> ConGenTask`.

## Requirements

- Functional: produced `ConGenTask` byte-identical to today (verified by Phase-1 task-content net).
- Non-functional: model holds only frozen data (no live SAT solver); honors the documented "immutable KB"
  contract. Snapshot built once at build, never mutated.

## Architecture

`OracleTaskData` = frozen carrier exposing exactly the pure reads task-prep needs:
`get_bg_data()`, `get_c()`, `get_kb()`, `get_assumptions()` (today these read `oracle._base_task`/`bg_data` —
all immutable snapshots). `OracleTaskData.from_oracle(oracle)` snapshots them at build. `GenerateNE` and
`ConGenTaskPreparation` are re-typed from `FeatureModelOracle` to this carrier (a `BGDataProvider`-style
Protocol) — their bodies are unchanged (same method names). The base `OracleBiasModelBuilder` does NOT inject
on the shared path; each subclass `_post_negation_build(model)` sets `model._oracle_data =
OracleTaskData.from_oracle(self._oracle)` (red-team #5: avoids undeclared-attr injection). `ConGenModel`
declares `self._oracle_data = None` in `__init__`; `prepare_task(task_input)` reads it.

## Related Code Files

- Create: `conacq/oracle/oracle_task_data.py` (`OracleTaskData` frozen dataclass + `from_oracle`; export via
  `conacq/oracle/__init__.py`)
- Modify: `conacq/algorithms/acqmss/congen_model_builder.py` (`_post_negation_build` builds + stashes snapshot)
- Modify: `conacq/algorithms/acqmss/congen_model.py` (`__init__` add `_oracle_data`; `prepare_task` drop oracle
  param, read `self._oracle_data`; pass to `ConGenTaskPreparation.prepare(self, task_input, self._oracle_data)`)
- Modify: `conacq/algorithms/acqmss/generate_ne.py` (re-type `__init__(self, oracle_data)`; body unchanged —
  still `get_c/get_kb/get_assumptions`)
- Modify: `conacq/algorithms/acqmss/task_preparation.py` (`ConGenTaskPreparation.prepare` param type → carrier)
- Modify (real call-site): `conacq/runners/congen_runner.py:118` → `self.model.prepare_task(task_input)`
- Modify (tests): `tests/test_congen.py` (`:57,289,312,341,346,371`), `tests/test_assumption_slicer.py`
  **lines 311 + 518 ONLY** (ConGen fixtures; red-team #7 — do NOT touch 370/535 here)
- Modify (docstrings): `conacq/algorithms/acqmss/congen_model_builder.py` (`:30,40,48,92`)

## Implementation Steps

1. Create `OracleTaskData` (frozen): fields snapshotting bg_data + set_c + set_kb + assumptions; methods
   `get_bg_data/get_c/get_kb/get_assumptions`; classmethod `from_oracle(oracle)`.
2. `GenerateNE.__init__` + `ConGenTaskPreparation.prepare`: accept the carrier (Protocol) instead of the
   oracle. Bodies unchanged.
3. `congen_model_builder._post_negation_build(model)`: `model._oracle_data = OracleTaskData.from_oracle(self._oracle)`.
4. `congen_model.py`: `__init__` declares `self._oracle_data = None`; `prepare_task(self, task_input) -> ConGenTask`
   reads `self._oracle_data`, guards `None` with a message naming `.with_oracle()` (belt-and-suspenders;
   `build()._validate` already enforces oracle — red-team #10, do NOT frame as a real risk).
5. Acceptance assertion (red-team #6): in a test, `model._oracle_data.get_bg_data() is runner.oracle.get_bg_data()`
   (or equivalent identity) — the snapshot derives from the runner's one oracle.
6. Update `congen_runner.py:118`, the 6 ConGen test sites, slicer lines 311+518, and the 3 docstrings.
7. Green-gate: full suite **plus** `uv run --no-sync pytest tests/test_assumption_slicer.py tests/test_congen.py
   tests/test_prepare_task_content_safety_net.py -q` (catch any shared-file cross-boundary edit in-phase).

## Success Criteria

- [ ] `OracleTaskData` frozen; built once at build; no live oracle/solver on the model.
- [ ] `ConGenModel.prepare_task(task_input) -> ConGenTask`; no caller passes oracle.
- [ ] Phase-1 ConGen task-content net (incl. `set_neg_tv`) unchanged.
- [ ] Slicer 370/535 (QuAcq) still call `prepare_task(oracle)` (untouched until Phase 4); full suite green.

## Risk Assessment

- Risk: snapshot misses a field GenerateNE/prep needs. Mitigation: carrier exposes exactly the 4 methods used
  (grep-verified: generate_ne.py:86,118,119 + task_preparation.py:95); Phase-1 net catches any drift.
- Risk: `_post_negation_build` is currently a no-op seam intended for auto-prepare. Mitigation: stash there is
  inert w.r.t. prepare; document that it runs before `return model`.

## Next Steps

Commit `refactor: fold frozen OracleTaskData snapshot onto model; ConGenModel.prepare_task drops oracle`;
proceed to Phase 4.
