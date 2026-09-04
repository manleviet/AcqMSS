# Code Review — A3 Solver Backend Strategy (fold SAT4J clones into `SolverBackend` enum)

Date: 2026-06-21 | Branch: feat/redesign-abc | Scope: uncommitted working tree only

## Verdict: PASS

Behavior-preserving, no dangling refs, assertions intact, 70 SAT4J + 376 full tests green. One non-blocking YAGNI observation (dead enum member). Status: DONE_WITH_CONCERNS (observational only).

## Scope reviewed
6 entries, all under `explanation/operations/` (check 6 PASS):
- M `pysat_abstract_explanation.py` (+enum, +backend param, dispatch in `_create_checker`)
- M `pysat_diagnosis.py`, `pysat_conflict.py` (forward `backend`)
- M `pysat_explanation_builder.py` (builders construct `backend=SAT4J`; drop SAT4J-clone imports)
- D `pysat_diagnosis_sat4j.py`, `pysat_conflict_sat4j.py`

## CRITICAL — behavior preservation (PASS)

### (a) SAT4J path — identical
Diffed deleted clones (`git show HEAD:...`) vs current `PySATDiagnosis`/`PySATConflict`:
- `_create_checker` SAT4J branch (`pysat_abstract_explanation.py:204-206`) calls
  `CheckerFactory.create_sat4jchecker(self.profiler, set_kb=task.set_kb, assumptions=task.assumptions)`
  — byte-for-byte the same args the deleted `_create_checker` overrides used.
- `_create_labeler` — identical (FastDiag/QuickXPlain + Parameters(set_c, set_b)).
- `prepare_hsdag` — identical.
- `set_result_messages` — identical ordering: diag `[diag_mess, cs_mess]`, conflict `[cs_mess, diag_mess]`.
The deleted clones' ONLY real delta from their non-SAT4J siblings was the `_create_checker` override; that delta is now reproduced exactly by the enum dispatch. No behavioral drift.

### (b) Default PySAT path — unchanged
HEAD base `_create_checker` called unconditionally:
`create_from_task(task, solver_name=self.solver_name, use_incremental=self.use_incremental, profiler_instance=self.profiler)`.
New base for `PYSAT_INCREMENTAL` (default) sets `use_inc = self.use_incremental` → identical call.
`with_incremental(False)` interaction verified at runtime: backend stays `PYSAT_INCREMENTAL`, `use_incremental=False`, routes through `else` branch → `use_inc=False`. Reproduces prior non-incremental behavior exactly. All 4 other base subclasses (`PySATTestCase`, `PySATTestCaseQuickXPlain`, `PySATRedundancyTestCases`, `PySATRedundancyConstraints`) call `super().__init__(profiler_instance)`; `backend` defaults to `PYSAT_INCREMENTAL` — no break, no behavior change.

### (c) `_create_labeler`/`prepare_hsdag`/`set_result_messages` — unchanged
Confirmed by file read; no edits to these in the diff.

## Check 2 — dangling references (PASS)
`grep` for `PySATDiagnosisSAT4J|PySATConflictSAT4J|pysat_diagnosis_sat4j|pysat_conflict_sat4j` across explanation/, conacq/, apps/, tests/, docs/ → zero (excluding stale `.pyc`). Builder imports of the deleted classes removed. `explanation/operations/__init__.py` is empty (0B) — no exports to update.

## Check 3 — assertions / tests (PASS)
- `test_diagnosis.py` routes SAT4J via `PySATDiagnosisBuilder.for_diagnosis_sat4j()` / `for_conflict_sat4j()` (lines ~451-452, 473), which now build `PySATDiagnosis/Conflict(backend=SAT4J)` — the operation-level SAT4J path IS exercised, not just the direct-checker helper.
- Assertions intact and specific (exact diagnosis/conflict strings, e.g. `:241`, `:459`). No weakening.
- `uv run --no-sync pytest tests/test_diagnosis.py -k sat4j -q` → 70 passed, 136 deselected (deselection is the `-k` filter, not a wrongful skip).
- `uv run --no-sync pytest tests/ -q` → 376 passed, 1 warning (known `TestSuiteReader` collection warning). Flaky `test_consistency_check_count_parity` passed.

## Check 4 — seam quality (PASS, clean)
Enum dispatch (`is` identity comparison on `SolverBackend`) is idiomatic and readable; no isinstance hacks, no stringly-typed flags. Replacing two subclass-per-solver clones with one parameterized op is a net DRY win and a reasonable precursor to a future backend port. Docstrings explain intent without over-promising. Not over-built.

## Check 5 — no plan-stage labels (PASS)
grep for `A3|C1|F\d+|Y\d+|CU\d+|phase-0|red.?team|audit A` in changed files → none. Comments describe intent only.

## Findings by severity

### Low / Informational (non-blocking)
- **L1 — `PYSAT_NONINCREMENTAL` is a dead enum member.** `pysat_abstract_explanation.py:22,207-208`. Defined and dispatched, but no caller anywhere constructs `backend=SolverBackend.PYSAT_NONINCREMENTAL` (grep confirms only `SAT4J` and `PYSAT_INCREMENTAL` are ever passed). Non-incremental solving is reached exclusively via `with_incremental(False)` on the default backend, which the `else`/`use_incremental` branch already handles. The member is harmless and arguably documents intent, but per YAGNI it is currently unexercised code (the `if PYSAT_NONINCREMENTAL` branch has no test coverage). Options: (a) keep as documented future seam — acceptable; (b) drop it until a caller needs it. No action required to ship; flag for awareness. Recommend NOT removing without confirming the spec/red-team intended it as the public non-incremental selector.
- **L2 — Docstring nuance (cosmetic).** `pysat_abstract_explanation.py:194-196`: "PYSAT_NONINCREMENTAL ... (overrides `use_incremental`)" vs "PYSAT_INCREMENTAL ... `use_incremental` is also consulted". Accurate but slightly asymmetric phrasing; since non-incremental is in practice selected via `use_incremental=False` on the default backend (not via the enum), a reader could expect the enum to be the primary lever. Tighten if convenient. Non-blocking.

## Positive observations
- Exact behavior preservation verified by source diff against deleted files AND by runtime wiring check (defaults, SAT4J builders, `with_incremental(False)`).
- Net −105 LOC (two clone files removed) with no contract change to builders/tests.
- `_create_checker` is the single seam touched; labeler/hsdag/messages untouched — minimal blast radius.
- Identity (`is`) comparison on enum members is correct and clear.

## Unresolved questions
1. Is `PYSAT_NONINCREMENTAL` intended as the public selector for non-incremental mode going forward (superseding `with_incremental(False)`), or is it speculative? If the former, add a builder method + a test exercising the `if PYSAT_NONINCREMENTAL` branch in a later stage. If the latter, consider dropping per YAGNI. (Do NOT change now — confirm intent first.)
