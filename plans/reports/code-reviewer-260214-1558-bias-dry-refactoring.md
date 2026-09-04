# Code Review: Bias Class DRY Refactoring

## Scope
- Files: 5 modified (`data_structures.py`, `congen_model_builder.py`, `learner.py`, `test_congen.py`, `test_interactive.py`)
- LOC: ~120 added to Bias, ~80 removed from callers
- Focus: DRY refactoring -- centralize `{c.id: c.clauses}` and `{f.name: f.id}` into Bias class

## Overall Assessment

The DRY intent is correct and the new Bias methods are well-designed. However, there are **2 critical bugs** in `ConGenModelBuilder` that will cause runtime failures, **1 behavioral difference** in `_build_task_from_bias`, and a few medium-priority issues.

---

## Critical Issues

### C1. `ConGenModelBuilder` references undefined attributes `_solver_name` and `_profiler`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model_builder.py`, line 133

```python
model.prepare(solver_name=self._solver_name, profiler=self._profiler)
```

Neither `_solver_name` nor `_profiler` are defined in `__init__()` or anywhere in the builder. This will raise `AttributeError` at runtime whenever examples are provided.

**Fix:** Add these fields to `__init__()` and add corresponding builder methods:

```python
# In __init__():
self._solver_name: str = 'glucose4'
self._profiler: Optional[AbstractProfiler] = None

# Add methods:
def with_solver(self, solver_name: str) -> 'ConGenModelBuilder':
    self._solver_name = solver_name
    return self

def with_profiler(self, profiler: AbstractProfiler) -> 'ConGenModelBuilder':
    self._profiler = profiler
    return self
```

### C2. Callers already use `.with_profiler()` and `.with_solver()` -- methods that don't exist

**Files:**
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py` line 56: `.with_profiler(profiler)`
- `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_congen.py` lines 109-110: `.with_solver(solver_name)` + `.with_profiler(profiler)`
- `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/eval/congen_runner.py` line 116: `.with_solver(solver_name)`

These calls will fail with `AttributeError`. The tester report (`tester-260214-1557-test-results.md`) already flagged these failures.

---

## High Priority

### H1. Behavioral difference in `_build_task_from_bias` tseitin_start computation

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/interactive/learner.py`, line 164

**Before (original code):**
```python
tseitin_var = max(f.id for f in bias.features) + 1
```

**After (refactored code):**
```python
tseitin_start = max(feature_ids.values()) + 1
```

In `_build_task_from_bias`, `feature_ids` comes from `oracle.get_feature_ids()`, **not from `bias.features`**. If the oracle and bias have different feature ID ranges (which is checked by `TestOracleFeatureIds` but still a semantic difference), the tseitin starting point would differ.

The `from_bias` method correctly switched to `bias.max_variable_id + 1`, which also considers constraint clause literals (a stricter, safer computation). But `_build_task_from_bias` uses `max(feature_ids.values()) + 1` which only considers feature IDs from the oracle -- not constraint clause literals.

**Impact:** If any constraint contains a literal with absolute value > max feature ID, the tseitin variable could collide with existing literals.

**Fix:** Use `bias.max_variable_id + 1` in `_build_task_from_bias` as well:

```python
tseitin_start = bias.max_variable_id + 1
```

### H2. `_load_model` method is dead code

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model_builder.py`, lines 159-174

The `_load_model` method loads a `FeatureModel` via FlamaPy readers but is never called. The `build()` method uses `FeatureModelOracle(self._fm_path)` instead.

**Fix:** Remove `_load_model` and the `FeatureModel` import (line 9).

### H3. Missing newline at end of file

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model_builder.py`, line 175

The diff shows `\ No newline at end of file`. Add trailing newline.

---

## Medium Priority

### M1. `feature_ids` and `id_to_feature` properties re-create dicts on every call

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/bias/data_structures.py`, lines 95-103

These properties create new dict objects on every access. For hot-path usage (e.g., inside loops or repeated calls), this is wasteful.

**Options:**
- (a) Cache with `@functools.cached_property` (safe since `Bias` is a `@dataclass` with list fields -- effectively mutable, so `cached_property` is fine as long as constraints/features don't change after construction)
- (b) Keep as-is if calls are infrequent (acceptable for now)

**Verdict:** Low risk currently, but worth noting for future optimization.

### M2. `max_variable_id` returns 0 for empty bias

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/bias/data_structures.py`, line 112

