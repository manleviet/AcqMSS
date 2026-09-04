# QuAcq DI Refactor — Completion Report

**Date:** 2026-02-28 01:08
**Plan:** `/Users/manleviet/Development/GitHub/AcqMSS/plans/260228-0035-quacq-di-refactor/`
**Status:** COMPLETE
**Tests:** 357 passed, 0 failures

---

## Summary

QuAcq DI refactoring completed successfully. All 7 phases finished. System now matches ConGen's dependency injection pattern: injected collaborators at construction, flat raw data params at `learn()`, single learning method with `mode` parameter. QuAcqTask eliminated from algorithm internals.

---

## Achievements

### Phase 1: DiscriminatingGenerator Refactor
- Removed `QuAcqTask` dependency
- Accepts: `background_clauses`, `constraint_clauses`, `negated_clauses`, `id_to_feature`, `solver_name`
- Inlined `model_to_config()` and `_get_constraint_vars()` logic using raw data
- File: 66 LOC, type hints on all public methods

### Phase 2: QueryGenerator Refactor
- Refactored `generate()` and `generate_with_priority()` to accept raw data params
- Removed `_get_negated_clauses()` and `_get_clause_map_for_priority()` duck-typing shims
- Removed `get_bg_clauses` import from `_task_compat`
- File: 187 LOC, stays under 200 LOC limit

### Phase 3: FindScope Refactor
- Created `sat_utils.py` with extracted utility functions
- Refactored `find_scope()` to accept raw params: `constraint_clauses`, `id_to_feature`, `feature_ids`, `bg_clauses`, `kb_clauses`
- Inlined task methods as standalone functions: `partial_config_to_assumptions()`, `_get_constraint_vars()`, `violates_clauses()`
- No QuAcqTask or `_task_compat` imports

### Phase 4: FindC Refactor
- Refactored `find_c()` to accept raw data params
- Uses `sat_utils` functions for computation
- Accepts `generator` param (already refactored DiscriminatingGenerator)
- No QuAcqTask dependency

### Phase 5: QuAcq Class Refactor
- New `__init__` with DI: `oracle`, `query_generator` (optional), `example_provider` (optional), `discriminating_generator` (optional), `profiler` (optional)
- Factory class methods:
  - `for_oracle(oracle, query_gen, discrim_gen, profiler=None)` — `discrim_gen` **required**
  - `for_examples(oracle, example_provider, discrim_gen=None, profiler=None)`
- Single `learn()` with `mode='oracle'|'example_only'|'example_first'` + flat raw data
- No internal QuAcqTask construction
- QuAcq class: ~195 LOC (under 200), QuAcqResult: ~105 LOC

### Phase 6: Update Callers
- `QuAcqRunner._run_oracle_mode()` extracts flat data from task, passes to `learn(mode='oracle')`
- `QuAcqRunner._run_example_mode()` constructs DI objects, calls `learn(mode='example_only')`
- `test_quacq.py` updated to new constructor and `learn()` signature
- All callers adapted without behavioral changes

### Phase 7: Test & Verify
- Full test suite: 357 passed, 0 failures
- New tests:
  - Factory methods (2 tests): `for_oracle()`, `for_examples()`
  - Mode validation (4 tests): invalid mode, oracle mode requirements, example modes
  - sat_utils functions (10 tests): `partial_config_to_assumptions()`, `_get_constraint_vars()`, `violates_clauses()`, etc.
- All 3 learning modes tested end-to-end: oracle, example_only, example_first

---

## Implementation Details

### New Files
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/sat_utils.py` — Extracted SAT utility functions

### Modified Files
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/discriminating_generator.py` — Raw params, no task
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/example_generators/query_generator.py` — Raw params, removed shims
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/findscope.py` — Raw params, utilities from sat_utils
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/findc.py` — Raw params, uses sat_utils
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` — DI constructor, factories, single learn() with mode
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_runner.py` — Uses new API
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py` — Updated constructor, new mode tests

---

## Key Decisions Validated

1. **discrim_gen required in for_oracle()** — Fail fast, no auto-creation. Prevents hidden internal construction.
2. **FindScope/FindC refactored to raw params** — Eliminates QuAcqTask from algorithm entirely. Clean architecture.
3. **All 3 modes tested** — oracle, example_only, example_first end-to-end coverage. Avoids regressions.
4. **Per-run QuAcq construction** — Stateless, simple pattern matches current QuAcqRunner implementation.

---

## Quality Metrics

| Metric | Value |
|--------|-------|
| Test Coverage | 357 tests, 0 failures |
| New Tests | 16 (factories, modes, sat_utils) |
| LOC Changes | ~1500 lines refactored across 7 files |
| File Sizes | All under thresholds (200 LOC for Python) |
| Type Hints | 100% on public methods |
| Imports | Zero QuAcqTask in algorithm package (only in task_preparation) |

---

## Integration Points

- **ConGen alignment:** QuAcq now matches ConGen's DI pattern (oracle, example_provider, profiler injection)
- **Task preparation:** QuAcqTask remains in `conacq.task_preparation` for external callers; algorithm internally uses raw data
- **Runner API:** `QuAcqRunner.run()` adapts per-run, maintains stateless pattern
- **Example generators:** QueryGenerator decoupled from QuAcqTask (raw params)

---

## Commits Ready

Following conventional commit format:
- `refactor: discriminating-generator raw data params (phase 1)`
- `refactor: query-generator raw data params, remove shims (phase 2)`
- `refactor: extract sat_utils, refactor find-scope (phase 3)`
- `refactor: find-c raw params using sat_utils (phase 4)`
- `refactor: quacq di constructor, factories, single learn mode (phase 5)`
- `refactor: update quacq_runner and tests to new api (phase 6)`
- `tests: add factory, mode, sat_utils test coverage (phase 7)`

---

## Unresolved Questions

None. All validation questions answered during plan creation. All phases implemented and tested.

---

## Next Steps (Post-Merge)

1. Code review via `code-reviewer` agent
2. Merge to main branch
3. Update `docs/codebase-summary.md` with new architecture
4. Consider QuAcq pattern for future algorithm packages
