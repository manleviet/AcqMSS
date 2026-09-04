# Code Review: Unified Runner Lifecycle Refactoring

**Date:** 2026-02-27
**Reviewer:** code-reviewer
**Scope:** BaseRunner/BaseRunResult extraction, runner inheritance, CV loop unification

---

## Scope

- **Files reviewed:** 8 (base_runner.py [NEW], congen_runner.py, interactive_runner.py, runners/__init__.py, performance_metrics.py, cross_validation.py, eval/__init__.py, extract_results.py)
- **LOC changed:** ~400 (new + modified)
- **Focus:** Backward compatibility, dataclass inheritance correctness, lifecycle safety, edge cases

---

## Overall Assessment

Solid refactoring that correctly extracts 9 shared fields into `BaseRunResult` and a build-once/run-many/cleanup-once lifecycle into `BaseRunner`. The dataclass inheritance design is sound, the `kw_only=True` approach for `profiler_data` is the correct Python 3.10+ solution for default-before-required ordering, and the CV loop unification eliminates significant duplication. A few issues found, one critical.

---

## Critical Issues

### 1. `n_bias_constraints` AttributeError in `apps/run_interactive.py` (line 47)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_interactive.py`
**Line:** 47

```python
print(f"  Bias constraints: {runner.n_bias_constraints}")
```

`n_bias_constraints` is NOT defined on `InteractiveRunner`, `BaseRunner`, or any ancestor. This will raise `AttributeError` at runtime when `--verbose` is used. The property existed on an older runner version or was never added after the refactoring.

**Fix options:**
- Add property to `InteractiveRunner`: `return len(self.model.constraint_map)`
- Or reference `len(runner.model.constraint_map)` directly in the app
- Or add a common `n_bias_constraints` property to `BaseRunner` (both runners have a `model` with `constraint_map`)

---

## High Priority

### 2. Missing `cleanup()` call in `_run_cv_loop` (resource leak)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/cross_validation.py`

Neither `_run_cv_loop` nor the public `n_fold_cross_validation` / `n_fold_cross_validation_interactive` functions call `runner.cleanup()`. The runner creates an oracle with a SAT solver in `__init__()`, and without cleanup, the solver resources leak when the function returns.

Both `apps/run_interactive.py` and `apps/run_evaluation.py` properly call `runner.cleanup()`. The CV path does not.

**Fix:** Add a `try/finally` block in the public functions:

```python
def n_fold_cross_validation(...):
    runner = ConGenRunner(...)
    try:
        return _run_cv_loop(runner, ...)
    finally:
        runner.cleanup()
```

Same for `n_fold_cross_validation_interactive`.

### 3. `kb_clauses` omitted from `_base_to_dict()` serialization

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/base_runner.py`

`BaseRunResult` has `kb_clauses: List[List[int]]` as a field, but `_base_to_dict()` serializes `kb_constraints` and `bg_clauses` while omitting `kb_clauses`. Neither `InteractiveRunResult.to_dict()` nor `ConGenRunResult.to_dict()` add it back.

If `kb_clauses` is intentionally excluded from JSON (it's large and only needed for accuracy calculations), this should be documented with a comment. If it's an oversight, add it to `_base_to_dict()`.

### 4. `BaseRunner` not usable as context manager

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/base_runner.py`

