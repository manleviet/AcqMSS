# Code Review — B1 explanation public surface + boundary

Date: 2026-06-21 | Branch: feat/redesign-abc | Scope: uncommitted working-tree only
Spec: plans/260621-1416-redesign-abc/phase-11-b1-explanation-public-surface-boundary.md

## Verdict

**B1: PASS** (with 1 must-fix rule violation + 2 should-fix over-exposure items; none block runtime correctness)

- **(1) Behavior-preserving: PASS (verified).** All 36 api.py re-exports are the *same object* (`is`) as their deep-path originals. api.py re-exports, never redefines/wraps/shadows. 498 tests green.
- **(2) Guard test is real: PASS (verified).** Exercised `_check_file` against synthetic violations — catches deep-reach, underscore-from-api, and bare deep `import`; allows `explanation.api` + bare `explanation`; ignores non-explanation. Asserts file count (>0 and >=20). Scans all `conacq/**/*.py`.

## Test status
- Full suite: 498 passed, 1 warning (53.9s) — warning is the pre-existing TestSuiteReader collection warning (C7-owned), not introduced by B1.
- B1 new tests: 30 passed (27 transformations + 3 boundary).
- No flaky failure observed (no re-run needed).

## Findings by severity

### MEDIUM — M1: Plan-stage labels in code comments (rule violation)
`review-audit-self-decision.md` §5 forbids plan-stage labels (phase/B1/B2/finding codes) in code & comments — they become unresolvable noise when plan headers get renumbered. Three instances:
- `explanation/api.py:6` — `Profiler name convention (settled in B1):`
- `tests/test_boundary_guard.py:8` — `Allowed explanation import patterns after B1:`
- `tests/test_transformations_characterization.py:8` — `excluded per the B1 safety-net spec.`

Fix: rephrase to the stable *reason*, drop the stage label. E.g. api.py:6 → "Profiler name convention:"; boundary_guard:8 → "Allowed explanation import patterns:"; transformations:8 → "dimacs_to_configuration.py has zero importers (dead code) and is intentionally excluded." (The `_ProfilerProtocol` mentions at api.py:9,71 and boundary_guard:4 are stable symbol references explaining *why*, and are acceptable.)

### MEDIUM — M2: Over-exposure — `DiagnosisTaskPreparationStrategy` has no conacq consumer; spec claim is inaccurate
Spec (`## 3` red-team note) claims 5 prep-strategy extension points are "real conacq extension needs". Verified each:
- `TestCaseTaskPreparationStrategy` — REAL: subclassed by `ConGenTaskPreparation` (conacq/algorithms/acqmss/task_preparation.py:53). ✅
- `PreparationOutput`, `prepare_kb`, `prepare_testsuite_with_negation` — REAL: used in fm_oracle_model.py (189,255) + acqmss/task_preparation.py (73,…). ✅
- `DiagnosisTaskPreparationStrategy` — **NOT used by conacq.** `QuAcqTaskPreparation` extends only `OracleAwareTaskPreparation` (a plain conacq class), and `QuAcqTask` extends `DiagnosisTask` (the task, not the Strategy ABC). The Strategy ABC is subclassed only inside `explanation/models/task_preparation.py:392` (framework-internal). Zero conacq importers.

Impact: low (extra export, no runtime cost) but the spec justification is wrong. Either drop `DiagnosisTaskPreparationStrategy` from the surface, or keep it as a *declared* future extension point (like SolverBackend) and correct the spec note from "subclassed by conacq" to "reserved symmetric extension point". Recommend: keep only if intentionally symmetric with TestCase variant; otherwise YAGNI-cut.

