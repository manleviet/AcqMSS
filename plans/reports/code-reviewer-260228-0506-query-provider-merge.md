# Code Review: QueryProvider Merge Refactoring

**Date**: 2026-02-28
**Commit**: 6deb34b
**Reviewer**: code-reviewer

---

## Code Review Summary

### Scope
- **Files changed**: 15 (1 new, 2 deleted, 12 modified)
- **LOC delta**: +410 / -430 (net -20)
- **Focus**: Merge ExampleProvider + QueryGenerator into unified QueryProvider

### Overall Assessment

Clean, well-executed merge. The two-class split (ExampleProvider for pool iteration, QueryGenerator for SAT queries) is unified into a single QueryProvider that handles both strategies with paper-aligned pool filtering. The refactoring simplifies the DI surface (2 params -> 1), eliminates the `_narrow_with_pool` code path from FindC, and correctly delegates Part 4 assignment logic to `QuAcqModel.config_to_assumptions()`.

**Verdict: APPROVE with minor doc hygiene items.**

---

### Critical Issues

None.

---

### High Priority

**H1. Mutable default argument `pool=None` is safe but type-incorrect**

File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/example_generators/query_provider.py`, line 35

```python
def __init__(self, solver_name: str = 'glucose4',
             pool: List[Dict[str, bool]] = None,
             seed: int = None,
             profiler_instance: AbstractProfiler = None) -> None:
```

`pool` is typed `List[...]` but defaults to `None`. Should be `Optional[List[...]]` for type correctness. Same for `seed: int = None` (should be `Optional[int]`) and `profiler_instance`. This will fail `mypy --strict`.

**Fix**: Change signatures to use `Optional[...]`:
```python
def __init__(self, solver_name: str = 'glucose4',
             pool: Optional[List[Dict[str, bool]]] = None,
             seed: Optional[int] = None,
             profiler_instance: Optional[AbstractProfiler] = None) -> None:
```

**H2. `generate_with_priority` is dead code**

File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/example_generators/query_provider.py`, lines 173-201

`generate_with_priority()` is carried over from the old `QueryGenerator` but has **zero callers** in the codebase. It also duplicates the SAT loop from `generate_from_sat()` (minus the profiler decorators). Per YAGNI, consider removing it -- or at minimum adding a TODO if it is planned for future use.

---

### Medium Priority

**M1. Stale documentation references (4 files)**

Several docs still reference `QueryGenerator` and `ExampleProvider` as if they exist:

1. `/Users/manleviet/Development/GitHub/AcqMSS/docs/quacq.md` -- Lines 158, 277-278, 298, 308-310, 336-345 still show old class names and import patterns
2. `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` -- Lines 62, 92, 100, 116-117, 168, 171, 669, 786 reference deleted classes
3. `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` -- Lines 50, 52, 86, 91-92 reference deleted files/classes
4. `/Users/manleviet/Development/GitHub/AcqMSS/README.md` -- Line 124 mentions `QueryGenerator, ExampleProvider`

**Impact**: Developers following doc examples will hit ImportErrors. Should be updated to reflect `QueryProvider`.

**M2. FindC pool-narrowing removal -- behavioral change**

File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/findc.py`

The `_narrow_with_pool` function was removed entirely from FindC. Previously in example modes, FindC would use pool examples to narrow candidate constraints before falling back to DiscriminatingGenerator. Now FindC only uses DiscriminatingGenerator (or returns first candidate).

This is a **correct simplification** -- pool filtering now happens at the QueryProvider level (in `generate_from_pool()`) with paper-aligned conditions. FindC's `_narrow_with_pool` was doing unvalidated oracle-based narrowing that mixed concerns. The change is sound, but worth noting for evaluation metric comparison: example-mode FindC may use more SAT queries and fewer pool queries than before.

**M3. `example_only` mode lost validation for pool existence**

File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py`, `_validate_mode()` (lines 276-286)

Old code validated that `example_only` and `example_first` modes require `example_provider`. New code only checks `query_provider is not None`, which passes even if `QueryProvider` was created without a pool. Running `example_only` with an empty pool will immediately return `pool_exhausted` / `(None, None)` and converge with `convergence_reason='pool_exhausted'`.