`BaseRunner` has a `cleanup()` method but does not implement `__enter__`/`__exit__`. This means callers must remember to call `cleanup()` manually (and risk missing it, as seen in issue #2). Adding context manager support would make the API more Pythonic and safer:

```python
def __enter__(self):
    return self

def __exit__(self, *exc):
    self.cleanup()
```

---

## Medium Priority

### 5. `InteractiveRunner.run()` signature differs from `BaseRunner.run()` (LSP concern)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/interactive_runner.py`

`BaseRunner.run()` abstract signature:
```python
def run(self, positive_examples=None, negative_examples=None, shuffle_seed=None) -> BaseRunResult
```

`InteractiveRunner.run()` adds `mode: Optional[str] = None` parameter:
```python
def run(self, positive_examples=None, negative_examples=None, mode=None, shuffle_seed=None) -> InteractiveRunResult
```

This technically violates Liskov Substitution Principle since callers using `BaseRunner` type hints cannot pass `mode`. In practice, this works because:
- `_run_cv_loop` doesn't pass `mode` (uses default `query_mode`)
- `mode` has a default value

However, this means the abstract method's docstring is misleading about the interface contract. Consider adding a comment on the abstract method noting subclasses may accept additional keyword arguments, or accept `**kwargs` in the base.

### 6. No tests for `BaseRunner` or `BaseRunResult`

No test coverage for the new base classes. Key scenarios to test:
- `BaseRunResult` dataclass construction (positional + kw_only)
- Inheritance ordering (child required fields before parent default)
- `_base_to_dict()` serialization
- `get_performance_metrics()` returns `n_mss=None`
- `BaseRunner.cleanup()` is idempotent

### 7. `tracemalloc.start()`/`stop()` not guarded for nesting

**Files:** `congen_runner.py`, `interactive_runner.py`

Both runners call `tracemalloc.start()` at the beginning of `run()` and `tracemalloc.stop()` in `finally`. If `tracemalloc` is already running (e.g., called from a profiling wrapper or nested usage), `start()` increments a counter but `stop()` only decrements it -- the peak memory may be inaccurate because it includes allocations from outside the run.

Low-risk in current usage patterns, but worth a comment noting this assumption.

### 8. Oracle `use_incremental=False` hardcoded in BaseRunner

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/base_runner.py`

```python
self.oracle = FeatureModelOracle(
    fm_path, solver_name=solver_name, use_incremental=False)
```

The oracle is always created with `use_incremental=False`, even though `ConGenRunner.__init__` accepts `use_incremental` parameter (which is used for the ConGen model, not the oracle). This is intentional for the oracle (which is used for membership queries, not constraint solving), but the dual meaning of `use_incremental` across model vs. oracle could confuse future maintainers. A brief comment would help:

```python
# Oracle uses non-incremental mode (membership queries only, not constraint solving)
```

---

## Low Priority

### 9. Lazy import in `BaseRunResult.get_performance_metrics()`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/base_runner.py`

```python
def get_performance_metrics(self):
    from conacq.eval.performance_metrics import PerformanceMetrics
    ...
```

Lazy import avoids circular dependency, which is fine. But it's called once per fold in the CV loop. The overhead is negligible (Python caches imports), but a module-level import with a `TYPE_CHECKING` guard would be cleaner if the circular dependency is resolvable.

### 10. `ConGenRunner.run()` missing early return for empty examples

Both `positive_examples` and `negative_examples` default to `None`, but the first line `len(positive_examples)` would raise `TypeError` if `None` is passed. The ConGen path always needs examples, so the method should validate inputs:

```python
if positive_examples is None or negative_examples is None:
    raise ValueError("ConGenRunner.run() requires positive and negative examples")
```

---

## Positive Observations

1. **`kw_only=True` on `profiler_data`** -- Clean solution for Python dataclass inheritance with defaults; avoids the "positional arg follows default" error that trips up many developers.

2. **Shared `_base_to_dict()`** -- DRY serialization pattern avoids field drift between runners.

3. **Oracle-per-runner lifecycle** -- Creating oracle once in `__init__()` and reusing across `run()` calls is correct and efficient for CV workloads (avoids re-parsing the FM file per fold).

4. **`model.prepare()` per run** -- Correctly resets accumulated state (task, description_provider) while keeping the expensive model/oracle intact.

5. **`getattr` for runner-specific fields** in CV loop -- `getattr(run_result, 'redundant_constraints', [])` and `getattr(run_result, 'n_mss', None)` elegantly handle the ConGen-specific fields without type checking.

6. **`PerformanceMetrics.n_mss` as `Optional[int] = None`** -- Clean handling of ConGen-specific metric; `aggregate_metrics` correctly filters `None` values.

7. **Good module docstrings** -- All files have clear docstrings explaining purpose and lifecycle.

---

## Recommended Actions (Prioritized)

1. **[CRITICAL]** Fix `n_bias_constraints` AttributeError in `apps/run_interactive.py`
2. **[HIGH]** Add `runner.cleanup()` in CV public functions via try/finally
3. **[HIGH]** Add comment or include `kb_clauses` in `_base_to_dict()`
4. **[MEDIUM]** Add `__enter__`/`__exit__` to `BaseRunner` for context manager support
5. **[MEDIUM]** Add basic tests for `BaseRunner`/`BaseRunResult`
6. **[MEDIUM]** Add input validation to `ConGenRunner.run()` for None examples
7. **[LOW]** Document `use_incremental=False` rationale in BaseRunner
8. **[LOW]** Document LSP deviation in `InteractiveRunner.run()` signature

---

## Metrics

- **Type Coverage:** Good -- type hints on all public methods, `Optional` used correctly
- **Test Coverage:** No direct tests for base classes; covered indirectly through subclass usage
- **Linting Issues:** 1 (AttributeError: `n_bias_constraints`)

---

## Unresolved Questions

1. Is `kb_clauses` intentionally excluded from `to_dict()` serialization? If so, should it be documented? If not, it's missing from both subclass `to_dict()` methods.
2. Should `BaseRunner` enforce `cleanup()` via context manager protocol, or keep it manual for backward compat with existing app scripts?
3. The CV functions create and discard runners without cleanup. Is this acceptable given Python GC will eventually call `__del__` on the oracle? (Note: `FeatureModelOracle.__del__` does call `self.cleanup()`, so resources will eventually be freed, but timing is non-deterministic.)
