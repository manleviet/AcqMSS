# A3 Backend Strategy Ops — Implementation Report

## Phase Executed
- Phase: 4 — A3 solver-backend strategy ops
- Plan: `/Users/manleviet/Development/GitHub/AcqMSS/plans/260621-1416-redesign-abc`
- Status: completed

## Strategy Design

`SolverBackend` enum added to `explanation/operations/pysat_abstract_explanation.py`:

```
PYSAT_INCREMENTAL   — persistent PySAT solver (was default, still is)
PYSAT_NONINCREMENTAL — fresh PySAT solver per check
SAT4J               — external Java solver via subprocess
```

The enum lives on `PySATAbstractExplanation.__init__(backend=SolverBackend.PYSAT_INCREMENTAL)`.
`_create_checker()` in the base class dispatches on it:
- SAT4J → `CheckerFactory.create_sat4jchecker(...)`
- PYSAT_NONINCREMENTAL → `create_from_task(..., use_incremental=False)`
- PYSAT_INCREMENTAL (default) → `create_from_task(..., use_incremental=self.use_incremental)` (preserves `with_incremental()` builder calls)

## Clone Deltas Absorbed

Both SAT4J clones vs PySAT siblings differed in exactly one place: `_create_checker()` override routing to `CheckerFactory.create_sat4jchecker()` instead of `create_from_task()`. The extra `_create_checker` in both clone files is now replaced by the base-class dispatch.

- `pysat_diagnosis_sat4j.py`: `_create_labeler` (FastDiag), `prepare_hsdag`, `set_result_messages` — all identical to `pysat_diagnosis.py`. Only `_create_checker` differed.
- `pysat_conflict_sat4j.py`: same pattern with `_create_labeler` (QuickXPlain). Only `_create_checker` differed.

No behavior unreproducible in the unified design — nothing to STOP for.

## Files Modified

| File | Change |
|------|--------|
| `explanation/operations/pysat_abstract_explanation.py` | Added `SolverBackend` enum; added `backend` param to `__init__`; updated `_create_checker` to dispatch on backend |
| `explanation/operations/pysat_diagnosis.py` | Added `SolverBackend` import; added `backend` param to `__init__`, forwarded to super |
| `explanation/operations/pysat_conflict.py` | Same as diagnosis |
| `explanation/operations/pysat_explanation_builder.py` | Removed imports of clone classes; imported `SolverBackend`; repointed `for_diagnosis_sat4j()` / `for_conflict_sat4j()` to `PySATDiagnosis(backend=SolverBackend.SAT4J)` / `PySATConflict(backend=SolverBackend.SAT4J)` |

## Files Deleted

- `explanation/operations/pysat_diagnosis_sat4j.py` — deleted
- `explanation/operations/pysat_conflict_sat4j.py` — deleted

Dangling-ref check: `grep -rn "PySATDiagnosisSAT4J|PySATConflictSAT4J|pysat_diagnosis_sat4j|pysat_conflict_sat4j"` → 0 matches.

## test_diagnosis.py SAT4J Path

`test_diagnosis.py` already exercised the SAT4J path through `PySATDiagnosisBuilder.for_diagnosis_sat4j()` / `for_conflict_sat4j()` — no direct imports of the deleted clone classes existed. No test file changes were required. The builder methods now construct `PySATDiagnosis(backend=SolverBackend.SAT4J)` / `PySATConflict(backend=SolverBackend.SAT4J)`.

## Tests Status

```
uv run --no-sync pytest tests/ -q
376 passed, 1 warning in 63.59s
```

SAT4J-only path: `pytest tests/test_diagnosis.py -k "sat4j"` → 70 passed (all exercised, none skipped).

## Deviations from Spec

- `use_incremental` field is preserved and still consulted for the `PYSAT_INCREMENTAL` backend (to keep `with_incremental()` working). The spec said "backend selection, not a one-off if/else" — the dispatch is a proper enum branch, compatible with C1 promotion.
- `PYSAT_NONINCREMENTAL` is added as an explicit backend value (separate from `use_incremental=False`) for clean C1 forwarding, but the `with_incremental(False)` path still works through the base-class `use_incremental` field for backwards compat.

---

**Status:** DONE
**Summary:** Two SAT4J clone files deleted; their sole behavioral difference (`_create_checker` routing) absorbed into a `SolverBackend` enum dispatch on the base class. Builder repointed. 376 tests pass; 70 SAT4J-path tests confirmed exercised.
**Concerns:** None.
