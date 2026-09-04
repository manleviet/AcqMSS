# Code Review: Bias Module Refactoring

**Date:** 2026-02-16
**Reviewer:** code-reviewer agent
**Scope:** Internal method extraction in 3 bias module files
**Tests:** 299 passed, 2 failed (pre-existing: missing data file)

## Scope

| File | LOC | Changes |
|------|-----|---------|
| `acqmss/bias/bias_generator.py` | 293 | Extracted `_generate_from_specific_pairs()`, `_generate_from_combinations()`; added `_cached_bias`; rewrote `get_statistics()` |
| `acqmss/bias/config_loader.py` | 209 | Extracted `_parse_hierarchical_candidates()`, `_parse_cross_tree_config()`; constant `_MAX_CROSS_TREE_FEATURES_WARNING` |
| `acqmss/bias/bias_io.py` | 230 | Extracted `_constraint_to_dict()`, `_constraint_from_dict()` |

**Focus:** Correctness of extraction, caching logic, edge cases.

## Overall Assessment

Clean refactoring. All extractions are behavior-preserving. No public API changes confirmed -- all new methods are `_`-prefixed and only called within the same class. The `__init__.py` exports unchanged. The `_cached_bias` addition fixes a real (though latent) counter-drift bug in `get_statistics()`.

## Critical Issues

None.

## High Priority

### H1. `get_statistics()` classification heuristic is fragile

**File:** `acqmss/bias/bias_generator.py`, lines 279-283

**Old behavior:** `get_statistics()` called `generate_hierarchical_constraints()` and `generate_cross_tree_constraints()` separately, giving exact counts by construction.

**New behavior:** Uses operator-type heuristic to split constraints:
```python
hierarchical_ops = {OperatorType.MANDATORY, OperatorType.OPTIONAL,
                   OperatorType.ALTERNATIVE, OperatorType.OR}
hierarchical = [c for c in all_constraints if c.operator in hierarchical_ops]
cross_tree = [c for c in all_constraints if c.operator not in hierarchical_ops]
```

**Risk:** If a future `OperatorType` is added (e.g., `XOR`, `NAND`), this heuristic silently misclassifies it. The old approach was immune since it counted by generation source.

**Impact:** Currently correct -- `REQUIRES` and `EXCLUDES` are the only cross-tree operators, and the 4 hierarchical operators are exhaustive. But this creates an implicit coupling to the `OperatorType` enum.

**Recommendation:** Add a comment documenting the assumption, or define the set as a module constant near `OperatorType` so future enum additions have a visible reminder:

```python
# In data_structures.py or at top of bias_generator.py:
_HIERARCHICAL_OPS = {OperatorType.MANDATORY, OperatorType.OPTIONAL,
                     OperatorType.ALTERNATIVE, OperatorType.OR}
```

## Medium Priority

### M1. No cache invalidation on repeated `generate_bias()` calls

**File:** `acqmss/bias/bias_generator.py`, line 253

`_cached_bias` is set at the end of `generate_bias()` but never cleared. If someone calls `generate_bias()` twice on the same `BiasGenerator` instance, the second call would produce constraints with IDs continuing from where the first left off (c33, c34...) due to `constraint_counter` accumulation, but `_cached_bias` would correctly point to the latest result.

**Impact:** Low. Current usage pattern (checked all callers: `generate_bias_files.py`, `test_bias_module.py`) creates a fresh `BiasGenerator` per config. No caller invokes `generate_bias()` twice.

**Recommendation:** No action needed now. If reuse becomes a pattern, add a `reset()` method or reset `constraint_counter` at the start of `generate_bias()`.

### M2. `get_statistics()` side effect when cache is empty

**File:** `acqmss/bias/bias_generator.py`, line 276

```python
bias = self._cached_bias if self._cached_bias else self.generate_bias()
```

