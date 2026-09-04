# C3 Operation Registry — Implementation Report

## Phase
Phase 17: C3 — operation registry / plugin seam

## Status: DONE

---

## Safety-net confirmation
- `tests/test_oracle_contract.py` present (B3 safety-net: CachedOracle, UserPromptOracle, GroundTruthData) — confirmed green (34 passed)
- `tests/test_boundary_guard.py` green
- Redundancy ops exercised by `test_diagnosis.py` params `wipeoutr_fm_redundancy`, `pysat_redundancy_constraints`, `wipeoutr_t_redundancy` — all green (206 passed)

---

## What was done

### 1. Registry (`explanation/operations/registry.py`) — created

- `register(key, factory)` — raises `KeyError` on duplicate key to prevent silent overwrites
- `get_operation_class(key)` — returns factory; raises `KeyError` with available-keys hint on miss
- `create_operation(key, **kwargs)` — instantiates from registry
- `registered_keys()` — sorted list of all keys

Built-in registrations at module import time:

| Key | Factory |
|-----|---------|
| `'diagnosis'` | `PySATDiagnosis` |
| `'conflict'` | `PySATConflict` |
| `'testcase'` | `PySATTestCase` |
| `'testcase_quickxplain'` | `PySATTestCaseQuickXPlain` |
| `'redundancy_constraints'` | `PySATRedundancyConstraints` |
| `'redundancy_testcases'` | `PySATRedundancyTestCases` |

### 2. Redundancy ops — inherit-then-stub anti-pattern eliminated

**Root cause:** `PySATRedundancyConstraints(PySATDiagnosis)` and `PySATRedundancyTestCases(PySATTestCase)` inherited the HSDAG template-method hierarchy but stubbed `_create_labeler` and `prepare_hsdag` with `pass`, overriding `execute()` entirely. LSP violation — they never used the HSDAG machinery.

**Fix:** Split `PySATAbstractExplanation` into two classes:

- `PySATOperationBase(Operation)` — checker creation (`_create_checker`), solver configuration (`solver_name`, `use_incremental`, `backend`, `profiler`), `get_result()`. No abstract HSDAG methods.
- `PySATAbstractExplanation(PySATOperationBase)` — adds abstract `_create_labeler`, `prepare_hsdag`, `set_result_messages` + concrete `execute()` template. All existing HSDAG-based ops (`PySATDiagnosis`, `PySATConflict`, `PySATTestCase`, `PySATTestCaseQuickXPlain`) still extend this unchanged.

Both redundancy ops now extend `PySATOperationBase` directly:
- `PySATRedundancyConstraints(PySATOperationBase)` — no `prepare_hsdag`, no `_create_labeler`, no stubs
- `PySATRedundancyTestCases(PySATOperationBase)` — same

All state and checker infrastructure is available from `PySATOperationBase` without any HSDAG contract.

### 3. `explanation/api.py` — registry exposed

Added imports and `__all__` entries:
- `get_operation_class`
- `create_operation`
- `get_registered_operation_keys` (aliased from `registered_keys`)

Docstring updated with registered-key table.

### 4. Apps dispatch

Reviewed `apps/run_cv.py:148-178`, `apps/run_quacq.py:58-70`, `apps/run_compare.py:34-51`. All string dispatch is at the conacq-runner level (`'congen'`/`'interactive'` algorithm selection, `ComparationStrategy` enum). These are NOT explanation operations — no explanation operation is selected by string anywhere in apps. Registry does not cleanly apply to these dispatch sites; applying it would add conacq/explanation coupling with no benefit. **No changes to apps.**

### 5. SEQ-1 red-team note

`test_diagnosis.py` imports `PySATRedundancyTestCasesBuilder` and `PySATRedundancyConstraintsBuilder` from `explanation.operations.pysat_explanation_builder` — unchanged. Builders still wrap the (now refactored) ops identically. No import or assertion updates needed.

---

## Files modified

| File | Change |
|------|--------|
| `explanation/operations/pysat_abstract_explanation.py` | Added `PySATOperationBase`; `PySATAbstractExplanation` now extends it |
| `explanation/operations/pysat_redundancy_constraints.py` | Extends `PySATOperationBase` directly; no stubs |
| `explanation/operations/pysat_redundancy_testcases.py` | Extends `PySATOperationBase` directly; no stubs |
| `explanation/operations/registry.py` | Created — registry with built-in registrations |
| `explanation/api.py` | Exports `get_operation_class`, `create_operation`, `get_registered_operation_keys` |

---

## Tests

- Full suite: **568 passed** (baseline 568 — identical)
- `test_diagnosis.py`: 206 passed (includes all 3 redundancy test groups)
- `test_boundary_guard.py`: green
- `test_oracle_contract.py`: green
- `test_solver_backend_port.py`: 8 passed

No assertions weakened. Redundancy outputs identical to pre-refactor.

---

## Success criteria check

- [x] Operation registry exists; ops resolved by key — 6 ops registered
- [x] Redundancy ops no longer inherit-then-stub — no `prepare_hsdag: pass`, no `_create_labeler: pass`; extend `PySATOperationBase` directly
- [x] String-based op dispatch in apps — no explanation ops dispatched by string in apps (conacq-level dispatch not in scope)
- [x] Full suite green (568 = baseline)

---

## Deviations

- Apps dispatch: spec says "where it cleanly applies". Confirmed apps dispatch is conacq-runner selection, not explanation operation selection. Registry not applied to apps — correct per spec qualifier.
- `PySATRedundancyTestCases` previously typed `redundant`/`non_redundant` as `str`; `PySATRedundancyConstraints` typed them as `List`. Both preserved exactly — no behavior change.

## Unresolved questions

None.
