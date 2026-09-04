---
phase: 1
title: A7 pytest infra (conftest + resources)
status: completed
priority: P1
effort: 1d
dependencies: []
---

# Phase 1: A7 — pytest infra (conftest + resources)

## Overview
Build the test infrastructure every later stage rides on: a single pytest convention, a `conftest.py` with shared fixtures, and a `tests/resources.py` single source for resource paths. Do FIRST — building it late means rewriting tests twice.

## Requirements
- Functional: shared fixtures for model+task setup and checker creation; one resource-path module; pytest as the only runner.
- Non-functional: suite stays green throughout; no behavioral test changes; no weakened assertions.

## Architecture
- `tests/conftest.py`: fixtures for the repeated `builder → prepare_task → checker` chain (3 checker-creation variants), plus FM/bias path fixtures.
- `tests/resources.py`: single class/functions returning resource paths (replaces the 3 styles in test_congen.py:25-29, test_diagnosis.py `Resources` class :160-180, test_evaluation.py:28-32, test_quacq.py:33-35).
- Migrate the 3 unittest files: `test_utils.py`, `test_executor.py` (easy, no parametrize) now; `test_diagnosis.py` (`@parameterized.expand` + `ENABLED_TESTS` :48-101 / `ENABLED_PARAMS` :107-114; `Resources` :102) pytest-migration is owned by **C7** (see Red-team adjustments) — pytest runs it as-is meanwhile, and A3/B2/C7/C3 each update its params/imports in-stage.

## Related Code Files
- Create: `tests/conftest.py`, `tests/resources.py`
- Modify: `tests/test_utils.py`, `tests/test_executor.py` (unittest→pytest); fold ~23 setup clones in `test_congen.py`/`test_diagnosis.py`/`test_quacq.py` into fixtures
- Move (out of `tests/`): `tests/test_bias_module.py` (117 lines, 0 asserts), `tests/test_bias_module_1.py` (27 lines, 0 asserts) — demo scripts → `apps/` or a `scripts/`/`examples/` location (confirm dest in implementation)
- Config: ensure `pyproject.toml`/`pytest.ini` testpaths/markers register `slow` (kills the known unregistered-marker warning)

## Implementation Steps
1. Add `tests/resources.py` (single resource-path source); add `tests/conftest.py` with model+task+checker fixtures.
2. Rewrite test_utils + test_executor to pytest style using the fixtures.
3. Refactor test_congen/test_diagnosis/test_quacq setup duplication to consume fixtures (keep all assertions identical).
4. Relocate the two demo non-tests out of `tests/`; update any references.
5. Register the `slow` marker; set pytest as default runner.
6. `PYTHONPATH=. pytest tests/ -v` → all green.

## Success Criteria
- [ ] `tests/conftest.py` + `tests/resources.py` exist and are consumed by all touched tests
- [ ] test_utils + test_executor run under pytest (no `unittest.TestCase`)
- [ ] Resource paths defined once; ≤1 copy remains (test_diagnosis deferred copy documented)
- [ ] Two demo scripts no longer under `tests/`
- [ ] Full suite green (≥351), no new warnings introduced

## Red-team adjustments (applied 260621)
- **test_diagnosis ownership corrected.** Do NOT "defer migration to a B-phase" — test_diagnosis exercises SAT4J (A3), profiler (B2), qx/wipeoutr/labelers (C7), redundancy ops (C3). The `@parameterized.expand`→`@pytest.mark.parametrize` migration is OWNED BY C7 (first C-phase touching diagnosis code). Until then pytest runs it as-is. **Each phase changing a diagnosis symbol (A3, B2, C7, C3) MUST update test_diagnosis's params/imports within its own stage** to keep the suite green.
- **Stale line fixed:** `Resources` class is at `test_diagnosis.py:102` (not :160-180); `ENABLED_TESTS` :48-101, `ENABLED_PARAMS` :107-114.

## Risk Assessment
- Fixture refactor accidentally changing a setup detail → mitigate by refactoring one test file at a time, re-running suite after each.
- test_diagnosis migration is genuinely harder (param matrix) — intentionally deferred; pytest executes it unchanged so no risk now.
