# C1 Solver Backend Port + Adapters — Implementation Report

## Phase Implementation Report

### Executed Phase
- Phase: 14 (C1 — SolverBackend port + PySAT/SAT4J adapters)
- Plan: /Users/manleviet/Development/GitHub/AcqMSS/plans/260621-1416-redesign-abc
- Status: completed

---

## Files Modified

| File | Action | Notes |
|------|--------|-------|
| `explanation/operations/algorithms/solver_backend.py` | **Created** | Port (Protocol) + config enum + factory |
| `explanation/operations/pysat_abstract_explanation.py` | Modified | Use `_BackendConfig`; `_create_checker` → `build_solver_backend`; remove unused `CheckerFactory` import |
| `explanation/operations/pysat_diagnosis.py` | Modified | Import `_BackendConfig`; type-annotate `backend` param |
| `explanation/operations/pysat_conflict.py` | Modified | Import `_BackendConfig`; type-annotate `backend` param |
| `explanation/operations/pysat_explanation_builder.py` | Modified | Import `_BackendConfig`; use `_BackendConfig.SAT4J` in factory methods |
| `explanation/api.py` | Modified | Export `SolverBackend` (Protocol) from `solver_backend.py` instead of enum from `pysat_abstract_explanation` |
| `tests/test_solver_backend_port.py` | **Created** | 8 new tests covering Protocol conformance, factory reachability, parity, and operation-level integration |

---

## Tasks Completed

- [x] Port interface defined (`SolverBackend` Protocol in `solver_backend.py`)
- [x] Config enum defined (`_BackendConfig` — internal, not exported via api)
- [x] Factory `build_solver_backend` maps config token → adapter (wraps existing checkers, no solver logic rewrite)
- [x] 3 adapters: `IncrementalPySATChecker`, `NonIncrementalPySATChecker`, `SAT4JChecker` — all satisfy Protocol structurally (verified by `isinstance(x, SolverBackend)`)
- [x] `_create_checker` replaced by `build_solver_backend` call — no duplicate branching
- [x] Dead `PYSAT_NONINCREMENTAL` branch resolved (see reconciliation section)
- [x] `explanation.api` exports `SolverBackend` as the real Protocol type
- [x] All 3 backends tested (including non-incremental, now reachable)
- [x] Parallel path (`ProcessExecutor`) untouched — still uses `IncrementalPySATChecker if use_incremental else NonIncrementalPySATChecker` in workers (safe: workers take primitives)

---

## Port Interface

**`SolverBackend` (Protocol, `@runtime_checkable`)** in `solver_backend.py`:
```python
def is_consistent(self, set_c: List) -> bool: ...
def get_model(self) -> Optional[List[int]]: ...
def cleanup(self) -> None: ...
```

Why these 3 methods:
- `is_consistent`: the core operation all algorithms call
- `get_model`: needed for `solve()` in `ConsistencyChecker` (model travels with result)
- `cleanup`: resource release (persistent solver handle, subprocess, etc.)

The existing `ConsistencyChecker` ABC and all 3 concrete classes already implement these — no wrapper classes needed. Net change: fewer branching sites, cleaner types.

---

## PYSAT_NONINCREMENTAL Reconciliation + Dead Branch Resolution

**Root cause of the dead branch:** `_create_checker` had:
```python
if self.backend is SolverBackend.PYSAT_NONINCREMENTAL:
    use_inc = False
else:  # PYSAT_INCREMENTAL — also respect explicit with_incremental() calls
    use_inc = self.use_incremental
```
No caller ever set `backend=SolverBackend.PYSAT_NONINCREMENTAL`; callers used `with_incremental(False)` which set `self.use_incremental = False` on the PYSAT_INCREMENTAL-backed op, reaching `NonIncrementalPySATChecker` via the else-branch. The enum member existed but was never reachable via the construction path.

**Resolution chosen:** Consolidate `use_incremental` flag into the backend choice inside `_create_checker`:
```python
effective = self.backend
if effective is _BackendConfig.PYSAT_INCREMENTAL and not self.use_incremental:
    effective = _BackendConfig.PYSAT_NONINCREMENTAL
return build_solver_backend(effective, ...)
```
- `with_incremental(False)` on a default op → reaches `PYSAT_NONINCREMENTAL` branch (same behavior, now explicit)
- `backend=_BackendConfig.PYSAT_NONINCREMENTAL` directly → also reaches it (previously dead; now alive and tested)
- No flag drift: one branch, one truth

