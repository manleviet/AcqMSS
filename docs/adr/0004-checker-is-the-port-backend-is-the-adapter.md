# ADR-0004: `checker` is the port, `solver_backend` is the adapter

**Status:** Accepted
**Date:** 2026-07-11
**Deciders:** Viet-Man Le

## Context

Consistency checking sits between two worlds: the algorithms (FastDiag, QuickXPlain, HSDAG, KBDiag) that ask *"is this set consistent?"*, and the solvers (PySAT incremental, PySAT non-incremental, an external SAT4J process) that answer.

The original code named these backwards, and the names then propagated:

- `checker.py` contained the three concrete classes — and `import subprocess`, `from pysat.solvers import Solver`, a `jar_path`. **That file is the infrastructure that talks to solvers.** It is an adapter, named "checker".
- A first pass at introducing a role-protocol named it `SolverBackend` — and gave it to the *algorithms* to depend on. **That is the port**, named "backend".

The evidence that settled it, measured on the real code:

| Observation | What it means |
|---|---|
| `checker.py` imports `pysat`, `subprocess`, holds a `jar_path` | it is solver-facing infrastructure → **adapter** |
| `ConsistencyChecker` appears **73 times across 24 files**, but only **3 of those subclass it** | the other ~70 are *annotations* in algorithms and application code → the name was already doing the job of a **port** |

So the domain word (`checker`) was attached to the technology side, and the technology word (`backend`) to the domain side. Exactly inverted.

There was a second symptom, which turned out to be a consequence: an **import cycle**. The factory in `checker.py` needed the port module, and the port module's builder needed the concrete checkers back from `checker.py`. It had been "fixed" with a lazy import inside the function body.

## Decision

**Name each module after the side of the dependency it serves.**

| Module | Role | Contents |
|---|---|---|
| `explanation/operations/algorithms/checker.py` | **PORT** — what algorithms depend on. Imports *neither* `pysat` nor `subprocess`, and must stay that way | `ConsistencyChecker` (Protocol: `is_consistent` / `get_model` / `cleanup`) · `TestCaseChecker(ConsistencyChecker)` (adds `is_consistent_test_cases`) |
| `explanation/operations/algorithms/solver_backend.py` | **ADAPTER** — what talks to solvers | `SolverCheckerBase` (shared impl base) · `IncrementalPySATChecker` · `NonIncrementalPySATChecker` · `SAT4JChecker` · `SolverBackend` (enum: which solver) · `build_checker(task, backend, …)` — the **single public door**; the primitive constructor is private and is the **single place a concrete class is chosen** |

### Naming inside the adapter module

The three adapters **are** consistency checkers — so they are named `*Checker`, after the role they implement (`Logger` / `FileLogger`, not `Logger` / `FileBackend`). `build_checker(...) -> ConsistencyChecker` returning an `IncrementalPySATChecker` reads straight; returning an `IncrementalPySATBackend` would make the reader translate.

The word **"backend" survives exactly where it carries meaning: naming *which solver technology*** — as the enum `SolverBackend` (`PYSAT_INCREMENTAL`, `PYSAT_NON_INCREMENTAL`, `SAT4J`) and in the module name. It is **not** used as a synonym for "checker".

```python
build_checker(task, SolverBackend.SAT4J)   # "build a checker, using the SAT4J backend"
```

`CheckerConfig` was rejected for that enum: it reads as *configuration of a checker* (solver name? timeout?), which is not what it selects.

The shared implementation base is `SolverCheckerBase`, **not** `AbstractConsistencyChecker`. The latter would sit next to the Protocol `ConsistencyChecker` — two near-identical names for two different roles (contract vs. implementation base), which is exactly the kind of collision this ADR exists to prevent. `Base` (not `Abstract`) signals impl-base rather than contract. It is deliberately **not** exported through `explanation.api`.

Supporting decisions:
- **Narrow role protocols.** One fat interface was rejected. Algorithms use checkers in three distinguishable roles: consistency checking (`ConsistencyChecker`), test-case checking (`TestCaseChecker`), and *copyable/picklable* for the parallel FastDiagP. Only the first two are ports here; the third belongs to the executor concern and is deliberately **not** in either protocol.
- **`CheckerFactory` was dissolved** into module-level functions. A class holding only `@staticmethod`s is a namespace; Python modules already are namespaces.
- **The public API exports no concrete adapter class.** `explanation.api` exposes `ConsistencyChecker`, `TestCaseChecker`, `SolverBackend`, `build_checker` — and nothing else from this area. Application code never names a solver class.
- **Checkers are always built from a `Task`.** The one caller that needed a checker for an inline sub-problem (`GenerateNE`) constructs a `DiagnosisTask` for it rather than reaching for a primitive constructor.

