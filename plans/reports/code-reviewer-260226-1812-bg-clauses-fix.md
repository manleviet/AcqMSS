# Code Review: BG Assumption ID Bug Fix

**Date:** 2026-02-26
**Reviewer:** code-reviewer
**Scope:** BG clauses bug fix + QuAcqTask migration + DRY extraction

---

## Code Review Summary

### Scope
- **Files reviewed:** 15 modified + 3 new
- **LOC changed:** ~1,200 (net +600)
- **Focus:** BG assumption ID misinterpretation bug, QuAcqTask assumption-based migration, shared compat helpers
- **Tests:** 63 passed, 0 failed (2 pre-existing failures in unrelated `test_evaluation.py`)

### Overall Assessment

**Solid bug fix with well-structured migration.** The core bug (BG assumption IDs misinterpreted as SAT variable literals) is correctly identified and fixed. The solution introduces `background_clauses` on `QuAcqTask` to store raw BG CNF, extracts shared duck-typing helpers into `_task_compat.py`, and migrates `InteractiveRunner` from deprecated `InteractiveLearner` to `InteractiveModel + QuAcq`.

---

## Critical Issues

**None found.** The bug fix is correct and all callers of the old `isinstance(task.background[0], int)` pattern have been eliminated.

---

## High Priority

### H1. DRY Violation: Duplicate `_get_negated_clauses` implementations

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/example_generators/query_generator.py` (lines 20-30)
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/interactive/_task_compat.py` (lines 17-23)

Two versions of `get_negated_clauses` exist with **different semantics**:
- `_task_compat.get_negated_clauses` returns `[]` when key is missing
- `query_generator._get_negated_clauses` returns `None` when key is missing

The `query_generator.py` version also has a local `_get_clause_map_for_priority` (lines 33-39) that duplicates logic from `_task_compat.get_clause_map`.

**Impact:** Two codepaths with subtly different error semantics. If a constraint is missing from the negated map, `_task_compat` returns `[]` (empty clauses, silently produces trivially SAT formula), while `query_generator` returns `None` (correctly skips).

**Recommendation:** Consolidate into `_task_compat.py` with a single `get_negated_clauses(task, c_id, default=None)` signature. Both callers can then use it consistently:
```python
# _task_compat.py
def get_negated_clauses(task, c_id, *, default=None):
    if hasattr(task, 'negated_clauses') and isinstance(c_id, int):
        return task.negated_clauses.get(c_id, default)
    if hasattr(task, 'negated_constraint_map'):
        return task.negated_constraint_map.get(c_id, default)
    return default
```

### H2. `findc._narrow_with_sat` uses `_task_compat.get_negated_clauses` (returns `[]` on missing)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/interactive/findc.py` (line 149)

```python
neg_j = _get_negated_clauses(task, c_j)  # Returns [] if missing
all_clauses = list(fm_clauses) + clauses_i + neg_j  # No negation -> trivially SAT
```

If a constraint has no negated form, `_get_negated_clauses` returns `[]`. The SAT formula then has no negation constraint, so `solver.solve()` will likely return SAT, producing a discriminating example that doesn't actually discriminate. This is a logic bug inherited from the compat layer returning `[]` instead of `None`.

**Recommendation:** Check for `None`/empty before building the SAT formula, similar to `query_generator.py`'s pattern.

---

## Medium Priority

### M1. Erased type annotations reduce readability

Multiple functions changed return types from specific to generic:
- `find_c() -> Optional[str]` became `-> Optional` (bare `Optional` is invalid per PEP 484)
- `_narrow_with_pool() -> Optional[str]` became `-> Optional`
- `_narrow_with_sat() -> Optional[str]` became `-> Optional`
- `_prune_rejecting_constraints() -> List[str]` became `-> list`
- `_quickxplain_constraints() -> List[str]` became `-> list`

**Impact:** `Optional` without a type argument is `Optional[Any]` which loses type safety. Bare `list` is fine in Python 3.9+ but inconsistent with the codebase's use of `List[...]`.

**Recommendation:** Use `Optional[Union[int, str]]` or the `TaskType`-aware return type. At minimum, fix `Optional` to `Optional[Any]` to be explicit.

### M2. `_try_generate_for_constraint` bg_clauses type narrowed without validation

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/example_generators/query_generator.py` (line 96)

The parameter `bg_clauses` changed from `List[int]` to `list`. The old code had an `isinstance(bg_clauses[0], int)` check to handle both list-of-ints and list-of-clauses formats. Now it assumes callers always pass `List[List[int]]` from `get_bg_clauses()`. This is correct for current callers but removes the defensive check.

**Impact:** Low -- all current callers go through `get_bg_clauses()` which always returns `List[List[int]]`.

### M3. `InteractiveRunner` bias shuffle may not behave identically

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/interactive_runner.py` (lines 180-184)

Old code: `keys = list(learner.task.bias)` (bias was a list of strings)
New code: `keys = sorted(task.bias)` then shuffle, then `task.bias = set(keys)`

