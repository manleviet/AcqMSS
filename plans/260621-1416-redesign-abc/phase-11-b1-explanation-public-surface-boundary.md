---
phase: 11
title: B1 explanation public surface + boundary
status: completed
priority: P1
effort: 2d
dependencies:
  - 2
  - 8
  - 9
  - 10
---

# Phase 11: B1 — explanation public surface + boundary

## Overview
The highest-leverage stage: make `explanation/` a package with one published surface so the future canonical-repo extraction is a clean cut. Today `conacq` imports underscore-private framework symbols (`_ASSUMPTION_PAIR_STRIDE` ×3) and reaches into `explanation.operations.algorithms.profiler`/`.checker` directly across 25 conacq files. Define the surface, rewrite all conacq imports to it, and add a guard test forbidding private cross-boundary imports.

## Safety-net FIRST (untested module)
`explanation/transformations/*` (4 files) is untested. Write characterization tests for the FM→SAT converters BEFORE touching imports.

## Requirements
- Functional: `explanation/__init__.py` (or `explanation/api.py`) exports exactly: `Task`/`DiagnosisTask`/`TestCaseTask`, `ModelProtocol`, `VariableCodec`, `CheckerFactory`, operation builders, `Profiler` Protocol (from B2), `SolverBackend` (placeholder until C1), and the A1 slicer promoted to a public helper. No underscore symbol crosses the boundary.
- Non-functional: all 25 conacq importers re-pointed to the surface; guard test green.

## Architecture
- Public surface module re-exporting the curated set; internal modules stay private.
- A1 slicer → public helper so `_ASSUMPTION_PAIR_STRIDE` stays internal to `explanation`.
- Guard test: AST/grep scan asserting no `conacq` module imports an `explanation` underscore symbol or deep-reaches a private path.

## Related Code Files (verified)
- Create: `explanation/api.py` (or expand `explanation/__init__.py`); `tests/test_boundary_guard.py`; `tests/test_transformations_*.py` (safety-net)
- Modify: all 25 `conacq` files importing `from explanation...`; specifically the 3 `_ASSUMPTION_PAIR_STRIDE` leaks (`conacq/oracle/fm_oracle_model.py:19`, `conacq/algorithms/acqmss/task_preparation.py:19`, `conacq/algorithms/quacq/task_preparation.py:19`); runners + oracle deep reach-ins (`fm_oracle.py:16-18`, `congen_runner.py:17-18`, `quacq_runner.py:12-14`); `apps/run_evaluation.py` reach-in (`runner.model.constraint_map`, `runner.feature_ids`)
- Consider: `conacq/algorithms/quacq/sat_utils.prune_rejecting` → move to shared framework utils on the surface

## Implementation Steps
1. Write safety-net transformations tests; run green.
2. Define the public surface; promote the A1 slicer helper.
3. Re-point all conacq imports (algorithms + runners + oracle) to the surface. (The 3 `_ASSUMPTION_PAIR_STRIDE` leaks were already removed in A1 via the plain-int stride arg — here the guard test ENFORCES they stay gone; re-point any residual.)
4. Add the boundary guard test.
5. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] One public surface module; curated exports only
- [ ] 0 `conacq`→`explanation` underscore/deep-private imports (guard test green)
- [ ] A1 slicer is public; `_ASSUMPTION_PAIR_STRIDE` internal-only
- [ ] Safety-net transformations tests exist
- [ ] Full suite green (≥351)

## Carried forward from B2 (260621)
- B2 added a `@runtime_checkable Profiler` Protocol in `explanation/operations/algorithms/profiler/protocol.py`, but the **public `Profiler` name still maps to the concrete class** (Protocol exported internally as `_ProfilerProtocol` for back-compat). B1 must settle the final public name: expose the Protocol on the `api` surface as the dependency type and decide whether the concrete class is renamed or kept. Resolve the transitional `_ProfilerProtocol` alias.

## Red-team adjustments (applied 260621)
- **Dead-code in transformations:** `explanation/transformations/dimacs_to_configuration.py` has ZERO importers (confirmed) — do NOT write a characterization test for it (that falsely makes it look load-bearing). Route its DELETION to C6. Focus the B1 safety-net on LIVE-but-untested converters (`fm_to_diag_pysat`, `dimacs_to_diag_pysat` — reached via `diagnosis_model_builder`; `testsuite_reader` already indirectly covered by test_diagnosis).
- **A2/B2 already surface-ready:** `abstract_model_builder` (A2, in `explanation/models/`) + the `profiler` package re-exports (B2) → B1 just folds them into `api.py`, no relocation.

## Risk Assessment
- 25-file import rewrite is broad → do it mechanically (one import pattern at a time), suite green after each cluster.
- Defining the surface too thin breaks conacq; too wide leaks internals → derive exports from actual conacq usage, not aspiration.
