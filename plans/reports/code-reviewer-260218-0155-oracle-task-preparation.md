# Code Review: Oracle Task Preparation Extraction

**Date:** 2026-02-18
**Scope:** `conacq/oracle/fm_oracle_model.py`, `tests/test_oracle_model.py`, `conacq/oracle/fm_oracle.py`
**Focus:** `_base_set_c` caching, `_config_to_assumptions` DRY helper, `with_configuration` return type change, BGData extraction

---

## Overall Assessment

The refactoring is structurally sound. The DRY extraction of `_config_to_assumptions`, the `_base_set_c` cache, and the fluent return from `with_configuration` are all correct. Two issues found: one medium (missing guard on BGData creation produces wrong data when called without negated constraints) and one low (missing guard on `with_configuration` before `prepare()`).

The two pre-existing test failures (`test_evaluate_real_fm_7`, `test_accuracy_with_real_examples`) are unrelated — they fail due to a missing JSON result file.

---

## Scope

- Files reviewed: 3
- LOC changed: ~100 (net)
- Test suite: 302/304 pass (2 pre-existing failures, unrelated)
- Oracle model tests: 12/12 pass

---

## Issues Found

### Medium — BGData created unconditionally; hardcoded `set_kb[:2]` slice incorrect without negation

**Location:** `conacq/oracle/fm_oracle_model.py`, Step 4 of `FMOracleTaskPreparation.prepare()`

```python
# Step 4: Extract root BG data for ConGen consumption (requires negated constraints)
model._bg_data = BGData(
    set_kb=result.set_kb[:2],  # first pair of assumptions for root constraint
    assumptions=(result.assumptions[0], result.assumptions[1]),
    negation_map={result.assumptions[0]: result.assumptions[1]},
    ...
)
```

Two problems in one block:

**Problem A — unconditional creation.** `BGData` is always created even when `negated_constraint_map` is empty. When negation is absent, `assumptions[1]` is the second FM constraint's ID (not the negated root), so `negation_map` and `assumptions` are semantically wrong. The `bg_data` property guard says `"Call prepare() first"` but does not say `"negated constraints required"`, so callers get silently bad data.

**Problem B — hardcoded `set_kb[:2]`.** The slice assumes the root constraint produces exactly one clause in `set_kb` (one original + one negated = 2 entries). If root has N original clauses, set_kb has N + M entries for root, and `[:2]` only captures the first 2. A computed `root_kb_size` variable appeared in the staged diff but was not used and was then removed entirely in the working tree — leaving the invariant undocumented.

In practice, real FMs (7 tested across `data/fms/`) always produce exactly 1 original clause for root, so the hardcoded `[:2]` happens to work. The bug is latent but not triggered by current data.

**Fix:**

```python
# Step 4: Extract root BG data — only valid with negated constraints
if negated_constraint_map:
    root_clause_count = len(model.constraint_map[next(iter(model.constraint_map))])
    neg_root_count = len(negated_constraint_map.get(
        f"NOT({next(iter(model.constraint_map))})", []))
    root_kb_end = root_clause_count + neg_root_count
    model._bg_data = BGData(
        set_kb=result.set_kb[:root_kb_end],
        assumptions=(result.assumptions[0], result.assumptions[1]),
        negation_map={result.assumptions[0]: result.assumptions[1]},
        descriptions=provider.get_descriptions_for(
            [result.assumptions[0], result.assumptions[1]]),
        next_available_id=id_assumption,
    )
```

The `bg_data` property's `RuntimeError` guard then correctly protects callers who call `from_fm_data()` (no negation) and try to access `bg_data`.

---

### Low — `with_configuration()` before `prepare()` gives misleading `KeyError`

**Location:** `FMOracleModel.with_configuration()`

Calling `with_configuration()` before `prepare()` raises `KeyError` on `self._pos_assignment_to_assumption[feat]` (empty dict) rather than a clear `RuntimeError`. The `task` property already has a guard; `with_configuration` should too.