### Why the two files are not merged

A recurring suggestion is to fold the port into the adapter module — "it is one concept, why two files?". It cannot be done without giving up what the split buys:

- Move `build_checker` into `checker.py` and that file must import the three adapters; the adapters import `ConsistencyChecker` for typing → **the cycle comes straight back**, and with it the lazy-import workaround.
- Merge everything into one file and the port is no longer clean: the **~24 algorithm/labeler/operation files that import `ConsistencyChecker` purely to annotate a parameter** would start pulling in `pysat`, `subprocess`, and a Java process spawner.

The asymmetry is the whole point, and it is textbook Dependency Inversion:

```
~24 algorithm files ──import type──►  checker.py  (no pysat, no subprocess)
                                          ▲
 ~9 assembly points ──import build──► solver_backend.py  (pysat + subprocess + Java)
                                          │ imports the port for typing
                                          ▼ constructs
                                    3 concrete checkers
```

Policy (algorithms) and detail (PySAT/SAT4J) both point at the port; neither points at the other. Many depend on the abstraction; few construct the concrete thing, at the edges. *(Compare logging: thousands of `logger.info(...)` call sites, one `basicConfig(handlers=...)`.)*

**"The public API is split across two files" is a non-issue** — `explanation.api` is the single door; consumers never see the split.

## Options considered

### Option A: Keep the names, keep both abstractions

| Dimension | Assessment |
|---|---|
| Effort | Zero |
| Cost | A reader sees `SolverBackend` and reasonably concludes "this is the thing that talks to the solver" — and is wrong. Every future contributor pays this tax |
| Cycle | Stays; the lazy-import workaround stays with it |

### Option B: Fix the *module* names and the dependency direction; keep the class names in the `*Checker` family (chosen)

| Dimension | Assessment |
|---|---|
| Effort | **Far smaller than it looks** — the ~70 annotation sites keep the literal text `ConsistencyChecker`; only *what it is* (ABC → Protocol) and *where it lives* changes. Most files were not edited at all |
| Cycle | **Disappears.** `solver_backend` imports `checker` at top level; `checker` imports nothing. Acyclic by construction; the lazy import was deleted |
| Cost | One mechanical rename of the impl base + the factory call sites |

### Option C: Rename the adapters to `*Backend` as well (considered, rejected)

An intermediate version of this work renamed the three concrete classes to `IncrementalPySATBackend` / `NonIncrementalPySATBackend` / `SAT4JBackend`, and the enum to `BackendConfig`. It was rejected before landing: it uses "backend" as a **synonym for "checker"**, which is the very conflation this ADR is about. The classes implement `ConsistencyChecker`; they should be named for that role. "Backend" is reserved for what actually distinguishes them — the solver — and lives in the enum `SolverBackend` and the module name.

## Trade-off analysis

The naming was not merely imprecise, it was **inverted** — which is worse, because inverted names actively mislead. And it was not cosmetic: it produced a real import cycle that had been papered over.

That is the generalisable lesson worth recording:

> **An import cycle between an abstraction and its implementation is a *smell of inverted naming/placement*, not a problem to be patched.** When the port and the adapter are in the right places, dependencies flow one way — adapter → port — and can never form a loop. A lazy import introduced to break such a cycle is a signal to stop and re-examine the names, not to reach for a scalpel.

## Consequences

**Easier**
- An algorithm author depends on `ConsistencyChecker` and cannot accidentally acquire a dependency on PySAT, SAT4J, or pickling.
- Adding a solver (Z3, MiniSat, …) means: one new `*Checker` class (subclassing `SolverCheckerBase`), one new `SolverBackend` enum member. There is exactly **one** place in the codebase where a concrete checker class is selected (`_build_checker`).
- No cycle, no lazy imports.

**Harder**
- Two files that sound similar (`checker.py`, `solver_backend.py`) must not be confused. The port file carries a docstring stating its own invariant — *"this module imports neither `pysat` nor `subprocess` and must stay that way"* — so the rule travels with the code.

**To revisit**
- The HSDAG labeler tree still types against the broad checker rather than the narrow role it uses (`kbdiag_labeler` needs `TestCaseChecker`; the others do not). Retyping that tree is scheduled with the labeler work.
- The copyable/picklable role used by FastDiagP has no protocol yet. It belongs to the executor design, not here.