Since `task.bias` is a `set`, converting back after shuffle loses ordering. The shuffle is effectively meaningless since `set()` discards insertion order. However, this may be intentional -- the shuffle only affects iteration order, and sets don't preserve it regardless. If the old behavior relied on ordering, this is a behavioral change.

**Impact:** In Python 3.7+, `set` iteration order is implementation-defined. If `QuAcq` iterates `task.bias` and order matters (e.g., first constraint tested), results may differ from old behavior. But `for c_id in task.bias` in `QueryGenerator.generate()` iterates the set directly, so shuffle has no effect.

**Recommendation:** If shuffle is meant to affect iteration order, `task.bias` should be stored as an ordered structure (e.g., `list` with a `set` for O(1) membership checks). Otherwise, remove the shuffle code for QuAcqTask path as it's a no-op.

---

## Low Priority

### L1. Excessive comment removal

Many explanatory comments were stripped from `quacq.py`, `findc.py`, and `query_generator.py`. While some were redundant, others provided algorithmic context (e.g., "Build formula: KB + BG + not-c"). Code is still readable but less self-documenting for newcomers.

### L2. `DeprecationWarning` in `InteractiveTask.__post_init__`

Good practice adding deprecation warnings. However, the warning fires on every instantiation including in tests, producing 18 warnings. Consider making tests use `pytest.warns(DeprecationWarning)` context manager to suppress noise.

---

## Edge Cases Found

1. **Empty `background_clauses` + non-empty `background`:** `get_bg_clauses()` falls through to the legacy `isinstance(task.background[0], int)` path. For `QuAcqTask`, this means if `background_clauses` is empty but `background` has assumption IDs, it would wrap assumption IDs as unit clauses -- which is exactly the bug being fixed. This can happen if `InteractiveTaskPreparation` fails to populate `background_clauses` but populates `background`.

   **Mitigation:** The preparation code always sets both fields together (lines 57-63 of `interactive_task_preparation.py`), so this shouldn't occur in practice. But a defensive check or assertion in `QuAcqTask.__post_init__` would prevent regression.

2. **`bg_data.set_kb` contains both root + negated root clauses.** The filter `clause[-1] == -root_aid` correctly extracts only the original root constraint. If BGData ever adds more constraint pairs, this extraction would need updating. Currently safe since BGData is frozen to a single root pair.

3. **`_apply_reduce` passes `task.background` (assumption IDs) to `reduce.reduce(set_bg=...)`.** This is correct -- REDUCE expects assumption IDs for `set_bg`, not raw clauses. The BG assumptions are activated in the checker via `set_kb` assumption guards.

---

## Positive Observations

1. **Correct root cause identification.** The bug (`isinstance(task.background[0], int)` treating assumption IDs as SAT variables) was subtle and the fix (separate `background_clauses` field) is clean.

2. **Good test coverage.** 9 new test classes with 34 new tests covering QuAcqTask, InteractiveModel, task compat helpers, background clauses, and assumption ID result serialization.

3. **Backward compatibility preserved.** Old `InteractiveTask`/`InteractiveLearner` paths still work with deprecation warnings. `InteractiveResult.load()` handles old format without `kb_assumption_ids`.

4. **`_task_compat.py` is well-scoped.** Single-responsibility module with 3 focused helpers, no unnecessary abstraction.

5. **Clean `InteractiveRunner` migration.** Removed dependency on deprecated `InteractiveLearner.from_files()` / `from_examples()`, using `InteractiveModel + QuAcq` directly.

---

## Recommended Actions

1. **[High]** Consolidate `_get_negated_clauses` into `_task_compat.py` with `default=None` parameter. Remove duplicates from `query_generator.py`.
2. **[High]** Fix `findc._narrow_with_sat` to skip constraints with no negated form (guard against empty `[]` from `get_negated_clauses`).
3. **[Medium]** Fix bare `Optional` return type annotations to `Optional[Any]` or `Optional[Union[int, str]]`.
4. **[Medium]** Evaluate whether bias shuffle in `InteractiveRunner` is actually effective with `set`-based bias. If not, remove the dead code.
5. **[Low]** Add assertion in `QuAcqTask.__post_init__`: if `background` is non-empty, `background_clauses` should also be non-empty.

---

## Metrics

- **Type Coverage:** Reduced in modified files (bare `list`, `dict`, `Optional` without args). Elsewhere stable.
- **Test Coverage:** 63/63 interactive tests pass. New tests cover all new classes/helpers.
- **Linting Issues:** No syntax errors. Deprecation warnings expected and correct.

---

## Unresolved Questions

1. Should `_task_compat.get_negated_clauses` return `None` or `[]` as default? Current inconsistency between `_task_compat.py` (`[]`) and `query_generator.py` (`None`) needs a decision.
2. Is the bias shuffle in `InteractiveRunner` intended to have no effect for QuAcqTask (set-based bias), or is this an oversight from the migration?
3. Should `QuAcqTask.background_clauses` be validated against `QuAcqTask.background` in `__post_init__` to prevent the fallback bug from resurfacing?
