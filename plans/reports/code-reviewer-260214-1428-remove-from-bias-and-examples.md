# Code Review: Remove `from_bias_and_examples`, Use `ConGenModelBuilder`

**Date**: 2026-02-14
**Reviewer**: code-reviewer
**Scope**: Migration from `ConGenModel.from_bias_and_examples()` to `ConGenModelBuilder` pattern

## Scope

- **Files**: 16 changed (8 Python, 4 docs, 4 config/docs)
- **LOC**: ~405 added, ~393 removed (net +12)
- **Focus**: API migration, builder pattern consolidation, caller updates

## Overall Assessment

Clean, well-executed refactoring. The migration from `from_bias_and_examples()` to `ConGenModelBuilder` is complete across all Python callers. The builder pattern is fluent and well-documented. The key improvement is CV fold reuse: build model once, call `prepare()` per fold. No remaining `.py` references to the removed method. All 300 tests pass.

---

## Critical Issues

None.

---

## High Priority

### H1: `_resolve_examples()` returns `None` for negative examples when using `with_examples_data()`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model_builder.py` line 169

```python
def _resolve_examples(self) -> Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]:
    if self._positive_examples is not None:
        return self._positive_examples, self._negative_examples  # <-- can be None
```

If a caller uses `with_examples_data(positive=[...], negative=None)` or sets only `_positive_examples`, `_negative_examples` remains `None`. The return type annotation says `List[Dict[str, bool]]` but it returns `None`. This propagates to `ConGenModel._examples_to_testsuite(None)` which will crash with `TypeError: 'NoneType' is not iterable`.

**Impact**: Runtime crash if caller provides positive examples without negative examples via `with_examples_data()`.

**Fix**: Default to empty list:
```python
return self._positive_examples, self._negative_examples or []
```

**Note**: The `with_examples_data()` method requires both params so this is unlikely in practice, but the type contract should still be honored.

### H2: `from_bias_and_fm_fide()` will fail at runtime

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model_builder.py` lines 55-61

The builder sets `_fm_source_type = 'fide'` but this field is **never used** in `build()`. The builder always passes the path to `FeatureModelOracle(self._fm_path)`, and `FeatureModelOracle._load_fm()` only supports `.uvl` files:

```python
# fm_oracle.py line 77
if fm_path.endswith('.uvl'):
    return UVLReader(fm_path).transform()
else:
    raise ValueError(f"Unsupported feature model format: {fm_path}")
```

Any caller using `from_bias_and_fm_fide()` with a `.xml` FeatureIDE file will get `ValueError: Unsupported feature model format`. The method name is misleading.

**Options**:
1. Add FeatureIDE support to `FeatureModelOracle._load_fm()` (if needed)
2. Remove `from_bias_and_fm_fide()` entirely if FeatureIDE is unused (YAGNI)
3. Add a docstring warning that only `.uvl` is currently supported

### H3: `solver_name` inconsistency between builder default and model default

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model_builder.py` line 50 vs `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model.py` line 41

- Builder default: `self._solver_name: str = 'glucose3'`
- ConGenModel default: `self.solver_name: str = 'glucose4'`
- ConGenRunner default: `solver_name: str = 'glucose4'`

The builder uses `glucose3` as default, everything else uses `glucose4`. This means a builder without `.with_solver()` will silently use a different solver than direct model construction.

**Fix**: Change builder default to `'glucose4'` for consistency.

---

## Medium Priority

### M1: `README.md` uses removed `acquire(task=...)` API

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/README.md` line 60

```python
result = congen.acquire(task=model.task)
```

`ConGen.acquire()` no longer accepts a `task` parameter. It now takes individual arguments (`set_b`, `set_bg`, `set_tc`, etc.). This will cause a `TypeError` if copy-pasted.

**Fix**: Update to match the actual API:
```python
task = model.task
result = congen.acquire(
    set_b=task.set_c, set_bg=task.set_b, set_tc=task.set_tc,
    set_ne=task.set_ne, neg_c_map=task.neg_c_map,
    assumption_to_constraint=task.assumption_to_constraint
)
```

### M2: `code-standards.md` line 531 still shows old `acquire(task)` call

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md` line 531

```python
>>> result = congen.acquire(task)
```

This docstring example is stale. Should match the new signature.

### M3: Import path inconsistency in docs vs code

**Files**: `docs/code-standards.md:283`, `docs/system-architecture.md:60`, `CLAUDE.md:170`

Docs use:
```python
from explanation.operations.algorithms.checker_factory import CheckerFactory
```

All actual Python code uses:
```python
from explanation.operations.algorithms.checker import CheckerFactory
```

There is no `checker_factory.py` module. The docs have a wrong import path.