### LOW — L1: Other exports with no current conacq importer (justified, document intent)
8 of 36 exports are not imported by any conacq file. Categorized:
- `SolverBackend` — sanctioned placeholder until C1. Keep. ✅
- `ProfilerProtocol` — B2 dependency-type, planned consumer surface. Keep. ✅
- `ModelProtocol` — structural Protocol; conacq models satisfy it by duck-typing (referenced only in docstrings). Keep — it is the documented contract. ✅
- `Profiler` (concrete), `NullProfiler` — conacq type-annotates against `AbstractProfiler`, not these. Borderline; keep `Profiler` (natural pair w/ Protocol), consider whether `NullProfiler` is needed on the *cross-boundary* surface (no conacq consumer).
- `Task` (base) — conacq uses `DiagnosisTask`/`TestCaseTask` only. Keep as the documented base type or YAGNI-cut.
- `DimacsToDiagPysat` — conacq uses only `FmToDiagPysat` (fm_oracle_model.py:138, ground_truth.py:40). `DimacsToDiagPysat` has no conacq consumer. Likely cut candidate (it IS reached via diagnosis_model_builder inside explanation, but that's internal — doesn't need to cross the conacq boundary).
- `DiagnosisTaskPreparationStrategy` — see M2.

These are non-blocking. Recommend a one-line `__all__` comment marking the *intentional-future* exports (SolverBackend, ProfilerProtocol, ModelProtocol, Task) vs. removing the genuinely-unneeded (`DimacsToDiagPysat`, `DiagnosisTaskPreparationStrategy`, possibly `NullProfiler`).

## Checklist verifications (all PASS)
- Re-points complete: 0 residual deep `from explanation` imports in conacq (the 2 grep hits at algorithms/__init__.py:63 and acqmss/__init__.py:64 are comments, not imports). No bare deep `import explanation.X`.
- `_ASSUMPTION_PAIR_STRIDE`: stays internal — `slice_assumptions` is the public helper; no conacq import of the stride constant.
- ProfilerProtocol rename: complete. `_ProfilerProtocol` alias removed from profiler/__init__.py `__all__`; `hasattr(profiler, '_ProfilerProtocol')` is False; no live consumers (only doc mentions). No consumer broke.
- `last_task`: zero references — no regression.
- Transformations safety-net REAL: 27 non-trivial characterization assertions (instance types, populated/empty maps under create_negation flag, codec name↔idx round-trip, malformed-DIMACS → FlamaException, missing-file → ConfigurationNotFound, static extension strings). Assertions verified against the real `Assignment(feature:str, value:bool)` dataclass and DiagnosisModel API. Not vacuous.
- `dimacs_to_configuration` correctly EXCLUDED: confirmed zero importers (only its own class def + the test's explanatory comment). C6 deletion target intact.
- No weakened assertions: transformations tests use `assertGreater`/`assertEqual`/`assertRaises(specific exception)` — strong forms. Boundary test fails loudly with violation list.
- Allowed-module set correct: `{explanation, explanation.api}` — allows both `from explanation.api` and bare `from explanation` per spec line 19/B1 req. Matches spec intent.
- `__all__` integrity: 36 names, no duplicates, all present on module.

## Positive observations
- api.py is genuinely curated from a usage audit, not a dump — 28/36 exports have direct conacq importers; the 8 without are mostly intentional (protocols/placeholders).
- Guard test has a 3-layer design: (a) violation scan, (b) surface-importability smoke test, (c) file-count sanity — good defense against vacuous-pass.
- Re-export-not-redefine discipline is perfect (36/36 `is`-identity), which is exactly what makes the future canonical-repo extraction a clean cut.
- Profiler name convention cleanly settled; transitional alias fully removed.

## Recommended actions (priority order)
1. (M1) Strip the 3 plan-stage labels from comments — rephrase to stable reason. *Must-fix per project rule before commit.*
2. (M2) Resolve `DiagnosisTaskPreparationStrategy`: cut it, or keep + correct the spec's "subclassed by conacq" claim to "reserved extension point".
3. (L1) Optionally trim `DimacsToDiagPysat` / `NullProfiler` from the cross-boundary surface, or annotate intentional-future exports in `__all__`.

## Unresolved questions
1. Is `DiagnosisTaskPreparationStrategy` meant as a *symmetric reserved* extension point (keep) or was the spec's "subclassed by conacq" claim a genuine error (cut)? Affects M2 resolution.
2. Should `DimacsToDiagPysat` cross the conacq boundary at all? It has no conacq consumer; its only live use is internal to `explanation/diagnosis_model_builder`. If conacq never builds from DIMACS, it is over-exposure.