```python
def with_configuration(self, configuration) -> 'FMOracleModel':
    if self._task is None:
        raise RuntimeError("Call prepare() first")
    self._task.set_c = self._base_set_c + self._config_to_assumptions(configuration)
    return self
```

In practice this only affects incorrect usage, but the error message is confusing.

---

## Correctness of Core Changes

### `_base_set_c` caching

Correct. Cached in `FMOracleTaskPreparation.prepare()` as `list(...)` (copy), then `with_configuration` always creates a new list via concatenation — `_base_set_c` is never mutated.

### `_config_to_assumptions` DRY extraction

Correct. Used in both `with_configuration` and `prepare(configuration=...)` without duplication. Duck-typing for `Configuration` object vs plain dict is handled via `hasattr(configuration, 'elements')`.

### `with_configuration` return type: `list` → `self`

All callers updated correctly:
- `FeatureModelOracle.is_valid()` — calls `with_configuration(assignments)` then `model.get_c()` separately. Correct.
- `tests/test_oracle_model.py` — three tests updated to call `model.with_configuration(...)` then `model.get_c()`. Correct.
- No callers in `conacq/algorithms/` consume the return value.

### `prepare(configuration=None)` optional param

Clean. Delegates directly to `FMOracleTaskPreparation.prepare(model, configuration)`. The two call sites (`build()`, `from_fm_data()`) pass no configuration, which is the common path.

### Rename: `next_tseitin_var` → `next_available_id`

Consistent across `FMOracleModel`, `FeatureModelOracle`, `from_fm_data()`, `build()`, and tests. No stale references remain.

### Rename: `OracleTaskPreparation` → `FMOracleTaskPreparation`

More precise name; no external callers reference the old name.

### Dead field cleanup

`_start_id_assignments` and `start_id_assignments` property removed; replaced by local variable `assignments_start_index` in `FMOracleTaskPreparation.prepare()`. The field `_assignments_start_index` and `assignments_start_index` property appearing in the staged diff were eliminated in the working tree — cleaner outcome.

---

## Positive Observations

- `_config_to_assumptions` extraction is clean DRY, eliminates branching duplicated in `with_configuration` and the old `_compute_base_set_c`.
- Fluent builder pattern on `with_configuration` is consistent with `set_incremental` and standard builder idiom.
- Docstring on `FMOracleTaskPreparation` class-level is a significant improvement — the assumption ID layout (Parts 1-4 / 5+) is now explicitly documented.
- `bg_data` property guard (`RuntimeError`) is consistent with `task` and `description_provider` guards.
- `BGData` dataclass is frozen (`frozen=True`) — immutable once created, appropriate for a snapshot object passed between components.

---

## Recommended Actions

1. **[Medium]** Add `if negated_constraint_map:` guard before BGData creation; compute `root_kb_end` dynamically rather than hardcoding `[:2]`. This prevents silent corruption when called without negated constraints.
2. **[Low]** Add `if self._task is None: raise RuntimeError("Call prepare() first")` at start of `with_configuration`.
3. **[Low]** Add a test for `from_fm_data()` that asserts `bg_data` raises `RuntimeError` (no negated constraints), to document and enforce the guard.

---

## Metrics

- Type coverage: partial (no mypy run requested; `List` without type param on `_base_set_c: List = []` is loose)
- Test coverage: 12/12 oracle model tests pass; BGData guard path not tested
- Linting issues: none observed

---

## Unresolved Questions

- Is it an intended invariant that `FMOracleModel.build()` always calls `FmToDiagPysat(create_negation=True)`, making negated constraints always present in production? If so, the BGData guard is defensive-only and the `[:2]` bug is unreachable in production but still worth fixing for correctness.
- Is `from_fm_data()` expected to ever produce a valid `bg_data`? Currently it does not pass negated constraints, so accessing `bg_data` after `from_fm_data()` would silently return wrong data.