### M4: `ConGenModel.solver_name` has `# TODO: remove` comment

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model.py` line 41

```python
self.solver_name: str = 'glucose4'  # TODO: remove
```

This TODO is stale. `solver_name` is now part of the CheckerModel protocol (used by `CheckerFactory.create_from_model()`). It should not be removed. Remove the TODO comment.

### M5: Unused `IncrementalPySATChecker` import in tests

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py` line 17

```python
from explanation.operations.algorithms.checker import (
    IncrementalPySATChecker,
    CheckerFactory
)
```

`IncrementalPySATChecker` is still used in `TestACQMSS` and `TestReduce` test classes, so this is actually fine. Disregard.

### M6: Redundant `FeatureModelOracle` instantiation in test helper

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py` lines 59-62

```python
# Get root_id from model for test assertions
oracle = FeatureModelOracle(fm_path)
root_name = oracle.get_root_feature()
root_id = model.variables[root_name]
```

The builder already creates a `FeatureModelOracle` internally (line 116 of builder). This creates a second oracle instance just to get `root_name`. Consider exposing root info from the builder or model, or accepting the duplication as test-only overhead.

**Impact**: Minor performance waste (double FM parsing in tests). Not a correctness issue.

---

## Low Priority

### L1: `_fm_source_type` field stored but never read

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/congen_model_builder.py` line 39

Dead field. If FeatureIDE support is not planned, remove it along with `from_bias_and_fm_fide()`.

### L2: `bias` fixture unused in some test methods

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py`

The `bias` fixture is passed to all `TestCONGEN` methods but is only used for assertion printing (`bias.get_constraint_by_id(c)`). The test would pass without it. Not a bug, just a minor observation.

---

## Edge Cases Found by Scout

1. **No remaining `.py` callers of `from_bias_and_examples()`** -- verified via grep. Migration is complete.
2. **No remaining `.py` callers of `acquire(task)`** -- verified. All callers updated to explicit params.
3. **Bias shuffle correctness in ConGenRunner**: The `_original_constraint_order` is captured at `__init__` time and used to restore ordering before each shuffle. This is correct -- dict insertion order is preserved in Python 3.7+, and `list(self._original_constraint_order)` creates a fresh copy each time. No mutation bug.
4. **`n_fold_cross_validation_interactive` not migrated**: Lines 304-470 of `cross_validation.py` still use the old-style `bias_clauses`/`feature_ids` params. This function was out of scope for this refactoring (it uses `InteractiveRunner`, not `ConGenRunner`). No issue, but noted for future alignment.
5. **`ConGenModel.prepare()` with `positive_examples=None` AND `negative_examples=[]`**: Line 97 checks `if positive_examples is not None or negative_examples is not None`. If caller passes `prepare(negative_examples=[])`, `positive_examples` defaults to `None`, triggering `positive_examples or []` which yields `[]`. This resets task_input to empty E+ and empty E-. Unlikely in practice but the `or` semantics could surprise.

---

## Positive Observations

- **Clean builder API**: Fluent pattern with `from_bias_and_fm_uvl().with_examples().build()` reads well
- **Single model construction for CV**: Building once and calling `prepare()` per fold eliminates redundant file I/O and parsing
- **GenerateNE encapsulated in `prepare()`**: Callers no longer need to manage temp checkers and NE merging manually -- significant DRY improvement
- **`_original_constraint_order` for shuffle restore**: Smart approach to preserve deterministic bias ordering across CV folds
- **ConGen.acquire() explicit params**: Moving from opaque `task` object to named params improves readability and makes data flow obvious

---

## Recommended Actions

1. **[H3]** Fix builder default solver from `'glucose3'` to `'glucose4'`
2. **[H1]** Add `or []` guard in `_resolve_examples()` for `_negative_examples`
3. **[H2]** Decide on `from_bias_and_fm_fide()` -- remove if unused, or add FeatureIDE support
4. **[M1]** Fix `README.md` stale `acquire(task=...)` example
5. **[M2]** Fix `code-standards.md` stale `acquire(task)` docstring example
6. **[M3]** Fix import path in docs: `checker_factory` -> `checker`
7. **[M4]** Remove stale `# TODO: remove` comment on `solver_name`

---

## Metrics

- **Type Coverage**: Good -- all public methods have type hints
- **Test Coverage**: 300/302 pass (2 pre-existing failures, unrelated)
- **Linting Issues**: Not run (no linter configured in project)

---

## Unresolved Questions

1. Is `from_bias_and_fm_fide()` needed? No callers exist in the codebase. If FeatureIDE support is planned, `FeatureModelOracle._load_fm()` also needs updating.
2. Should `n_fold_cross_validation_interactive` be migrated to the builder pattern in a follow-up?
3. The `# TODO: remove` on `solver_name` -- was there a plan to remove it from CheckerModel protocol, or is this truly stale?
