# P0 — Defect cleanup (conacq) — implementation plan

**Date:** 2026-06-18 · **Owner:** Claude Code (AcqMSS) · **Status:** ready to implement
**Scope:** `conacq/algorithms/quacq/quacq_model.py`, `conacq/algorithms/quacq/sat_utils.py`
**Origin:** Cowork design review `design-review-explanation-conacq-2026-06-18.md` (§P5). These 3 defects are **independent** of the larger model→Task refactor (Phase R) and safe to merge on their own. All verified at path:line below.

## Guardrails
- Do NOT start the big refactor (model→Task / VariableCodec / ModelProtocol). This plan is ONLY the 3 isolated fixes.
- After all 3 fixes, the full suite must stay green: `PYTHONPATH=. pytest tests/ -v`.
- Keep changes minimal; no API/behavior change beyond the fix.

## Task 1 — Fix mutable-default misuse in QuAcqModel (latent bug)
**File:** `conacq/algorithms/quacq/quacq_model.py`
**Problem (verified):** `QuAcqModel` is a plain class (not `@dataclass`), but lines 54–55 use `field(default_factory=dict)`:
```python
self.pos_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
self.neg_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
```
`dataclasses.field(...)` outside a dataclass returns a `Field` object, NOT a dict. It's currently masked only because `QuAcqModelBuilder.build()` overwrites both attributes (quacq_model_builder.py:74–75). Any code that constructs `QuAcqModel()` and touches these before the builder runs gets a `Field`, not `{}`.

**Fix:**
- Lines 54–55 → `= {}` (plain empty dict).
- Line 10 `from dataclasses import field` is then unused (only uses were lines 54–55) → remove the import.

**Acceptance:** `QuAcqModel()` has `pos_assignment_to_assumption == {}` and `neg_assignment_to_assumption == {}`, both real dicts (`isinstance(..., dict)`).

## Task 2 — `prune_rejecting` ignores the passed `profiler`
**File:** `conacq/algorithms/quacq/sat_utils.py`
**Problem (verified):** signature takes `profiler` (line 34) but line 43 unconditionally overwrites it:
```python
def prune_rejecting(checker, model, remaining_bias, assignment, root_assumption, profiler) -> list:
    profiler = get_global_profiler()   # <-- discards the passed profiler
```
Callers DO pass a profiler (`quacq.py:187`, `findscope.py:65`), so per-call profiler metrics (`prune_is_consistent_calls`) are silently lost to the global one.

**Fix:**
- Default the param: `profiler=None`.
- Replace line 43 with: `if profiler is None: profiler = get_global_profiler()`.

**Acceptance:** when a caller passes a profiler, the `prune_is_consistent_calls` increments land on THAT profiler; when none is passed, falls back to global. Existing tests still pass.

## Task 3 — Remove dead standalone `get_constraint_vars`
**File:** `conacq/algorithms/quacq/sat_utils.py`
**Problem (verified):** `get_constraint_vars(...)` (sat_utils.py:13) is never imported/used — only `prune_rejecting` is imported from sat_utils (`quacq.py:20`, `findscope.py:16`). All real callers use the **method** `QuAcqModel.get_constraint_vars` (quacq_model.py:131; e.g. discriminating_generator.py:51, quacq_model.py:197). The standalone is duplicate dead code.

**Fix:**
- Delete the standalone `get_constraint_vars` function from sat_utils.py.
- Clean up now-unused imports in sat_utils.py (`from typing import Dict, List, Set` — verify each is unused after removal; `prune_rejecting` uses only builtins `set/dict/list/int`, so all three likely become unused → remove them).

**Acceptance:** `grep -rn get_constraint_vars conacq` shows only the method on `QuAcqModel` and its call sites; suite green; no unused-import lint regressions.

## Verification (after all 3)
```
PYTHONPATH=. pytest tests/ -v           # full suite green
PYTHONPATH=. pytest tests/test_quacq.py tests/test_oracle_model.py -v   # most relevant
```

## Out of scope (do NOT touch here)
- model→Task / `Task` ABC / `VariableCodec` / `ModelProtocol` / `prepare_task` / `execute(task)` — separate Phase R plan.
- Commented-out blocks (`QuAcqModel.get_cf` ~:88–94, assignment-clause lines ~:99/114; `ConGenModel.resolve_result` ~:192–204) — leave for the Phase R refactor unless trivially removable; do not change behavior.

## Unresolved questions
- `@count_calls('prune_calls')` decorator on `prune_rejecting` may still use the global profiler independently of the param fix — acceptable for P0 (out of scope to change decorator semantics).
