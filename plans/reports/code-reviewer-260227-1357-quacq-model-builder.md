# Code Review: QuAcqModelBuilder Feature

**Date**: 2026-02-27
**Reviewer**: code-reviewer
**ID**: a837cef95ed9c6ffa

---

## Code Review Summary

### Scope
- **Files**: 7 (1 new, 6 modified)
  - `conacq/algorithms/quacq/quacq_model_builder.py` (NEW, 74 lines)
  - `conacq/algorithms/quacq/quacq_model.py` (modified)
  - `conacq/algorithms/quacq/__init__.py` (modified)
  - `conacq/algorithms/__init__.py` (modified)
  - `conacq/algorithms/acqmss/__init__.py` (modified)
  - `conacq/runners/quacq_runner.py` (modified)
  - `tests/test_quacq.py` (modified)
- **LOC changed**: ~100 net
- **Focus**: Builder pattern, runner lifecycle, consistency with ConGenModelBuilder

### Overall Assessment

The QuAcqModelBuilder is clean, well-structured, and correctly mirrors the ConGenModelBuilder API. The builder itself is sound. However, the runner integration has two bugs (one critical, one high) and a performance issue.

---

## Critical Issues

### 1. [BUG] Shuffle bias is a no-op in QuAcqRunner (quacq_runner.py:160-163)

**Problem**: The shuffle code converts a `set` to a sorted list, shuffles it, then converts back to `set()` -- which discards the shuffled ordering entirely. The shuffle has zero effect on iteration order.

```python
# quacq_runner.py lines 160-163
keys = sorted(task.bias)          # list in sorted order
random.Random(shuffle_seed).shuffle(keys)  # shuffled list
task.bias = set(keys)             # BUG: set discards order
```

**Impact**: Cross-validation experiments using `shuffle_seed` for bias ordering reproducibility will silently produce identical results regardless of seed. This undermines experimental reproducibility for QuAcq CV runs.

**Comparison**: ConGenRunner shuffles `constraint_map` (an ordered dict), which correctly affects iteration order:
```python
# congen_runner.py lines 155-158 (correct)
keys = list(self._original_bias_constraint_order)
random.Random(shuffle_seed).shuffle(keys)
self.model.constraint_map = {k: self.model.constraint_map[k] for k in keys}
```

**Fix**: QuAcqTask.bias is `Set[int]` by design (O(1) removal). To control iteration order, the shuffle must be applied at the point where bias is iterated (e.g., in QueryGenerator or QuAcq), or the model's `constraint_map` should be shuffled similarly to ConGenRunner. The simplest fix that preserves the rebuild-per-run pattern:

```python
if shuffle_seed is not None:
    keys = sorted(model.constraint_map.keys())
    random.Random(shuffle_seed).shuffle(keys)
    model.constraint_map = {k: model.constraint_map[k] for k in keys}
    logging.debug('Shuffled bias with seed=%d', shuffle_seed)
```

This requires confirming that QuAcq/QueryGenerator iterate `constraint_map` or derive iteration order from it. Otherwise, QuAcqTask needs a `bias_order: List[int]` field.

---

## High Priority

### 2. [BUG] UnboundLocalError on exception in QuAcqRunner.run() (quacq_runner.py:144-213)

**Problem**: If an exception occurs inside the `try` block before `model`, `result`, `kb_clauses`, `bg_clauses`, `profiler_snapshot`, or `consistency_checks` are assigned, the `finally` block runs and then execution continues to lines 195-213 which reference those unbound variables, causing `UnboundLocalError`.

```python
try:
    # If BiasIO.load_from_json() raises here...
    model = (QuAcqModelBuilder ...)  # never assigned
    ...
    result = ...                      # never assigned
    kb_clauses = ...                  # never assigned
finally:
    end_time = time.perf_counter()
    ...
    tracemalloc.stop()

# These will crash with UnboundLocalError:
run_result = QuAcqRunResult(
    kb_constraints=result.kb_constraints,  # UnboundLocalError
    kb_clauses=kb_clauses,                 # UnboundLocalError
    ...
)
```

