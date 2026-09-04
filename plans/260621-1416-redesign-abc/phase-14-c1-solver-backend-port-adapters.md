---
phase: 14
title: C1 solver-backend port + adapters
status: completed
priority: P2
effort: 2d
dependencies:
  - 4
  - 11
---

# Phase 14: C1 — SolverBackend port + PySAT/SAT4J adapters

## Overview
Formalise PySAT vs SAT4J as adapters behind one `SolverBackend` port. The executor, checker, and operations all consume the port — removing the last backend-specific branches and making a future solver a drop-in. A3 unified the op layer; C1 unifies the layer below it.

**Carried forward from A3 (260621):** A3 already introduced a `SolverBackend` **enum** (PYSAT_INCREMENTAL / PYSAT_NONINCREMENTAL / SAT4J) in `explanation/operations/pysat_abstract_explanation.py`, with `_create_checker` dispatching on it. C1 must (a) reconcile the name — promote/replace this enum into the real port/Protocol (avoid a clash), and (b) resolve `PYSAT_NONINCREMENTAL`, which is currently a **dead branch** (non-incremental is reached via `with_incremental(False)` on the default backend, not via the enum) — either wire a caller + test for it, or consolidate `use_incremental` INTO the backend so the flag disappears. Replaces B1's `SolverBackend` placeholder with the real type.

## Requirements
- Functional: a `SolverBackend` Protocol/port; PySAT-incremental, PySAT-nonincremental, SAT4J adapters; checker/executor/operations depend on the port, not concrete backends.
- Non-functional: framework-isolated; identical results per backend (~50x incremental advantage preserved); replaces B1's `SolverBackend` placeholder with the real type.

## Architecture
- `explanation/operations/.../solver_backend.py`: `SolverBackend` port + 3 adapters wrapping current PySAT/SAT4J wiring.
- A3's backend-strategy seam gets promoted to consume the port (no second abstraction).
- Checker (`checker.py`) + executor (`executor.py`) take a `SolverBackend` instead of branching on solver name.

## Related Code Files (verified)
- Create: `explanation/operations/.../solver_backend.py` (port + adapters); update B1 surface export
- Modify: `explanation/operations/pysat_diagnosis.py` / `pysat_conflict.py` (consume port — from A3 strategy), `explanation/operations/algorithms/checker.py`, `explanation/operations/algorithms/executor.py`
- Modify: callers passing `solver_name`/`use_incremental` (e.g. `CheckerFactory.create_from_task`) to construct the right adapter

## Implementation Steps
1. Define the `SolverBackend` port from current solver call-sites.
2. Implement 3 adapters; route A3's strategy through the port.
3. Re-point checker/executor/ops to the port; construct adapters from existing config (solver_name/use_incremental).
4. Replace the B1 `SolverBackend` placeholder with the real export.
5. `PYTHONPATH=. pytest tests/ -v` → green (each backend exercised).

## Success Criteria
- [ ] One `SolverBackend` port + PySAT-incr/PySAT-nonincr/SAT4J adapters
- [ ] checker/executor/operations consume the port (no solver-name branching)
- [ ] B1 surface exports the real `SolverBackend`
- [ ] Each backend covered by a test; incremental perf path intact
- [ ] Full suite green (≥351)

## Risk Assessment
- Risk of a second abstraction layer atop A3 → C1 must absorb the A3 strategy, not stack on it (net less code).
- Incremental-vs-nonincremental semantics subtle → adapter tests must assert both correctness and that the incremental path is actually used.
