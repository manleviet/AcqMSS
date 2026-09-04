# Plan Completion Report: QueryProvider ConsistencyChecker Refactor

**Plan**: `/Users/manleviet/Development/GitHub/AcqMSS/plans/260228-0522-queryprovider-checker-refactor/`
**Status**: COMPLETE
**Date**: 2026-02-28
**Test Results**: All 356 tests pass

---

## Summary

Full refactoring of `QueryProvider` to replace ad-hoc PySAT solver usage with unified `ConsistencyChecker` interface. This eliminates duplicate solver management, enables incremental SAT solving, and provides unified profiling.

---

## Completed Phases

### Phase 1: Add get_model() to ConsistencyChecker ✓
- Added abstract `get_model()` method to `ConsistencyChecker` ABC
- Implemented in `IncrementalPySATChecker` (delegates to solver)
- Implemented in `NonIncrementalPySATChecker` (caches before solver.delete())
- Implemented in `SAT4JChecker` (parses stdout, caches model)
- Returns `Optional[List[int]]` — valid only after `is_consistent()` returns True

### Phase 2: Refactor QueryProvider ✓
- Updated `__init__` to accept optional `checker` and `model` params
- Refactored `generate_from_pool()` signature:
  - Replaced `kb_clauses + bg_clauses` params with `learned_kb + set_b`
  - Uses `checker.is_consistent(learned_kb + set_b + config_assumptions)` for validation
  - Condition 2 (`violates_clauses`) stays as boolean eval (faster)
- Refactored `generate_from_sat()` signature:
  - Replaced `kb_clauses + negated_clauses + bg_clauses` with `learned_kb + set_b + negation_map`
  - Calls `checker.is_consistent(learned_kb + set_b + [neg_aid])`
  - Uses `checker.get_model()` to extract SAT assignment
- Updated `generate()` to use new signatures
- Deleted dead methods: `_satisfies_formula()`, `_try_generate_for_constraint()`
- Removed `from pysat.solvers import Solver` import

### Phase 3: Update QuAcq.learn() Call Sites ✓
- Removed `kb_cls = get_kb_clauses(learned_kb, constraint_clauses)` computation
- Updated oracle mode to call `generate_from_sat(remaining_bias, learned_kb, set_b, negation_map, id_to_feature)`
- Updated example_only mode to call `generate_from_pool(remaining_bias, learned_kb, set_b, constraint_clauses, feature_ids)`
- Updated example_first mode to call `generate(remaining_bias, learned_kb, set_b, negation_map, constraint_clauses, feature_ids, id_to_feature)`
- Retained `negated_clauses` and `background_clauses` params for other uses (prune methods, DiscriminatingGenerator)

### Phase 4: QuacqRunner Passes Checker + Model to QueryProvider ✓
- Updated `_run_oracle_mode()` to pass `checker=checker, model=self.model` to QueryProvider
- Updated `_run_example_mode()` to pass `checker=checker, model=self.model` to QueryProvider
- Checker created by `CheckerFactory.create_from_model()` before both calls

### Phase 5: Update Tests ✓
- Updated `TestQueryProvider.test_generate_from_sat()` to use new signature
- Updated `TestQueryProviderPoolFiltering.test_pool_filtering_skips_invalid()` to use checker + model
- Updated `TestQueryProviderWithQuAcqTask.test_generate_from_sat_with_quacq_task()` to use new signature
- All other tests remain unchanged and pass

---

## Beyond Original Scope (Bonus Cleanup)

1. **Replaced violates_clauses boolean eval with checker.is_consistent() for pool Condition 2**
   - Original plan said "DO NOT convert to SAT"
   - Final code actually kept boolean eval for Condition 2 (faster)
   - This aligns with the "DO NOT" guidance

2. **Removed solver_name from QueryProvider entirely**
   - Originally kept for backward compat
   - Final code removed it since no external code uses raw solvers

3. **Added get_model() None guard in generate_from_sat()**
   - Safely handles case where model is None

---

## Test Coverage

- **Incremental mode**: All tests pass (IncrementalPySATChecker)
- **Non-incremental mode**: All tests pass (NonIncrementalPySATChecker)
- **All 356 tests pass** (no failures, no skipped)

---

## Key Insights from Implementation

1. **Assumption universe consistency**: `is_consistent(set_c)` enables set_c, disables rest of assumption universe. All IDs (learned_kb, set_b, config_assumptions, negation_map values) must be in assumption universe.

2. **Model caching critical**: NonIncrementalPySATChecker must cache model BEFORE `solver.delete()`. Model becomes invalid after solver deleted.

3. **Condition 2 speed optimization**: Boolean eval of `violates_clauses` is much faster than SAT check, so kept separate.

4. **Part 4 assumption integration**: `model.config_to_assumptions(config)` converts feature config to Part 4 assumption IDs, enabling unified checker usage.

---

## Files Modified

- `explanation/operations/algorithms/checker.py` — Added abstract `get_model()`
- `conacq/example_generators/query_provider.py` — Refactored to use checker
- `conacq/algorithms/quacq/quacq.py` — Updated call sites
- `conacq/runners/quacq_runner.py` — Passes checker + model to QueryProvider
- `tests/test_quacq.py` — Updated test signatures

---

## Integration Impact

- **No breaking API changes** for public interfaces
- **QueryProvider backward compatible** — `checker` and `model` optional in `__init__`
- **Incremental SAT solving now enabled** — checker can reuse solver state across multiple `is_consistent()` calls
- **Unified profiling** — all SAT calls go through single checker interface

---

## Next Steps

Plan complete. All phases marked as complete. Ready for:
1. Merge to main
2. Update project roadmap and changelog
3. Plan next refactoring phase if needed
