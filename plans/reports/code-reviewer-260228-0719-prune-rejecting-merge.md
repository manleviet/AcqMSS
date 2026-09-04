# Code Review: DRY Refactoring -- prune_rejecting() Merge

**Date**: 2026-02-28
**Commit**: b1f191a (HEAD)
**Reviewer**: code-reviewer

## Code Review Summary

### Scope
- Files: 13 changed (focus on 3 core: `sat_utils.py`, `findscope.py`, `quacq.py`)
- Also changed: `query_provider.py`, `checker.py`, `quacq_runner.py`, `findc.py`, `quacq_model.py`, `quacq_model_builder.py`, `test_quacq.py`, `docs/quacq.md`, `docs/system-architecture.md`
- LOC: ~200 removed, ~80 added (net negative -- good DRY)
- Focus: DRY extraction of `prune_rejecting()`, plus QueryProvider migration to checker-based API

### Overall Assessment

The commit is a **large multi-concern refactoring** that bundles at least 4 separate changes:
1. DRY extraction of `prune_rejecting()` into `sat_utils.py`
2. Migration of QueryProvider from raw SAT solver to `checker.is_consistent()` + `checker.get_model()`
3. Addition of abstract `get_model()` method to `ConsistencyChecker`
4. Removal of legacy clause-based fallback paths

The DRY extraction itself is clean and correct. However, this commit introduces **2 test failures** and a **critical runner signature mismatch** that will crash at runtime.

---

## Critical Issues

### 1. Runner `_learn_params_from_task` signature mismatch (will crash at runtime)

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/quacq_runner.py` (lines 51-57)

`_learn_params_from_task()` was trimmed to only return `set_c`, `set_b`, `negation_map`. But `QuAcq.learn()` still requires `feature_ids`, `id_to_feature`, and `constraint_clauses` as positional/keyword args (no defaults).

```python
# quacq_runner.py:51-57 -- only 3 params
def _learn_params_from_task(task) -> dict:
    return dict(
        set_c=task.set_c,
        set_b=task.set_b,
        negation_map=task.negation_map,
    )

# quacq.py:101 -- still requires 6 data params
def learn(self, set_c, set_b, negation_map,
          feature_ids, id_to_feature, constraint_clauses, ...):
```

**Impact**: `quacq.learn(**task_data, ...)` will raise `TypeError: learn() missing 3 required keyword arguments: 'feature_ids', 'id_to_feature', 'constraint_clauses'` for ALL runner-based executions.

**Fix**: Either (a) add the 3 params back to `_learn_params_from_task`, or (b) give them defaults in `learn()` and source them from `self.model`. Option (b) is cleaner long-term.

### 2. Two test failures -- stale `id_to_feature` kwarg

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py` (lines 192 and 612)

Two test methods still pass `id_to_feature=task.id_to_feature` to `generate_from_sat()`, but that parameter was removed from the method signature.

```
FAILED tests/test_quacq.py::TestQueryProvider::test_generate_from_sat
FAILED tests/test_quacq.py::TestQueryProviderWithQuAcqTask::test_generate_from_sat_with_quacq_task
TypeError: QueryProvider.generate_from_sat() got an unexpected keyword argument 'id_to_feature'
```

**Fix**: Remove `id_to_feature=task.id_to_feature` from both test call sites.

---

## High Priority

### 3. FindScope behavioral change: scope filtering removed

**Old behavior** (`_prune_rejecting_partial` pre-refactor):
```python
for c_id in list(remaining_bias):
    c_vars = get_constraint_vars(c_id, constraint_clauses, id_to_feature)
    if not c_vars.issubset(R):  # SKIP constraints whose vars extend beyond R
        continue
    if violates_clauses(clauses, assignment):
        pruned.append(c_id)
```

**New behavior** (via shared `prune_rejecting()`):
```python
for c_id in list(remaining_bias):
    if not checker.is_consistent(base + [c_id]):  # Check ALL bias constraints
        pruned.append(c_id)
```

The old code **only pruned constraints whose variables were a subset of R** (the partial scope). The new code checks **all remaining bias constraints** against the partial assignment. This is a semantic change, not just a DRY refactoring.

**Impact**: The new behavior is arguably **more correct** (SAT-based checking catches implied violations that pure clause evaluation misses), and it prunes more aggressively. However, it changes the algorithm's pruning semantics. If this is intentional, it should be documented. If not, the scope filter should be restored in the `_prune_rejecting_partial` wrapper or as a parameter to `prune_rejecting()`.

