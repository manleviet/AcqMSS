# Code Review: DiscriminatingGenerator ConsistencyChecker DI Refactor

**Date:** 2026-02-28
**Files reviewed:** 5
**Tests:** 62 passed, 1 warning (unrelated `pytest.mark.slow`)

---

## Scope

| File | Change |
|---|---|
| `conacq/algorithms/quacq/discriminating_generator.py` | Full rewrite to DI pattern |
| `conacq/algorithms/quacq/quacq_model.py` | Added `get_constraint_vars()` |
| `conacq/runners/quacq_runner.py` | 2 construction sites updated |
| `conacq/algorithms/quacq/__init__.py` | Docstring example updated |
| `tests/test_quacq.py` | 7 construction sites updated |

**Scout findings:** No raw PySAT imports remain in `discriminating_generator.py`. All construction sites confirmed updated. No other callers found outside these files.

---

## Overall Assessment

Clean, well-scoped refactor. The DI pattern is applied correctly and consistently with FindScope/FindC. The old implementation opened its own raw PySAT solver per `generate()` call — the new one reuses the shared checker, eliminating redundant solver startup cost. No regressions. All 62 tests pass.

---

## Critical Issues

None.

---

## High Priority

### 1. Semantic change: assumption-based vs clause-based SAT formula

**Risk: Medium-Low** — confirmed correct, but worth documenting.

Old `generate()` appended raw CNF clauses from `background_clauses + cl_y_clauses + clauses_i + neg_j_clauses` into a fresh solver. New `generate()` passes assumption IDs to `checker.is_consistent(set_c)`:

```python
set_c = [self.root_assumption] + cl_y + [c_i, neg_j]
```

This works correctly because the checker's KB already contains the full formula with assumption-guarded clauses (`set_kb`) and the assumption IDs act as activation literals for those clauses. The `_compute_delta` method in `ConsistencyChecker` handles the enabled/disabled partitioning. Verified against `IncrementalPySATChecker.is_consistent()` internals.

**However:** `cl_y` is now a list of assumption IDs (constraint IDs from `learned_kb`), not raw clauses. This is correct given how the checker is built from the model — those IDs are already part of `assumptions`. The old code bundled the raw clauses directly into the solver formula, which is a subtly different encoding. The new code relies on assumption-gating to selectively activate them. This is the right approach for the assumption-ID architecture but the docstring on `generate()` should note this distinction.

**Recommendation:** Add a one-line comment clarifying `cl_y` contains assumption IDs (not raw clauses):

```python
# C_L[Y]: assumption IDs of learned constraints whose vars are in scope
cl_y = [c_id for c_id in learned_kb
        if self.model.get_constraint_vars(c_id).issubset(scope)]
```

---

## Medium Priority

### 2. `model=None` guard for empty-bias tests

`test_quacq_empty_bias` and `test_quacq_empty_bias_quacq_task` pass `model=None` to `DiscriminatingGenerator`. This is safe only because `generate()` is never called when `set_c=[]` (bias is empty, so the algorithm converges immediately without triggering discriminating generation).

There is no guard in `generate()` itself:

```python
# In generate(), line 47:
cl_y = [c_id for c_id in learned_kb
        if self.model.get_constraint_vars(c_id).issubset(scope)]
```

If `model=None` and `generate()` is ever called, this raises `AttributeError: 'NoneType' object has no attribute 'get_constraint_vars'`. The guard exists implicitly in the algorithm flow (empty bias → no negative example → `generate()` never called), but it is non-obvious.

**Options:**
- Add a guard at top of `generate()`: `if self.model is None: return None`
- Or add an assertion: `assert self.model is not None, "model required for generate()"`

The guard approach is more defensive; the assertion makes the contract explicit. Either is fine. The guard is recommended to prevent confusing `AttributeError` if the invariant is violated.

### 3. `get_constraint_vars()` on `QuAcqModel`: minor duplication with `sat_utils`

`QuAcqModel.get_constraint_vars()` (new, line 131–137) duplicates the logic of the standalone `get_constraint_vars()` in `sat_utils.py` (line 36–47). Both extract feature names from constraint clauses using `id_to_feature`. The `sat_utils` version takes explicit `constraint_clauses` and `id_to_feature` dicts; the model method delegates to `task` fields.

