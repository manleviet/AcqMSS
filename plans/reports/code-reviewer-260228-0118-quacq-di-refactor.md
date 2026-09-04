# Code Review: QuAcq DI Refactor

**Date**: 2026-02-28
**Scope**: 10 files changed, +702 / -369 lines
**Focus**: DI pattern, mode validation, sat_utils correctness, backward compat

## Overall Assessment

Strong refactor. QuAcq now takes collaborators at construction time instead of reaching into `QuAcqTask` for everything. `learn()` unified into single method with mode dispatch. `sat_utils.py` cleanly extracts pure functions. Tests comprehensive: 63 tests, all passing.

## Critical Issues

### 1. Missing `_require_task()` method in QuAcqModel (CRITICAL)

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py`

New convenience getters `get_c()`, `get_b()`, `get_kb()`, `get_negation_map()`, `get_assumptions()` all call `self._require_task()` which is **never defined**. Will crash with `AttributeError` at runtime.

**Impact**: Dead code today (no callers in production), but will break if anyone calls these CheckerModel protocol methods.

**Fix**: Add the method or remove the convenience getters:
```python
def _require_task(self) -> QuAcqTask:
    if self._task is None:
        raise RuntimeError("Call prepare() first")
    return self._task
```

## High Priority

### 2. `_validate_mode` missing check for `example_first` + `discriminating_generator`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (line 372-382)

`example_first` mode uses `discriminating_generator` in `FindC._narrow_with_generator()` (line 171 of `findc.py`). But `_validate_mode` only checks `query_generator` for `example_first`, not `discriminating_generator`. If constructed without it, will crash with `AttributeError: 'NoneType' object has no attribute 'generate'` at runtime.

**Impact**: Runner wires it correctly, so not hit today. But the validation is incomplete, leaving a trap for direct API users.

**Fix**:
```python
if mode == 'example_first':
    if self.query_generator is None:
        raise ValueError("example_first mode requires query_generator")
    if self.discriminating_generator is None:
        raise ValueError("example_first mode requires discriminating_generator")
```

### 3. No validation for invalid mode strings

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (line 372-382)

`_validate_mode` only checks specific modes for deps, but `learn()` with `mode='garbage'` would silently proceed and never generate a query (falls through all `if mode ==` branches), returning `convergence_reason = ''` (empty string).

Runner validates mode in `run()` (line 148-152), but direct `QuAcq.learn()` callers are unprotected.

**Fix**: Add at top of `_validate_mode`:
```python
valid_modes = ('oracle', 'example_only', 'example_first')
if mode not in valid_modes:
    raise ValueError(f"Unknown mode '{mode}'. Use one of: {valid_modes}")
```

## Medium Priority

### 4. `_learn_params_from_task` duplicated (DRY violation)

Identical helper defined in:
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/quacq_runner.py` (line 51)
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py` (line 40)

**Fix**: Move to `sat_utils.py` or `task_preparation.py` and import from there.

### 5. `DiscriminatingGenerator._get_constraint_vars` duplicates `sat_utils.get_constraint_vars`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/discriminating_generator.py` (line 85-94)

Identical logic to `sat_utils.get_constraint_vars`. The private method could delegate to the public function.

**Fix**:
```python
from .sat_utils import get_constraint_vars

def _get_constraint_vars(self, assumption_id: int) -> Set[str]:
    return get_constraint_vars(assumption_id, self._constraint_clauses, self._id_to_feature)
```

### 6. `__init__.py` example is verbose -- API ergonomics concern

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/__init__.py` (line 19-42)

The docstring usage example went from 3 lines to 15 lines. While accurate, the DI pattern makes the simple case more verbose. Users must manually extract 10 flat params from task and pass them individually.

**Suggestion**: Consider a `learn_from_task(task, ...)` convenience method or make `_learn_params_from_task` part of the public API so the common case remains ergonomic.

### 7. Commented-out `get_cf()` in `QuAcqModel`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py` (line 77-84)

Dead commented-out code adds noise. Either implement or remove.

### 8. `_task_compat.py` now orphaned from production code

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/_task_compat.py`

Only referenced by tests (`TestTaskCompat` class) and a stale comment in `example_generators/__init__.py`. No production code imports it anymore. The circular dependency comment in `example_generators/__init__.py` (line 9-12) still references it but the dep chain through `_task_compat` no longer exists since `QueryGenerator` no longer uses it.

**Fix**: Consider removing `_task_compat.py` and `TestTaskCompat` if no longer needed. Update the lazy import comment.

## Low Priority

### 9. `violates_clauses` edge case: unassigned variables treated as violation

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/sat_utils.py` (line 48-61)

If a clause contains only variables NOT in `assignment`, it's treated as violated (returns `True`). This is correct for the current use cases (full configs or scope-restricted partial checks), but could surprise future callers with truly sparse assignments.

**Verdict**: Acceptable. Document the behavior.

### 10. Type annotations incomplete in `find_c`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/findc.py` (line 33)

`generator` param has no type annotation. Should be `Optional[DiscriminatingGenerator]` to match the DI pattern and catch None-passing issues at type-check time.

## Positive Observations

- Clean DI pattern: collaborators injected at construction, not pulled from task
- Factory classmethods (`for_oracle`, `for_examples`) guide correct construction
- Single `learn()` method with mode dispatch eliminates method proliferation
- `sat_utils.py` extracts pure functions -- easy to test, no side effects, well-typed
- Comprehensive mode validation tests (4 test cases for each invalid combo)
- `sat_utils` tests cover all functions with both positive and negative cases
- Solver cleanup with `try/finally` blocks in `DiscriminatingGenerator` and `QueryGenerator`
- `record_query` closure pattern cleanly captures query history without mutable class state
- All 63 tests pass, 0 failures

## Recommended Actions

1. **[Critical]** Add `_require_task()` to `QuAcqModel` or remove dead getters
2. **[High]** Add `discriminating_generator` check for `example_first` in `_validate_mode`
3. **[High]** Add unknown mode rejection in `_validate_mode`
4. **[Medium]** Deduplicate `_learn_params_from_task` -- move to shared location
5. **[Medium]** Delegate `DiscriminatingGenerator._get_constraint_vars` to `sat_utils`
6. **[Low]** Remove orphaned `_task_compat.py` and `TestTaskCompat`
7. **[Low]** Add type annotation to `find_c(generator=...)` param

## Metrics

- Test Coverage: 63 tests, all passing
- Type Coverage: Good in new code; `find_c.generator` param untyped
- Linting Issues: 0 syntax errors, imports verified
- DRY Violations: 2 (learn_params helper, get_constraint_vars)

## Unresolved Questions

1. Should `_learn_params_from_task` be a method on `QuAcqTask` itself (e.g., `task.to_learn_params()`)? This would be the most natural location and eliminate the duplication.
2. Are the `QuAcqModel` convenience getters (`get_c`, `get_b`, etc.) actually needed? They implement the CheckerModel protocol, but `QuAcqModel` is not currently used with `CheckerFactory`. If not needed, removing them is simpler than fixing `_require_task`.
3. The stale circular dependency comment in `example_generators/__init__.py` -- is the lazy import still necessary after the `_task_compat` decoupling?
