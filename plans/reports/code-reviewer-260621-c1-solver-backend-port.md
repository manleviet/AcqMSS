# Code Review — C1: SolverBackend Port + Adapters + Factory

**Date:** 2026-06-21
**Branch:** feat/redesign-abc
**Scope:** Uncommitted working-tree only. New: `solver_backend.py`, `test_solver_backend_port.py`. Modified: `api.py`, `pysat_abstract_explanation.py`, `pysat_conflict.py`, `pysat_diagnosis.py`, `pysat_explanation_builder.py`.
**Verdict: PASS** (1 LOW informational note, no blockers)

---

## Verdicts on critical claims

### (1) Incremental-advantage preserved — VERIFIED ✅
- `build_solver_backend(PYSAT_INCREMENTAL, ...)` → `IncrementalPySATChecker(set_kb, assumptions, solver_name, profiler)` (solver_backend.py:101-102). Identical args to the old `CheckerFactory.create_from_task(use_incremental=True)` (checker.py:268-271).
- `IncrementalPySATChecker.__init__` builds ONE persistent `self.solver = Solver(...)` (checker.py:126); `is_consistent` reuses it via `self.solver.solve(assumptions=...)` (checker.py:133) — NOT fresh-per-call. The ~50x warm-solver advantage is intact.
- `checker.py` is **untouched** in the working tree (`git diff --stat` empty) — the 3 concrete checkers are byte-identical to pre-C1. Behavior preservation is structural, not just claimed.
- SAT4J path: `build_solver_backend(SAT4J, ...)` → `SAT4JChecker(set_kb, assumptions, jar_path, profiler)` (solver_backend.py:105-111), same wiring as old `create_sat4jchecker`. Unchanged.
- `with_incremental(False)`: resolves `PYSAT_INCREMENTAL → PYSAT_NONINCREMENTAL` (pysat_abstract_explanation.py:196-199) → `NonIncrementalPySATChecker`. The old else-branch produced `NonIncrementalPySATChecker` via `create_from_task(use_incremental=False)` (checker.py:272-275) — same class, same constructor args. Identical behavior.

### (2) Dead branch resolved AND tested — VERIFIED ✅
- Pre-C1 `PYSAT_NONINCREMENTAL` was unreachable (enum branch had no caller path). Now reachable two ways:
  1. Via `with_incremental(False)` resolution (pysat_abstract_explanation.py:196-199).
  2. Via direct op construction `PySATDiagnosis(backend=_BackendConfig.PYSAT_NONINCREMENTAL)`.
- Tests exercise it as a **working/correct** solver, not merely constructed:
  - `test_nonincremental_returns_consistent_result` (test:112-125): asserts `is_consistent(set_b) is True` and `is_consistent(set_b + set_c) is False` — real SAT answers.
  - `test_parity_on_consistent_and_inconsistent_probes` (test:135-153): incr == non-incr on both probes.
  - `test_operation_executes_without_error_nonincremental` (test:176-182): full end-to-end `op.execute(task)` with the non-incremental token, asserts 2 result messages.

---

## Findings by severity

### Critical — none

### High — none

### Medium — none

### Low (informational, non-blocking)

**L1 — `SolverBackend` Protocol is narrower than the runtime consumer surface (intentional, but worth a doc note).**
`solver_backend.py:23-45` — File: `explanation/operations/algorithms/solver_backend.py:35-45`
The Protocol declares only `is_consistent / get_model / cleanup`. But the object returned by `_create_checker` is consumed as a full `ConsistencyChecker` / `ConsistencyExecutor`:
- `kbdiag_labeler.py:46` calls `checker.is_consistent_test_cases(...)`
- `fastdiag_labeler.py:41` calls `checker.is_consistent(...)`
- `ConsistencyChecker.solve` / `submit` are part of the executor contract (checker.py:91-104).