This is technically correct (not a crash) but could silently produce empty results. Consider adding a warning log or validation:

```python
if mode == 'example_only' and self.query_provider.pool_exhausted:
    raise ValueError("example_only mode requires QueryProvider with a pool")
```

---

### Low Priority

**L1. `generate_from_pool` formula recomputed every call**

File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/example_generators/query_provider.py`, line 78

```python
formula = kb_clauses + bg_clauses
```

This creates a new list on every call. In the main loop, `kb_clauses` changes as the KB grows, so caching is not trivial. Current approach is correct; just noting it as a micro-optimization opportunity if pool sizes become large.

**L2. Solver lifecycle in `_satisfies_formula`**

File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/example_generators/query_provider.py`, lines 99-108

A new solver is created and deleted per pool example. For large pools this is suboptimal. An incremental solver that persists across the while-loop in `generate_from_pool` would be faster. However, since pool examples are already filtered (checked one at a time), this is unlikely to be a bottleneck in practice.

**L3. `_pool_index` state is never resettable**

File: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/example_generators/query_provider.py`

Once the pool is exhausted, there's no way to reset the index or provide a new pool. This matches the old `ExampleProvider` behavior (one-shot consumption). Fine for current usage; just noting it is a design choice.

---

### Edge Cases Found

1. **Empty pool + `example_only` mode**: Converges immediately with `pool_exhausted`. No crash but no learning either. See M3 above.

2. **Pool example with features not in `feature_ids`**: `config_to_assumptions()` (from sat_utils) silently skips unknown features. Pool examples generated from a different FM would lose variables. Current behavior is safe (partial assumption list) but could miss violations.

3. **`self.model` is `None` when `root_assumption` is passed**: The pruning guard `if self.model and root_assumption is not None` correctly handles this -- falls through to legacy pruning. No issue.

4. **`config_to_assumptions` in `QuAcqModel` vs `sat_utils`**: Two different functions with the same name exist. `QuAcqModel.config_to_assumptions()` uses Part 4 assignment assumption IDs (pos/neg maps). `sat_utils.config_to_assumptions()` converts feature name -> SAT variable literal. Different semantics, different callers. No collision, but naming is ambiguous. Consider renaming the model method to `config_to_assignment_assumptions()` for clarity.

---

### Positive Observations

1. **Paper-aligned pool filtering**: `generate_from_pool()` now properly checks both conditions (satisfies C_L+BG AND violates >= 1 c in B). The old ExampleProvider was a blind iterator with no filtering.

2. **Clean DI simplification**: Reducing from 2 injected params to 1 removes ambiguity about which modes need which provider.

3. **`QuAcqModel.config_to_assumptions()` delegation**: Moving Part 4 assignment lookup into the model is correct -- keeps domain knowledge out of the algorithm.

4. **Proper solver cleanup**: All SAT solver usage follows try/finally pattern with `solver.delete()`.

5. **Profiler decorators preserved**: `@measure_time` and `@count_calls` carried over correctly to new methods.

6. **Test coverage good**: New `TestQueryProviderPoolFiltering` class, updated factory tests, mode validation tests all cover the refactored paths.

---

### Recommended Actions

1. **Fix type hints** in `QueryProvider.__init__()` -- use `Optional[...]` (H1)
2. **Remove `generate_with_priority()`** or add caller if planned (H2, YAGNI)
3. **Update docs** -- 4 files still reference deleted classes (M1)
4. **Add validation** for `example_only` with empty pool (M3, optional)

### Metrics
- **Type Coverage**: Medium (Optional types missing in QueryProvider signature)
- **Test Coverage**: 359/359 passing; pool filtering, factory, mode validation all covered
- **Linting Issues**: ~4 (Optional type hints)

### Unresolved Questions

1. Was `_narrow_with_pool` removal in FindC validated against evaluation metrics? The behavioral change means FindC in example modes only uses DiscriminatingGenerator now -- potentially different query counts.
2. Is `generate_with_priority()` planned for future use (e.g., heuristic ordering)? If not, recommend removal per YAGNI.