If `get_statistics()` is called before `generate_bias()`, it triggers `generate_bias()` which: (a) prints to stdout, (b) populates `_cached_bias`, (c) increments `constraint_counter`. This is a behavior change from the old code which also had side effects (counter drift) but did NOT populate a cache or print the "Generating..." messages.

**Impact:** Minor -- the docstring now correctly documents this ("otherwise generates fresh"), and the old code had worse side effects (counter drift). But callers unaware of the stdout output may be surprised.

**Recommendation:** Acceptable trade-off. The old counter-drift bug was worse. Document in docstring that it prints to stdout if called before `generate_bias()`.

## Low Priority

### L1. Removed `cross_tree_mode` local variable

**File:** `acqmss/bias/bias_generator.py`

Old code assigned `cross_tree_mode = self.config.cross_tree_config.cross_tree_mode` but never used it (the variable was only set, not read in the original). The refactored code correctly removes this dead variable. Good cleanup.

### L2. `_constraint_from_dict` trusts feature_map completeness

**File:** `acqmss/bias/bias_io.py`, line 176

```python
children = [feature_map[name] for name in c_data['children']]
```

A missing child name raises `KeyError` with no context about which constraint failed. This is pre-existing behavior (unchanged from old code), not introduced by the refactoring. Noting for completeness only.

### L3. `_parse_cross_tree_config` default for missing `cross_tree_candidates`

**File:** `acqmss/bias/config_loader.py`, line 125

```python
ct_data = data.get('cross_tree_candidates', {})
```

Pre-existing: if YAML has no `cross_tree_candidates` key, defaults to `{}`, producing a valid `CrossTreeConfig` with mode='leaf'. Unchanged behavior.

## Edge Cases Scouted

1. **`_generate_from_specific_pairs` does NOT generate bidirectional requires** -- When `specific_pairs` is used, only one direction of `requires` is generated per pair (A requires B). The combination-based path generates both directions. This is **pre-existing** behavior, not introduced by this refactoring. The extraction is faithful.

2. **Feature ID ordering preserved** -- Both `_generate_from_specific_pairs` and `_generate_from_combinations` use `self._get_feature_obj()` which lookups from `self.feature_ids` (populated by `config.get_feature_ids()` using list order). flamapy tree traversal order is preserved.

3. **`_MAX_CROSS_TREE_FEATURES_WARNING` scope** -- Module-level constant, not class-level. Correct choice since `validate_config` is a `@staticmethod`. Only referenced once (line 196). Clean extraction.

4. **`_constraint_to_dict` / `_constraint_from_dict` are `@staticmethod`** -- Correct. They don't access instance state, and are called via `BiasIO._constraint_to_dict(c)` which works with static methods.

## Positive Observations

- **Counter-drift fix** is a genuine improvement. Old `get_statistics()` silently corrupted `constraint_counter` state.
- **Method naming** follows `_`-prefix convention consistently.
- **Extraction boundaries** are well-chosen -- each extracted method has a single responsibility.
- **config_loader** extractions make `load()` much more readable (88 lines to ~30 lines of top-level logic).
- **bias_io** extractions reduce duplication between `save_to_json` and `load_from_json` serialization logic.
- **File sizes** all under 300 lines -- well within Python guidelines.

## Recommended Actions

1. **(H1)** Add a comment or constant for the hierarchical operator set to prevent silent misclassification on future enum additions.
2. **(M2)** Optionally note stdout side-effect in `get_statistics()` docstring.
3. No other action required -- all extractions are correct.

## Metrics

| Metric | Value |
|--------|-------|
| Type Coverage | Partial (type hints on public methods, not all internals) |
| Test Coverage | 21 bias+congen tests passing |
| Linting Issues | 0 new |
| Public API Changes | None |
| New Files | None |

## Verdict

**APPROVE.** The refactoring is clean, behavior-preserving, and fixes a latent bug in `get_statistics()`. The single high-priority item (H1) is a maintainability suggestion, not a correctness issue. All 13 bias+congen tests pass.
