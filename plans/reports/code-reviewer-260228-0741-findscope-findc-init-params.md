# Code Review: FindScope/FindC __init__ Param Migration

**Date:** 2026-02-28
**Plan:** `plans/260228-0735-findscope-findc-init-params/`
**Scope:** `findscope.py`, `findc.py`, `quacq.py`, `__init__.py`

---

## Overall Assessment

Clean, well-scoped refactor. The migration of `record_query` and `root_assumption` from method params to `__init__` is correct, complete, and internally consistent. The key invariant — both values are fixed for the lifetime of each FindScope/FindC instance (constructed once per negative example inside `learn()`) — holds. No regressions expected and tests confirm this.

One low-priority concern and a couple of minor observations follow.

---

## Critical Issues

None.

---

## High Priority

None.

---

## Medium Priority

### 1. Redundant `partial` recomputation in `FindScope.run()`

**File:** `conacq/algorithms/quacq/findscope.py`, lines 54 and 59

```python
if ask_query:
    partial = {k: e[k] for k in R if k in e}          # line 54
    is_consistent = self.oracle.is_valid(partial)
    self.record_query(partial, is_consistent, 'findscope')

    if is_consistent:
        partial = {k: e[k] for k in R if k in e}      # line 59 — duplicate
        if partial:
            pruned = prune_rejecting(...)
```

`partial` is built identically twice. The second assignment on line 59 was introduced during this refactor when `_prune_rejecting_partial()` was inlined via `prune_rejecting()`. `partial` from line 54 is still valid at line 59 — no mutation occurs between the two assignments.

**Fix:**

```python
if ask_query:
    partial = {k: e[k] for k in R if k in e}
    is_consistent = self.oracle.is_valid(partial)
    self.record_query(partial, is_consistent, 'findscope')

    if is_consistent:
        if partial:
            pruned = prune_rejecting(self.checker, self.model, remaining_bias, partial, self.root_assumption)
            if pruned:
                logging.debug('FindScope pruned %d constraints from partial query', len(pruned))
    else:
        return []
```

---

## Low Priority

### 2. `FindScope` and `FindC` are instantiated per-negative-example, not per-`learn()` call

**File:** `conacq/algorithms/quacq/quacq.py`, lines 199–212

```python
find_scope = FindScope(self.oracle, self.checker, self.model,
                       record_query, set_b[0])
...
find_c = FindC(self.oracle, self.checker, self.model,
               record_query, set_b[0],
               generator=self.discriminating_generator)
```

Both objects are constructed fresh inside the `while remaining_bias` loop, once for every negative oracle answer. Since `record_query` and `set_b[0]` are stable for the full duration of `learn()`, these instances could be created once before the loop and reused.

This is purely an allocation efficiency note — correctness is unaffected. With small bias sets the overhead is negligible. Worth a follow-up if profiling shows hot-path object churn.

### 3. Docstring of `FindScope` class body still says "per-call data passed to run()"

**File:** `conacq/algorithms/quacq/findscope.py`, line 22

```python
"""Finds scope of violated constraint via partial membership queries.

Oracle, checker, and model injected at construction; per-call data passed to run().
"""
```

After this refactor, `record_query` and `root_assumption` are also injected at construction, so the comment is stale. Same pattern appears in `FindC` (line 26).

**Fix:** Update to:
```
Oracle, checker, model, record_query, and root_assumption injected at construction;
per-call data (example, variable sets, remaining_bias) passed to run().
```

### 4. `__init__.py` docstring example still missing `feature_ids` / `id_to_feature` / `constraint_clauses` args

**File:** `conacq/algorithms/quacq/__init__.py`, lines 30–35

The usage example in the module docstring was updated correctly for the DI constructor style, but `learn()` is shown without `feature_ids`, `id_to_feature`, or `constraint_clauses` arguments — all of which are required by the current `learn()` signature. This is a documentation-only gap, not a runtime bug.

---

## Backward Compatibility

`FindScope` and `FindC` are both exported via `__init__.py` `__all__`. The constructor signatures changed (two new required positional params added: `record_query`, `root_assumption`). Any external caller constructing these directly will break at instantiation.

The test suite has no direct `FindScope(...)` or `FindC(...)` instantiations — all exercised indirectly through `QuAcq.learn()`. This means no test breakage, but the API surface contract changed.

**Assessment:** Acceptable given the project's current maturity level (no downstream library consumers evident). If these classes are intended as a public extension point, consider adding a note in the docstring that they are internal algorithm components.

---

## Parameter Migration Correctness

Full trace of removed references:

| Param | Removed from | Replaced with |
|---|---|---|
| `record_query` | `FindScope.run()` sig | `self.record_query` (line 56) |
| `root_assumption` | `FindScope.run()` sig | `self.root_assumption` (line 61) |
| `record_query`, `root_assumption` | recursive `FindScope.run()` calls (lines 76–77) | absent — no longer needed |
| `record_query` | `FindC.run()` sig | `self.record_query` (line 124) |
| `root_assumption` | `FindC.run()` sig | `self.root_assumption` (line 78) |
| `record_query` | `FindC._narrow_with_generator()` sig | `self.record_query` (line 124) |
| `record_query` passed to `_narrow_with_generator` | `FindC.run()` line 95–96 | removed from call |

No missed `self.` references found. No dangling local usages of old param names remain.

`_prune_rejecting_partial()` was removed from `FindScope` and replaced by a direct call to `prune_rejecting()` from `sat_utils`. The inline replacement is functionally equivalent — same logic, same mutation of `remaining_bias`.

---

## Positive Observations

- Recursive threading of `record_query` and `root_assumption` through `FindScope.run()` was the clearest source of noise; eliminating it is the right call.
- The `generator=` keyword-only idiom in `FindC.__init__` keeps the positional order readable.
- `prune_rejecting()` DRY extraction into `sat_utils` (from a prior commit) is used cleanly here.
- All 356 tests pass — no regressions.

---

## Recommended Actions

1. **[Medium]** Remove duplicate `partial` dict comprehension in `FindScope.run()` — one-line fix.
2. **[Low]** Update `FindScope`/`FindC` class docstrings to reflect full init signature.
3. **[Low]** Fix `__init__.py` usage example to include required `learn()` args.
4. **[Low/Optional]** Consider lifting `FindScope`/`FindC` construction out of the `while` loop in `quacq.py` to avoid per-iteration allocation.

---

## Unresolved Questions

None.
