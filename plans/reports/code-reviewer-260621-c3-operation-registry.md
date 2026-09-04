# Code Review — C3 Operation Registry + Redundancy First-Class Conversion

Date: 2026-06-21
Reviewer: code-reviewer
Branch: feat/redesign-abc
Scope: uncommitted working-tree changes only (prior stages out of scope)
Spec: plans/260621-1416-redesign-abc/phase-17-c3-operation-registry-plugin-seam.md

## Verdict: PASS

568 passed / 0 failed / 0 warnings (`uv run --no-sync pytest tests/ -q`), matches baseline exactly. No flaky test triggered. Refactor is behavior-preserving; registry is sound; no inherit-then-stub residue; surface + boundary green; no plan-stage labels in code.

## Scope
- Files: explanation/api.py (M), explanation/operations/pysat_abstract_explanation.py (M), pysat_redundancy_constraints.py (M), pysat_redundancy_testcases.py (M), explanation/operations/registry.py (new)
- LOC: +116 / -77 across modified; registry.py 106 lines
- Focus: recent uncommitted changes

## Behavior-Preservation Verdicts

### (1) Redundancy ops behavior-preserving — CONFIRMED
Diffed working-tree vs `git show HEAD:` for both redundancy ops:
- `execute()` bodies byte-identical except comment removal (same checker creation, same `reversed(set_c)` for constraints, same `find_redundancies`/`find_redundant_testcases` calls, same `negation_map` arg, same try/finally cleanup, same `return self`).
- `_format_result_messages`, `get_redundant`, `get_non_redundant`, `get_result` (constraints) — byte-identical.
- Removed `_create_labeler`/`prepare_hsdag` stubs were never called: `execute()` is overridden and never delegates to the HSDAG template. Dropping them is pure dead-code removal.
- **Backend default preserved.** HEAD: `PySATRedundancyConstraints(PySATDiagnosis)` → `PySATDiagnosis.__init__` defaulted `backend=PYSAT_INCREMENTAL`. HEAD: `PySATRedundancyTestCases(PySATTestCase)` → `PySATTestCase.__init__` passed only profiler to super, inheriting `PySATAbstractExplanation`'s `backend=PYSAT_INCREMENTAL` default. New code: both default `backend=PYSAT_INCREMENTAL` directly. Verified at runtime: both ops construct with `backend=PYSAT_INCREMENTAL`, `use_incremental=True`. No silent backend change.
- **`get_result` for testcases** (no override now) resolves to `PySATOperationBase.get_result` → `return self.result_messages`. HEAD path resolved to the same method (then on `PySATAbstractExplanation`). Identical. Verified via `__qualname__`.
- Builder path unchanged: `PySATRedundancyConstraintsBuilder`/`PySATRedundancyTestCasesBuilder` call `Op(profiler)` positionally (backend defaulted), and `with_solver`/`with_incremental` set only `solver_name`/`use_incremental` — both inherited from `PySATOperationBase`. No HSDAG config touched.
- test_diagnosis `wipeoutr_fm_redundancy`/`pysat_redundancy_constraints`/`wipeoutr_t_redundancy` params: 18 redundancy/wipeoutr tests pass; full test_diagnosis 206 pass. No weakened asserts (params still True at :95-99; SEQ-1 builders/imports intact).

### (2) HSDAG-ops split behavior-preserving — CONFIRMED
`PySATAbstractExplanation(Operation)` → `PySATAbstractExplanation(PySATOperationBase(Operation))`. Moved into `PySATOperationBase`: `__init__` body (profiler/backend/result/solver_name/use_incremental/result_messages), `_create_checker` (verbatim incl. the `PYSAT_INCREMENTAL`+`not use_incremental` → `NONINCREMENTAL` effective-backend logic), `get_result`. `PySATAbstractExplanation.__init__` now `super().__init__(...)` then adds HSDAG-only state (checker/hsdag/max_*/depth_first_search). MRO verified for the 4 HSDAG ops: `PySATDiagnosis → PySATAbstractExplanation → PySATOperationBase → Operation → ABC → object`; `_create_checker` and `get_result` resolve from `PySATOperationBase`; abstract `_create_labeler`/`prepare_hsdag`/`set_result_messages` and concrete `execute()` template untouched. No method moved that the 4 ops depend on changed semantics.

