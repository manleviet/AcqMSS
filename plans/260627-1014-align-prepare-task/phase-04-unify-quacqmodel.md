---
phase: 4
title: Unify QuAcqModel
status: completed
priority: P2
effort: 2h
dependencies:
  - 3
---

# Phase 4: Unify QuAcqModel.prepare_task (reject non-empty TaskInput)

## Overview

Drop the `oracle` parameter from `QuAcqModel.prepare_task(oracle)` → `prepare_task(task_input: TaskInput = None)`,
reading the frozen `self._oracle_data` snapshot (stashed via the builder hook in Phase 3). Red-team #2 user
decision: QuAcq is interactive and uses NO per-task input, so it **rejects a non-empty TaskInput** with a clear
error (no silent drop) rather than ignoring it.

## Requirements

- Functional: produced `QuAcqTask` byte-identical to today (verified by Phase-1 QuAcq task-content net).
- Non-functional: passing a non-empty `TaskInput` raises a clear `ValueError`; uniform signature preserved.

## Architecture

`QuAcqModel.prepare_task(task_input=None)` validates `task_input` is None/empty (else raise), reads
`self._oracle_data`, and calls `QuAcqTaskPreparation.prepare(self, self._oracle_data)` (re-typed to the
carrier). Codec build (id_to_name + pos/neg maps from `oracle_data.get_bg_data()`) unchanged. The
`_oracle_data` field is set by `quacq_model_builder._post_negation_build` (mirrors Phase 3) and declared in
`QuAcqModel.__init__` (red-team #5 — unconditional declaration, avoids AttributeError).

## Related Code Files

- Modify: `conacq/algorithms/quacq/quacq_model.py` (`__init__` declare `self._oracle_data = None`;
  `prepare_task(task_input=None)` reject non-empty, read `self._oracle_data`)
- Modify: `conacq/algorithms/quacq/quacq_model_builder.py` (`_post_negation_build` stashes snapshot; `:25,41`
  docstrings)
- Modify: `conacq/algorithms/quacq/task_preparation.py` (`QuAcqTaskPreparation.prepare` param type → carrier)
- Modify (real call-site): `conacq/runners/quacq_runner.py:280` → `self.model.prepare_task(TaskInput())`
  (import `TaskInput`)
- Modify (tests): `tests/test_quacq.py` (`:55,253,420,425`), `tests/test_assumption_slicer.py`
  **lines 370 + 535 ONLY** (red-team #7)
- Modify (docstrings): `conacq/algorithms/quacq/__init__.py:27`

## Implementation Steps

1. `quacq_model_builder._post_negation_build(model)`: `model._oracle_data = OracleTaskData.from_oracle(self._oracle)`.
2. `quacq_model.py` `__init__`: add `self._oracle_data: Optional[OracleTaskData] = None`.
3. `quacq_model.py` `prepare_task(self, task_input: TaskInput = None) -> QuAcqTask`: if `task_input` is not
   None and carries any set field → `raise ValueError("QuAcqModel.prepare_task takes no per-task input ...")`;
   read `self._oracle_data` (guard None → message naming `.with_oracle()`); call
   `QuAcqTaskPreparation.prepare(self, self._oracle_data)`. Add a `_is_empty(task_input)` helper or check the
   known TaskInput fields.
4. Re-type `QuAcqTaskPreparation.prepare` param to the carrier; body unchanged.
5. Update `quacq_runner.py:280`, the 6 test sites, slicer 370/535, and the docstring example.
6. Add acceptance assertion that `model._oracle_data` derives from `runner.oracle` (red-team #6).
7. Green-gate: full suite + targeted `pytest tests/test_assumption_slicer.py tests/test_quacq.py -q`.

## Success Criteria

- [ ] `QuAcqModel.prepare_task(task_input=None) -> QuAcqTask`; non-empty TaskInput raises ValueError.
- [ ] All four models share `prepare_task(task_input) -> Task`.
- [ ] Phase-1 QuAcq task-content net unchanged; full suite green.

## Risk Assessment

- Risk: the non-empty check rejects a legitimate empty `TaskInput()` (e.g. all-None). Mitigation: `_is_empty`
  treats the default `TaskInput()` (all fields None/False) as empty → allowed; only set fields raise.
- Risk: Phase-3 hook must have run for `_oracle_data` to exist. Mitigation: dependency on Phase 3; declared
  field defaults None → clear guard, not AttributeError.

## Next Steps

Commit `refactor: QuAcqModel.prepare_task takes TaskInput (rejects non-empty); reads frozen snapshot`;
proceed to Phase 5.