**Why not full consolidation of `use_incremental` flag removal?** The `with_incremental()` builder method is part of the public builder API (`pysat_explanation_builder.py`) used by `test_diagnosis.py` heavily. Removing it would change the public builder interface — out of scope for C1. The flag is still set by the builder but is now immediately resolved in `_create_checker` rather than kept as a parallel switch.

---

## Checker/Executor/Operations Re-pointing

- `pysat_abstract_explanation._create_checker`: now calls `build_solver_backend` — single dispatch point, no solver-name branching
- `pysat_diagnosis.py`, `pysat_conflict.py`: type annotation changed from `SolverBackend` (old enum) to `_BackendConfig`
- `pysat_explanation_builder.py`: uses `_BackendConfig.SAT4J` instead of `SolverBackend.SAT4J`
- `pysat_redundancy_constraints.py`, `pysat_redundancy_testcases.py`, `pysat_testcase.py`, `pysat_testcase_quickxplain.py`: no changes needed — they call `self._create_checker(task)` which is updated

---

## API Export Update

**Before:** `from explanation.operations.pysat_abstract_explanation import SolverBackend` (Enum)
**After:** `from explanation.operations.algorithms.solver_backend import SolverBackend` (Protocol)

`explanation.api` now exports the real port type. Any future solver only needs to implement `is_consistent/get_model/cleanup` to be drop-in compatible.

---

## Backend Test Coverage

| Backend | Config Token | Tested via |
|---------|-------------|------------|
| PySAT incremental | `_BackendConfig.PYSAT_INCREMENTAL` | `test_solver_backend_port.py` + all `test_diagnosis.py` incremental params |
| PySAT non-incremental | `_BackendConfig.PYSAT_NONINCREMENTAL` | `test_solver_backend_port.py` (direct factory + operation token) + `test_diagnosis.py` non-incremental params |
| SAT4J | `_BackendConfig.SAT4J` | `test_solver_backend_port.py::test_sat4j_satisfies_protocol` (passed — jar present) + `test_diagnosis.py` sat4j params |

---

## Parallel Path Safety

`ProcessExecutor` in `executor.py` was **not modified**. It builds checkers in worker processes via:
```python
checker_cls = IncrementalPySATChecker if use_incremental else NonIncrementalPySATChecker
```
This path is independent of the new `build_solver_backend` factory and safe from pickling concerns — workers receive only primitives (`set_kb`, `assumptions`, `solver_name`, `use_incremental`) and instantiate their own checker locally. The parallel `test_consistency_check_count_parity` test still passes.

The incremental advantage is preserved: `IncrementalPySATChecker` still holds a persistent `Solver` instance across calls within a worker.

---

## Tests Status

- Type check: n/a (project uses pytest without mypy in CI)
- Unit tests (new): **8 passed** (`test_solver_backend_port.py`)
- Full suite: **517 passed** (509 original + 8 new), 0 warnings, 53s
- Boundary guard: GREEN
- Known flaky (`test_consistency_check_count_parity`): passed in this run; not modified

---

## Issues Encountered

None blocking. One cleanup: `CheckerFactory` import in `pysat_abstract_explanation.py` became unused after `_create_checker` refactor — removed.

## Deviations from Spec

- Spec suggested "checker/executor consume the port (no solver-name branching)" — `executor.py`'s worker initializer still branches on `use_incremental` (bool) rather than the port. This was intentional: the parallel path passes primitives to workers, not protocol objects. Changing it would require serialising the config token through `mp.Pool.initargs`, which is safe but not required by the spec's parallel-path safety constraint. Noted as follow-up.

---

**Status:** DONE
**Summary:** `SolverBackend` Protocol defined; `_BackendConfig` enum is the config token; `build_solver_backend` factory wires the 3 adapters; `_create_checker` dead branch eliminated; api exports real port; 8 new tests green; 517 total green.
**Concerns:** None blocking. `executor.py` worker init still uses raw bool (not `_BackendConfig`) — cosmetic follow-up only, parallel path is correct and tested.
