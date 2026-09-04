# Code Review: QuAcq DI Refactor (commit b038a74)

**Date**: 2026-02-28
**Commit**: `b038a74` — "refactor: align QuAcq DI pattern with ConGen for consistency"
**Scope**: 15 files changed, +944 / -445 lines

---

## Scope

- **Files**: 15 (10 source, 4 docs, 1 test)
- **LOC changed**: ~1,389
- **Focus**: DI pattern refactoring -- QuAcq constructor injection, single `learn()` method, `sat_utils.py` extraction, DescriptionProvider removal from algorithm

## Overall Assessment

**GOOD refactoring**. Successfully:
- Merges `learn()` + `learn_from_examples()` into single mode-dispatched `learn()`
- Extracts pure SAT utilities to `sat_utils.py` (93 LOC)
- Removes DescriptionProvider from algorithm layer (runner resolves names)
- Aligns QuAcq DI pattern with ConGen
- Fixes `set_b` to contain only original BG assumption (matching ConGen's existing pattern)
- Adds factory methods `for_oracle()` / `for_examples()` with mode validation
- All 357 tests pass

Core logic preserved; no behavioral regressions detected.

---

## Critical Issues

### 1. Missing `_require_task()` in QuAcqModel (carried forward from prior commit)

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py` lines 69-100

New convenience getters (`get_c`, `get_b`, `get_kb`, `get_negation_map`, `get_assumptions`) call `self._require_task()` which is **never defined** on `QuAcqModel`. Will crash with `AttributeError` at runtime.

**Impact**: Not currently triggered (no production caller uses these getters on QuAcqModel), but violates the CheckerModel protocol contract they implement.

**Fix**: Add the missing method:
```python
def _require_task(self) -> QuAcqTask:
    if self._task is None:
        raise RuntimeError("Call prepare() first")
    return self._task
```

Or remove the dead getters if they are not needed yet (YAGNI).

---

## High Priority

### 2. Documentation inconsistencies in code examples (3 files)

**Files**:
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md` line 202, 203, 314
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/quacq.md` lines 48, 178, 307-308
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` lines 100-101, 600-601, 699-701

**Issues**:
- `QueryGenerator(max_query_size=10)` -- no such parameter; constructor accepts `solver_name` and `profiler_instance`
- `DiscriminatingGenerator()` -- requires 4 positional args: `background_clauses`, `constraint_clauses`, `negated_clauses`, `id_to_feature`
- `code-standards.md` line 314: `learn()` signature includes `description_provider=None` but actual implementation removed that parameter
- `quacq.md` lines 48, 178: References to `learn_from_examples()` which no longer exists
- `system-architecture.md` lines 600, 701: References to `learn_from_examples()` which no longer exists

**Impact**: Misleading developer documentation; copy-paste will produce runtime errors.

### 3. `_task_compat.py` is dead code

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/_task_compat.py` (45 LOC)

No imports reference this module from any production code. All consumers migrated to `sat_utils.py`. The comment in `conacq/example_generators/__init__.py` line 10 still references the old circular dependency via `_task_compat` (stale comment).

**Fix**: Delete `_task_compat.py` and update the stale comment in `example_generators/__init__.py`.

---

## Medium Priority

### 4. `_learn_params_from_task` duplicated (runner + tests)

**Files**:
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/quacq_runner.py` lines 51-63
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py` lines 40-52

Identical helper duplicated. Previously flagged. Consider adding `to_learn_params()` on `QuAcqTask` itself.

### 5. `_model_to_config` duplicated across 3 classes

**Locations**:
- `DiscriminatingGenerator._model_to_config` (line 78)
- `QueryGenerator._model_to_config` (line 105)
- `QuAcqTask.model_to_config` (line 88)

All perform identical SAT-model-to-config-dict conversion. Could be extracted to `sat_utils.py` as a pure function.

### 6. `quacq.py` at 464 lines (exceeds 200-line threshold)

`QuAcqResult` (141 lines) is co-located with `QuAcq` class (323 lines). Extracting `QuAcqResult` to its own file (`quacq_result.py`) would bring both under threshold.

---

## Low Priority

### 7. `violates_clauses` treats unknown variables as non-satisfying

In `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/sat_utils.py` lines 48-61, when a variable in a clause is not in the `assignment` dict, the literal is treated as not satisfying the clause. This is correct for the current conservative pruning use case but could be surprising in other contexts. A docstring note would help.

### 8. Hardcoded solver name in `_apply_reduce`

In `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` line 432:
```python
checker = NonIncrementalPySATChecker(set_kb, assumptions, 'glucose4', self.profiler)
```
The solver name `'glucose4'` is hardcoded rather than using a configurable value. Minor since it's an internal implementation detail.

---

## Edge Cases Found

1. **Oracle mode FindC behavior**: When `mode='oracle'`, `find_c` is called with `example_provider=None` and `query_mode='example_only'`. This means neither pool narrowing nor generator narrowing runs -- FindC returns the first rejecting candidate. Verified this matches the old behavior exactly (old `learn()` also passed defaults to `find_c`).

2. **`set_b` change in task_preparation.py**: Changed from `list(bg_data.assumptions)` (both original + negated) to `[bg_data.assumptions[0]]` (original only). Verified this aligns with ConGen's `task_preparation.py` line 225 which already uses `[result.assumptions[0]]`. The negated form is tracked separately in `negation_map`. Correct fix.

3. **`example_generators/__init__.py`**: Comment references old `_task_compat` circular dependency chain (line 10). The circular dependency may still exist through different paths -- verify before removing the lazy import pattern.

---

## Positive Observations

1. **Clean DI pattern**: `QuAcq.__init__` now receives all collaborators; no internal creation. Matches ConGen's checker injection pattern.
2. **Factory methods with validation**: `for_oracle()` and `for_examples()` with `_validate_mode()` provide clear error messages for misconfigured instances.
3. **`sat_utils.py` extraction**: Pure functions with no state -- easily testable and reusable. Good granularity.
4. **Comprehensive new tests**: `TestQuAcqFactories`, `TestQuAcqModeValidation`, `TestSatUtils` add 16 new test cases covering DI wiring, mode validation, and extracted utilities.
5. **`_learn_params_from_task` helper**: Clean adapter between task object and flat params, isolates the conversion.
6. **Consistent mode dispatch**: Single `learn()` with `mode` parameter eliminates the dual-method confusion.

---

## Recommended Actions

1. **(Critical)** Add `_require_task()` to `QuAcqModel` or remove the 5 dead convenience getters
2. **(High)** Fix doc code examples: correct `QueryGenerator` and `DiscriminatingGenerator` constructor args in `code-standards.md`, `quacq.md`, `system-architecture.md`
3. **(High)** Remove stale `learn_from_examples()` references from `quacq.md` (lines 48, 178) and `system-architecture.md` (lines 600, 701)
4. **(High)** Delete dead `_task_compat.py`; update stale comment in `example_generators/__init__.py`
5. **(Medium)** Deduplicate `_learn_params_from_task` -- consider `QuAcqTask.to_learn_params()`
6. **(Medium)** Extract `model_to_config` to `sat_utils.py` to DRY the 3 copies
7. **(Low)** Consider extracting `QuAcqResult` to its own file to bring `quacq.py` under 200 lines

---

## Metrics

- **Test Coverage**: 357/357 passing (100% green)
- **New Tests Added**: 16 (factories, mode validation, sat_utils)
- **Dead Code**: `_task_compat.py` (45 LOC) -- safe to delete
- **File Size Violations**: `quacq.py` (464 lines), `test_quacq.py` (912 lines)

---

## Unresolved Questions

1. Should the 5 convenience getters on `QuAcqModel` be fixed (add `_require_task()`) or removed (YAGNI -- no caller uses them)?
2. Is the lazy import in `example_generators/__init__.py` still needed after `_task_compat` removal, or has the circular dependency been resolved?
3. Should `description_provider=None` in the `code-standards.md` learn() signature be removed, or is it kept intentionally for potential future use?