This is an acceptable trade-off — the method encapsulates task field access behind the model interface, consistent with how `config_to_assumptions` is handled. No action required, but worth noting for future refactoring if `sat_utils` standalone functions are retired.

### 4. `__init__.py` docstring example omits `model` arg to `QuAcq.for_oracle()`

```python
# In __init__.py line 32:
quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)
```

The actual call in the runner passes `model=self.model`:

```python
quacq = QuAcq.for_oracle(checker, learn_oracle, query_provider, discrim_gen,
                          model=self.model, profiler=profiler)
```

The docstring example is incomplete for real usage. Technically not a bug (model is optional), but misleading for newcomers.

**Recommendation:** Add `model=model` to the docstring example call.

---

## Low Priority

### 5. DI consistency with FindScope/FindC

Constructor signature matches FindScope/FindC convention: `(checker, model, ...)`. Public attributes (`self.checker`, `self.model`, `self.root_assumption`) are consistent with FindScope/FindC (`self.oracle`, `self.checker`, `self.model`). One minor inconsistency: FindScope uses private helper `_prune_rejecting_partial()` for sub-operations; DiscriminatingGenerator has no private helpers (all logic in `generate()`). This is fine — `generate()` is small enough at 17 lines.

### 6. `negation_map` fetched on every `generate()` call

```python
negation_map = self.model.get_negation_map()
neg_j = negation_map.get(c_j)
```

`get_negation_map()` calls `_require_task()` which returns the already-computed task dict. Cost is minimal (dict attribute lookup, no recomputation), but if `generate()` is called frequently in tight loops this pattern could be cached at construction time. YAGNI applies — leave as-is unless profiling shows it as a bottleneck.

---

## Edge Cases Found by Scout

1. **`set_b` empty guard in runner**: `task.set_b[0]` is used as `root_assumption` at both construction sites in `quacq_runner.py` (lines 239, 266). If `set_b` is ever empty at this point, this raises `IndexError`. The guard exists upstream (oracle always produces BG assumptions), but is not checked at the call site. Low risk given architecture guarantees, but consider `task.set_b[0] if task.set_b else 0` or a precondition check.

2. **`checker.get_model()` after `is_consistent()`**: The new code calls `self.checker.get_model()` immediately after `is_consistent()` returns True. The contract on `ConsistencyChecker.get_model()` states "Only valid after `is_consistent()` returned True". Since the call is correctly gated by `if self.checker.is_consistent(set_c):`, this is safe. No issue.

3. **Shared checker state in concurrent scenarios**: `DiscriminatingGenerator` shares the same `checker` instance with `FindC`, `FindScope`, `QueryProvider`, and `QuAcq`. If `generate()` is ever called from multiple threads, `get_model()` could return a stale model. Current usage is single-threaded; no issue now.

---

## Positive Observations

- Elimination of raw `Solver` creation per `generate()` call is correct — avoids solver startup overhead and ensures consistent accounting via the shared profiler.
- No PySAT imports remain in `discriminating_generator.py` — clean separation.
- `generate()` is now 17 lines vs 35 lines; substantially simpler and easier to reason about.
- The `cl_y` filtering (assumption IDs whose vars are a subset of scope) is semantically equivalent to the old `_get_learned_clauses_in_scope()` — the translation is correct.
- All 7 test construction sites updated with consistent `(checker=checker, model=model, root_assumption=task.set_b[0])` signature.
- Empty-bias test pattern (`model=None, root_assumption=0`) is a reasonable sentinel for no-op construction.
- `__all__` export of `DiscriminatingGenerator` in `__init__.py` is correctly retained.

---

## Recommended Actions

1. **[Low]** Add `if self.model is None: return None` guard at top of `generate()` to make the `model=None` sentinel explicit and prevent cryptic `AttributeError`.
2. **[Low]** Add comment clarifying `cl_y` items are assumption IDs, not raw clauses.
3. **[Low]** Add `model=model` to the `__init__.py` docstring example call.
4. **[Skip]** `task.set_b[0]` IndexError: accepted risk given architecture guarantees.

---

## Metrics

- Type coverage: `get_constraint_vars()` correctly typed as `-> Set[str]`; `generate()` return `Optional[Dict[str, bool]]` unchanged
- Linting: No issues found
- Test coverage: 62/62 pass; empty-bias, full-learning, and factory paths all exercised

---

## Unresolved Questions

None.
