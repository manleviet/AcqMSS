# Phase 2: Refactor FindScope — oracle.is_valid() + record_query

## Context

- Brainstorm: `plans/reports/brainstorm-260227-1614-findscope-findc-oracle-refactor.md`
- Paper: IJCAI 2013 Algorithm 2 — FindScope uses oracle partial membership queries
- Depends on: Phase 1 (no code dependency, but phase ordering)

## Overview

- **Priority**: P1
- **Status**: completed
- **Effort**: 30min

Replace `_check_partial_consistency()` (OneShotModel SAT) with `oracle.is_valid(partial_dict)`. Add `record_query` callback for query counting. Remove `fm_clauses` and `solver_name` params.

## Key Changes

| Before | After |
|--------|-------|
| `_check_partial_consistency(fm_clauses, assumptions, solver_name)` | `oracle.is_valid(partial_config_dict)` |
| No query recording | `record_query(partial, is_consistent, 'findscope')` |
| Params: `fm_clauses`, `solver_name` | Params: `oracle`, `record_query` |
| Imports: `OneShotModel`, `CheckerFactory` | Imports: none new (Oracle passed in) |

## Requirements

### Functional
- Partial membership queries via `oracle.is_valid({k: e[k] for k in R})`
- Every query recorded via `record_query(config, answer, 'findscope')`
- `_prune_rejecting_partial()` unchanged (operates on task, not oracle)

### Non-functional
- No SAT solver imports remaining in findscope.py
- File stays under 100 LOC after cleanup

## Related Code Files

### Modify
- `conacq/algorithms/quacq/findscope.py` (122 LOC -> ~85 LOC)

### Read (callers to update in Phase 4)
- `conacq/algorithms/quacq/quacq.py` — `learn_from_examples()` calls `find_scope()`

## New Signature

```python
def find_scope(
        e: dict,
        R: set,
        Y: set,
        ask_query: bool,
        oracle,                    # NEW: replaces fm_clauses
        task,
        remaining_bias: set,
        record_query,              # NEW: callback(config, answer, source)
        profiler: AbstractProfiler = None
) -> List[str]:
```

## Implementation Steps

1. **Update signature**: Remove `fm_clauses: List[List[int]]`, `solver_name: str`. Add `oracle`, `record_query` params.
2. **Replace partial check logic** (lines 51-64):
   ```python
   if ask_query:
       partial = {k: e[k] for k in R}
       is_consistent = oracle.is_valid(partial)
       record_query(partial, is_consistent, 'findscope')
       if is_consistent:
           _prune_rejecting_partial(task, remaining_bias, e, R)
       else:
           return []
   ```
   Key: build `partial` as `Dict[str, bool]` from `e` restricted to `R`, pass directly to oracle.
3. **Update recursive calls** (lines 75-76): Pass `oracle` and `record_query` instead of `fm_clauses` and `solver_name`.
   ```python
   S1 = find_scope(e, R | Y1, Y2, True, oracle, task, remaining_bias, record_query, profiler)
   S2 = find_scope(e, R | set(S1), Y1, len(S1) > 0, oracle, task, remaining_bias, record_query, profiler)
   ```
4. **Delete `_check_partial_consistency()`** function (lines 81-93) — no longer needed.
5. **Remove dead imports**: `OneShotModel`, `CheckerFactory`. Remove `from ._task_compat import get_clause_map` if only used by deleted code. Keep `get_clause_map` if `_prune_rejecting_partial` uses it (it does — keep).
6. **Update module docstring**: "Checks via oracle.is_valid() partial membership queries" instead of "ConsistencyChecker against FM".
7. **Update function docstring**: Document `oracle` and `record_query` params.

## Implementation Code (Final State)

```python
"""
FindScope algorithm from IJCAI13 paper (Algorithm 2).

Finds scope of violated constraint using partial membership queries
checked via oracle.is_valid().

Complexity: O(|S| * log|X|) queries where S=scope size, X=total variables.
"""

import logging
from typing import List

from ._task_compat import get_clause_map
from explanation.operations.algorithms.profiler import AbstractProfiler


def find_scope(
        e: dict,
        R: set,
        Y: set,
        ask_query: bool,
        oracle,
        task,
        remaining_bias: set,
        record_query,
        profiler: AbstractProfiler = None
) -> List[str]:
    """
    Find scope of violated constraint via partial membership queries.

    Args:
        e: Complete negative example (config dict)
        R: Already-determined scope variables (feature names)
        Y: Remaining variables to search
        ask_query: Whether to query oracle with e[R]
        oracle: Oracle with is_valid(Dict[str, bool]) -> bool
        task: QuAcqTask state (immutable)
        remaining_bias: Mutable set of remaining bias assumption IDs
        record_query: Callback(config, answer, source) to record queries
        profiler: Optional profiler

    Returns:
        Scope variables (feature names) as list
    """
    if ask_query:
        partial = {k: e[k] for k in R}
        is_consistent = oracle.is_valid(partial)
        record_query(partial, is_consistent, 'findscope')

        if is_consistent:
            _prune_rejecting_partial(task, remaining_bias, e, R)
        else:
            return []

    if len(Y) <= 1:
        return list(Y)

    # Binary split
    Y_list = sorted(Y)
    mid = len(Y_list) // 2
    Y1 = set(Y_list[:mid])
    Y2 = set(Y_list[mid:])

    S1 = find_scope(e, R | Y1, Y2, True, oracle, task, remaining_bias, record_query, profiler)
    S2 = find_scope(e, R | set(S1), Y1, len(S1) > 0, oracle, task, remaining_bias, record_query, profiler)

    return S1 + S2


def _prune_rejecting_partial(task, remaining_bias: set, e: dict, R: set) -> None:
    """Prune bias constraints that reject partial assignment e[R].

    Mutates remaining_bias in place.
    """
    assumptions = task.partial_config_to_assumptions(e, R)
    if not assumptions:
        return

    assignment = {abs(lit): lit > 0 for lit in assumptions}
    clause_map = get_clause_map(task)

    pruned = []
    for c_id in list(remaining_bias):
        clauses = clause_map.get(c_id, [])
        c_vars = task._get_constraint_vars(c_id)
        if not c_vars.issubset(R):
            continue

        if task.violates_clauses(clauses, assignment):
            pruned.append(c_id)

    if pruned:
        remaining_bias -= set(pruned)
        logging.debug('FindScope pruned %d constraints from partial query', len(pruned))
```

## Todo

- [x] Update `find_scope()` signature: remove `fm_clauses`, `solver_name`; add `oracle`, `record_query`
- [x] Replace `_check_partial_consistency` call with `oracle.is_valid(partial_dict)` + `record_query`
- [x] Update recursive calls to pass new params
- [x] Delete `_check_partial_consistency()` function
- [x] Remove `OneShotModel`, `CheckerFactory` imports
- [x] Update docstrings
- [x] DO NOT update callers yet (Phase 4)

## Success Criteria

- `findscope.py` has no `OneShotModel` or `CheckerFactory` imports
- `_check_partial_consistency` deleted
- All partial queries go through `oracle.is_valid()`
- All queries recorded via `record_query`
- File compiles without import errors

## Risk Assessment

- **Low risk**: Internal function, callers updated in Phase 4
- **Note**: Callers will break until Phase 4 updates call sites. Run tests only after Phase 4.