```python
max_var = max((f.id for f in self.features), default=0)
```

If `features` is empty, `max_var` starts at 0. Then if `constraints` is also empty, `max_variable_id` returns 0. This means `next_tseitin_var` = 1, which could conflict with actual variable IDs in other systems. Not a practical concern (empty bias is degenerate) but worth a docstring note.

### M3. Stale docstring example in `from_files`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/interactive/learner.py`, line 91

```python
>>> learner = InteractiveLearner.from_bias_and_fm_fide(
```

The method is `from_files`, not `from_bias_and_fm_fide`. The example in the docstring references a wrong method name.

### M4. `to_constraint_map` could be a property for consistency

`feature_ids` and `id_to_feature` are `@property`, but `to_constraint_map()` is a regular method. The `to_` prefix convention suggests transformation, which is fine as a method. However, for consistency within the class, consider either making all of them properties or all methods. Minor style point.

---

## Low Priority

### L1. Unused import `Tuple` will become available only after adding it

The `Tuple` import was added to `data_structures.py` -- correct usage in `to_constraint_maps_with_negation` return type.

### L2. Lazy import in `to_constraint_maps_with_negation`

The `negate_cnf_tseitin` import inside the method body avoids circular imports. This is consistent with patterns used elsewhere in the codebase (e.g., `ConGenModel.prepare()`). Acceptable.

---

## Positive Observations

1. **Clean DRY extraction** -- The 5 new methods/properties on `Bias` are well-named and have clear docstrings
2. **`to_constraint_maps_with_negation` returns the next tseitin var** -- callers don't need to track state manually
3. **`max_variable_id` scans both features and constraint literals** -- safer than the old `max(f.id)` pattern
4. **Import cleanup** in `learner.py` -- removed unused `negate_cnf_tseitin` import
5. **test_interactive.py change is minimal and correct** -- `bias.to_constraint_map()` replaces inline dict comprehension with identical semantics

## Behavioral Equivalence Verification

| Call site | Before | After | Equivalent? |
|-----------|--------|-------|-------------|
| `learner.from_bias` feature_ids | `{f.name: f.id for f in bias.features}` | `bias.feature_ids` | Yes |
| `learner.from_bias` id_to_feature | `{f.id: f.name for f in bias.features}` | `bias.id_to_feature` | Yes |
| `learner.from_bias` tseitin_start | `max(f.id for f in bias.features) + 1` | `bias.max_variable_id + 1` | **Safer** (considers clause literals) |
| `learner._build_task_from_bias` tseitin | `max(feature_ids.values()) + 1` | `max(feature_ids.values()) + 1` | Unchanged (but see H1) |
| `test_interactive` constraint_map | inline `{c.id: c.clauses}` | `bias.to_constraint_map()` | Yes |
| `test_congen` feature_ids | `{f.name: f.id for f in bias.features}` | `bias.feature_ids` | Yes |
| `congen_model_builder` constraint_map | N/A (new file) | `bias.to_constraint_map()` | N/A |
| `congen_model_builder` max_variable_id | N/A (new file) | `bias.max_variable_id` | N/A |

---

## Recommended Actions (Priority Order)

1. **[CRITICAL]** Add `_solver_name`, `_profiler` fields + `with_solver()`, `with_profiler()` methods to `ConGenModelBuilder`
2. **[HIGH]** Fix `_build_task_from_bias` to use `bias.max_variable_id + 1` for tseitin_start
3. **[HIGH]** Remove dead `_load_model` method and unused `FeatureModel` import from builder
4. **[HIGH]** Add trailing newline to `congen_model_builder.py`
5. **[MEDIUM]** Fix docstring example in `learner.py` `from_files` method
6. **[LOW]** Consider `@cached_property` for `feature_ids` and `id_to_feature` if perf matters

## Metrics
- Type Coverage: Good -- all new methods have type hints
- Test Coverage: Existing tests use the new methods; no new unit tests for Bias methods themselves
- Linting Issues: 1 (missing EOF newline)

## Unresolved Questions

1. Should `Bias` have unit tests for the new methods (`feature_ids`, `id_to_feature`, `to_constraint_map`, `max_variable_id`, `to_constraint_maps_with_negation`)? Currently only tested indirectly through integration tests.
2. Should `to_constraint_map()` be a `@property` for consistency with `feature_ids`/`id_to_feature`?