## Registry Soundness — CONFIRMED
- register/get/create correct. Dup key → KeyError (prevents silent overwrite, verified). Miss → KeyError with sorted available-keys hint (verified).
- 6 registrations import + resolve to correct classes (verified at runtime).
- No circular import: registry imports op classes at module bottom (after helpers); op classes do not import registry; `explanation.api` imports registry last. `import explanation.api` clean.
- No inherit-then-stub residue anywhere: grep for `prepare_hsdag = pass` / `_create_labeler = pass` / `(PySATDiagnosis)` / `(PySATTestCase)` in explanation/operations → none.

## Findings by Severity

### Critical
None.

### High
None.

### Medium
None.

### Low
- **L1 — unused import `Type`.** registry.py:20 `from typing import Any, Callable, Dict, Type` — `Type` never referenced (only `Any`/`Callable`/`Dict` used). AST-confirmed. Fix: drop `Type` from the import. (ruff not installed in env, so not auto-caught.)
- **L2 — bare `list` return annotation.** registry.py:82 `registered_keys() -> list:` while the module uses `typing` aliases elsewhere; `api.py` re-exports it as `get_registered_operation_keys`. Cosmetic — prefer `List[str]` for consistency. Non-blocking.

### Advisory
- **A1 — registry is registered-but-unconsumed.** grep confirms no caller outside registry.py/api.py invokes `get_operation_class`/`create_operation`/`get_registered_operation_keys`. This is the intended plugin seam per spec (flamapy-plugin publish target) — acceptable, do NOT remove. Caveat: spec step 4 ("re-point string-based op dispatch in apps to registry lookup") rests on a faulty premise. The apps dispatch (`apps/run_cv.py:104/149/162/190` `algorithm == 'congen'/'interactive'`) selects conacq CV runner functions (`n_fold_cross_validation` vs `_interactive`), NOT explanation operations — there is zero key overlap with the op registry. Requester's independent assessment confirmed correct; leaving apps unchanged is right, and Success-Criteria item "String-based op dispatch replaced by registry lookup" is N/A (no such explanation-op dispatch exists in apps). Recommend annotating the spec so the unmet checkbox isn't read as incomplete work. The seam is genuine plugin infrastructure, not dead code, given the stated flamapy-plugin target.

## Behavioral Checklist
- Concurrency: n/a (no shared mutable state introduced; registry populated once at import).
- Error boundaries: KeyError on dup/miss is explicit and appropriate; try/finally cleanup in ops preserved.
- API contracts: backend/profiler defaults preserved; get_result shape (List[str]) preserved; nullability unchanged.
- Backwards compat: no exported symbol removed; api `__all__` only gains 3 names; redundancy op public methods unchanged.
- Input validation: n/a (internal refactor).
- Auth/authz: n/a.
- N+1 / query efficiency: n/a; solver-call count unchanged (consistency_check_count parity preserved by identical execute bodies).
- Data leaks: n/a.

## Positive Observations
- Clean LSP fix: redundancy ops no longer masquerade as diagnosis ops with no-op overrides.
- `PySATOperationBase` extraction is minimal and surgical — only genuinely-shared infra moved; HSDAG contract stays on `PySATAbstractExplanation`.
- Registry uses factory callables (not bare class refs) leaving room for default-arg-carrying entries; KeyError-on-dup is the right safety default for a plugin seam.
- Docstrings on both base classes clearly state when to use which.

## Recommended Actions
1. (Low) Drop unused `Type` import in registry.py:20.
2. (Low, optional) `registered_keys() -> List[str]` for annotation consistency.
3. (Advisory) Annotate spec: Success-Criteria "string-based op dispatch replaced" is N/A — apps dispatch is conacq-runner selection, not op selection. Don't read the unchecked box as incomplete.

## Metrics
- Tests: 568 passed / 0 failed / 0 warnings
- Redundancy subset: 18 passed; test_diagnosis: 206 passed; boundary_guard: 3 passed
- Type/lint: ruff unavailable in env; AST scan found 1 unused import (L1)

## Unresolved Questions
None. (Registry-unconsumed is intended per spec; spec step-4 premise flagged as advisory, not a blocker.)