**Impact**: Real errors (bad file path, corrupt bias JSON) are masked by a confusing `UnboundLocalError` instead of the original exception. This makes debugging harder.

**Comparison**: ConGenRunner uses a `with profiler_session` context and `try/finally` only around the inner section, so the result construction is inside the `with` block (lines 215-235), avoiding this issue.

**Fix**: Move the `QuAcqRunResult` construction inside the `try` block (after the `with profiler_session` closes), or restructure to match ConGenRunner's pattern:

```python
with profiler_session(ProfilerPreset.BENCHMARK) as profiler:
    tracemalloc.start()
    start_time = time.perf_counter()
    try:
        model = ...
        ...
    finally:
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    runtime_ms = (end_time - start_time) * 1000
    memory_peak_mb = peak / (1024 * 1024)

    run_result = QuAcqRunResult(...)
    return run_result
```

### 3. [PERF] feature_ids property reloads bias from disk on every call (quacq_runner.py:90-95)

**Problem**: `QuAcqRunner.feature_ids` property loads bias from JSON on every access:

```python
@property
def feature_ids(self) -> Dict[str, int]:
    from conacq.bias import BiasIO
    bias = BiasIO.load_from_json(self.bias_path)
    return bias.feature_ids
```

**Comparison**: ConGenRunner caches the model and delegates to `self.model.variables` (no file I/O):

```python
@property
def feature_ids(self) -> Dict[str, int]:
    return self.model.variables
```

**Impact**: Called by `cross_validation.py:165` at CV start. Currently only called once per CV run, so impact is low. But the pattern is wrong -- property access should not trigger file I/O.

**Fix**: Cache the bias feature_ids in `__init__` or lazily:

```python
def __init__(self, ...):
    ...
    from conacq.bias import BiasIO
    bias = BiasIO.load_from_json(bias_path)
    self._feature_ids = bias.feature_ids

@property
def feature_ids(self) -> Dict[str, int]:
    return self._feature_ids
```

---

## Medium Priority

### 4. [CONSISTENCY] use_incremental: public attr vs private attr

**Observation**: QuAcqModel uses a **public** attribute `self.use_incremental` (line 44), and QuAcqModelBuilder sets it as `model.use_incremental = self._use_incremental` (line 63). ConGenModel uses a **private** attribute `self._use_incremental` with a `@property` getter, and ConGenModelBuilder sets it as `model._use_incremental = self._use_incremental` (line 112).

Both satisfy the `CheckerModel` protocol (`use_incremental: bool`). The `Protocol` attribute check works with both bare attributes and properties. However, the inconsistency is notable:

| Model | Attribute | Builder sets |
|-------|-----------|-------------|
| ConGenModel | `_use_incremental` (private) + `@property use_incremental` | `model._use_incremental` |
| QuAcqModel | `use_incremental` (public) | `model.use_incremental` |

**Impact**: Not a bug -- both work. QuAcqModel's approach is actually simpler and arguably better. But worth noting for consistency review.

### 5. [STYLE] Import placement inside run() method (quacq_runner.py:145-152)

**Problem**: Imports for `QuAcq`, `profiler_session`, `ProfilerPreset`, and `QuAcqModelBuilder` are inside the `run()` method body:

```python
def run(self, ...):
    ...
    try:
        from conacq.algorithms.quacq.quacq import QuAcq
        from explanation.operations.algorithms.profiler import (
            profiler_session, ProfilerPreset)

        with profiler_session(...) as profiler:
            from conacq.algorithms.quacq.quacq_model_builder import QuAcqModelBuilder
```

These are all project-internal modules with no circular dependency risk. ConGenRunner imports at module level (lines 1-21).

**Fix**: Move imports to module level for consistency with ConGenRunner.