### 4. `set_b[0]` IndexError risk (no guard)

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (lines 192, 205, 220)

`set_b[0]` is accessed without checking if `set_b` is non-empty. The old code had a guard via `root_assumption=task.set_b[0] if task.set_b else None` in the runner, plus `if self.model and root_assumption is not None` in `_prune_rejecting_constraints`.

The legacy fallback (which handled `root_assumption=None`) was removed. If `set_b` is ever empty, this crashes with `IndexError`.

**Mitigation**: `set_b` is populated by `QuAcqTaskPreparation` which always includes root BG assumptions, so empty `set_b` is unlikely in practice. But adding an early guard or assertion at the top of `learn()` would be defensive:
```python
assert set_b, "set_b (BG assumptions) must be non-empty; root BG always present"
```

---

## Medium Priority

### 5. FindScope/FindC instantiated per-iteration (object allocation churn)

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` (lines 199, 211)

```python
find_scope = FindScope(self.oracle, self.checker, self.model)  # per negative answer
find_c = FindC(self.oracle, self.checker, self.model, self.discriminating_generator)
```

Previously these were created once in `__init__`. Now they are re-created each iteration. Since they are lightweight (just store references), this is not a performance concern, but it is a pattern change worth noting. The DI at construction was cleaner.

### 6. Removed legacy fallback without migration path

The commit removes `_prune_rejecting_constraints_legacy()` which was the pure Boolean eval fallback used when `self.model` or `root_assumption` was `None`. Now `prune_rejecting()` unconditionally calls `model.config_to_assumptions()`, meaning `model` is **required** for all pruning. Tests that construct QuAcq without a model (e.g., `test_quacq_empty_bias`) work only because empty bias skips the pruning path entirely.

### 7. Stale documentation references

**Files**: `/Users/manleviet/Development/GitHub/AcqMSS/docs/quacq.md` (line 169), `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` (lines 127, 188)

Docs still reference `generate_from_sat(remaining_bias, learned_kb, set_b, negation_map, id_to_feature)` with the old parameter `id_to_feature` which was removed from the actual signature (now 4 params: `remaining_bias, learned_kb, set_b, negation_map`).

---

## Low Priority

### 8. Dead code: `partial_config_to_assumptions` and `config_to_assumptions` in sat_utils

These functions are no longer imported by any production code (only by tests). They could be moved to test utilities or removed if tests are updated to use `model.config_to_assumptions()`.

### 9. `NonIncrementalPySATChecker` already had `_cached_model` before this commit?

The diff shows `_cached_model` being added to `NonIncrementalPySATChecker.__init__()`, but looking at the final file, the field already exists. This suggests the diff might include changes from a previous commit as well. Minor -- no functional impact.

### 10. Minor: comment-only noise

`sat_utils.py:75`: Added comment `# Collects bias constraints matching scope exactly or subset` that just restates what the code does.

---

## Positive Observations

- Clean DRY extraction: `prune_rejecting()` consolidates identical logic from 2 call sites
- SAT-based approach is more robust than pure Boolean clause evaluation
- Removed ~120 lines of redundant code
- `ConsistencyChecker.get_model()` as abstract method is a proper API addition
- QueryProvider migration to checker-based API removes direct PySAT dependency

---

## Recommended Actions

1. **[CRITICAL]** Fix runner `_learn_params_from_task` -- add back `feature_ids`, `id_to_feature`, `constraint_clauses` or refactor `learn()` to get them from `self.model`
2. **[CRITICAL]** Fix 2 test failures -- remove stale `id_to_feature` kwarg from test_generate_from_sat call sites
3. **[HIGH]** Document the FindScope scope-filter removal as intentional behavioral change, or restore the filter
4. **[HIGH]** Add `assert set_b` or equivalent guard at top of `learn()`
5. **[MEDIUM]** Update doc references for `generate_from_sat()` signature (remove `id_to_feature` param)

### Metrics
- Test Results: 60 passed, 2 failed, 1 warning
- Runtime Crash Risk: HIGH (runner will fail with TypeError)

### Unresolved Questions

1. Was the removal of the scope-subset filter in FindScope's pruning intentional? The old code only pruned constraints whose variables were within the partial scope R. The new code prunes all bias constraints. This changes algorithm behavior.
2. Should `learn()` still require `feature_ids`/`id_to_feature`/`constraint_clauses` as explicit params, or should they migrate to `self.model` (which already has them)?
3. Is the `@count_calls('prune_calls')` profiling metric still meaningful now that FindScope's pruning bypasses it (only QuAcq's wrapper is decorated)?