So `SolverBackend` is the *minimal selection/conformance port* (the 3 ops the factory guarantees + boundary type), while the richer `ConsistencyExecutor` Protocol (checker.py:24-45) is the *consumer* contract. This is a defensible two-protocol split (port = "what every backend must expose"; executor = "what algorithms call"), and `_create_checker` is typed `-> ConsistencyChecker` (the full surface), so callers are NOT restricted to the thin port — no functional gap.

Assessment: **NOT too thin in practice** (callers get the full `ConsistencyChecker`), and **NOT too wide** (3 methods, all consumed). The only risk is conceptual: a reader may assume `SolverBackend` is the complete backend contract. The docstring at solver_backend.py:24-32 says "the operations a consistency-checking backend must expose" / "Checker, executor, and operations depend ONLY on this type" — that second clause is slightly overstated, since labelers depend on `is_consistent_test_cases` which is NOT on the port. Suggest softening to: "the minimal port the factory guarantees; algorithms consume the richer ConsistencyExecutor surface." No code change required to ship.

---

## Checklist verification

| Check | Result |
|---|---|
| **Behavior-preserving (CRITICAL)** | ✅ checker.py untouched; incremental reuses persistent solver; SAT4J & non-incr wiring identical |
| **Dead branch resolved + tested** | ✅ reachable 2 ways; 3 tests prove correctness (not just construction) |
| **Parallel path untouched** | ✅ `executor.py` git diff EMPTY. `_init_worker` still branches `IncrementalPySATChecker if use_incremental else NonIncrementalPySATChecker` (executor.py:68); workers still build own checker from KB primitives (executor.py:58-71). No regression. |
| **Port real, not over-built** | ✅ 3-method Protocol, all consumed; 3 concrete checkers satisfy it structurally (inherit from `ConsistencyChecker` ABC which defines all 3). `runtime_checkable isinstance` tests pass for all 3. See L1 for the port-vs-executor scope nuance. |
| **api export correct** | ✅ `api.py:76,123` exports the real `SolverBackend` Protocol from `solver_backend.py` (was placeholder enum). `_BackendConfig` and `build_solver_backend` correctly NOT in `__all__` (selection internals stay private; only the Protocol type crosses). |
| **Boundary guard green** | ✅ `test_boundary_guard.py` passes; `_BackendConfig` imports are all intra-`explanation` (no conacq/apps deep-reach). |
| **No weakened assertions** | ✅ 11 asserts: real `isinstance`, `is True/False`, equality parity, `len == 2` end-to-end. No tautologies, no `assert True`. |
| **No plan-stage labels in code** | ✅ grep for C1/phase/stage/A3/red-team/F##/Y## in new files = none. Comments explain *why* (circular-import avoidance, with_incremental honoring), not plan origin. |
| **Framework-scope** | ✅ all changes within `explanation/operations`; no leakage to conacq. |
| **Full suite** | ✅ 517 passed, 0 warnings, 52s. Flaky `test_consistency_check_count_parity` passed. |

---

## Positive observations
- `checker.py` left untouched — strongest possible evidence of behavior preservation; the factory is pure re-wiring.
- Circular-import comment (solver_backend.py:93-94) is **accurate** — verified checker.py has zero `solver_backend` imports; dependency is genuinely one-directional.
- `ValueError` fallthrough for unrecognised config (solver_backend.py:112) — fail-fast, no silent wrong-backend.
- Tests use `try/finally: backend.cleanup()` consistently — no leaked persistent PySAT solver handles.
- SAT4J protocol test is jar-guarded (`skipif`) AND the jar is present here, so it actually ran (not silently skipped).
- `with_incremental(False)` resolution keeps the public flag API working without callers knowing the `PYSAT_NONINCREMENTAL` token exists — good encapsulation (KISS).

---

## Metrics
- Type coverage: full type hints on new public surface (Protocol methods, factory signature).
- New test file: 8 tests, all passing.
- Linting: no syntax errors; compiles clean (suite imports succeed).
- Suite: 517 passed / 0 failed / 0 warnings.

---

## Unresolved questions
- None blocking. L1 (docstring scope wording) is a polish item the author may apply at discretion or defer — it does not affect correctness, exports, or behavior.