### 6. [TEST] No dedicated builder test class

**Observation**: Tests use `QuAcqModelBuilder` in the `interactive_model` fixture and indirectly test it via `TestQuAcqModel`. There is no dedicated `TestQuAcqModelBuilder` class that tests:
- Missing bias path raises `ValueError`
- Missing oracle raises `ValueError`
- `use_incremental(False)` propagates to model
- Builder reuse (calling `build()` twice)

**Impact**: Low -- the builder is simple and well-covered through fixture usage. But explicit validation tests catch regressions.

---

## Low Priority

### 7. [STYLE] Redundant `kb_constraints=` field (quacq_runner.py:196)

The `kb_constraints` field in `QuAcqRunResult.__init__` is set to `result.kb_constraints` which is a `List[str]` default `[]` on `BaseRunResult`. In ConGenRunner, `kb_names` is computed from `model.resolve_result()`. In QuAcqRunner, it comes from the `QuAcqResult` directly. This is fine but worth noting the different resolution paths.

### 8. [DOC] quacq_model.py docstring references builder but no import shown

```python
# quacq_model.py lines 28-33
"""
Usage:
    oracle = FeatureModelOracle('data/fms/model.uvl')
    model = (QuAcqModelBuilder
             .from_bias('data/bias/model.json')
             ...
```

Minor: docstring references `QuAcqModelBuilder` but the import is not shown. Could add `from conacq.algorithms.quacq import QuAcqModelBuilder` in the docstring example.

---

## Positive Observations

1. **Clean builder pattern**: QuAcqModelBuilder is focused and minimal (74 lines). Correctly omits examples support that QuAcq does not need.
2. **Proper validation**: `_validate()` checks both `bias_path` and `oracle` -- good fail-fast behavior.
3. **Always auto-prepare**: Unlike ConGenModelBuilder which has conditional prepare, QuAcqModelBuilder always prepares. This is correct -- QuAcq always needs oracle data for task setup.
4. **Test fixtures updated correctly**: `interactive_model` and `prepared_model` fixtures properly use the builder pattern.
5. **Export chain complete**: `quacq/__init__.py` -> `algorithms/__init__.py` -> `acqmss/__init__.py` all export `QuAcqModelBuilder`.
6. **Docstring on __init__.py** updated with builder usage example.
7. **`from_bias()` correctly removed** from `QuAcqModel` -- no stale references found in codebase.

---

## Recommended Actions

| Priority | Action | File |
|----------|--------|------|
| **Critical** | Fix shuffle no-op (set discards order) | `quacq_runner.py:160-163` |
| **High** | Fix UnboundLocalError on exception path | `quacq_runner.py:144-213` |
| **High** | Cache feature_ids, remove per-call file I/O | `quacq_runner.py:90-95` |
| Medium | Consider aligning use_incremental pattern | `quacq_model.py:44` |
| Medium | Move imports to module level | `quacq_runner.py:145-152` |
| Low | Add dedicated builder validation tests | `tests/test_quacq.py` |

---

## Unresolved Questions

1. **Shuffle intent for QuAcq**: Does QuAcq's query generation iterate `task.bias` in insertion order? If bias is a `set`, iteration order is implementation-defined. Need to trace `QueryGenerator.generate()` to confirm where bias iteration order matters before choosing the right shuffle fix.
2. **Builder reuse**: Is `QuAcqModelBuilder` intended to be reusable (call `build()` multiple times)? Currently `build()` can be called multiple times, and the runner creates a fresh builder each `run()`. This is fine, but the builder stores no mutable state from `build()`, so reuse is safe.
3. **`kb_constraints` field defaults**: `BaseRunResult.kb_constraints` is a required positional arg, but `QuAcqRunResult` inherits it. The runner passes `result.kb_constraints` from `QuAcqResult`. If `QuAcqResult.kb_constraints` is empty (e.g., no constraints learned), the field is `[]` which is correct. No issue, just confirming.
