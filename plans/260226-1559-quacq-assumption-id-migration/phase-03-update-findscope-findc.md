# Phase 3: Update FindScope + FindC

## Context Links
- [Parent Plan](plan.md) | [Phase 1](phase-01-create-quacq-task-and-model.md) | [Phase 2](phase-02-update-quacq-algorithm.md)
- Source: `conacq/algorithms/interactive/findscope.py` (134 LOC)
- Source: `conacq/algorithms/interactive/findc.py` (197 LOC)

## Overview
- **Priority**: P1
- **Status**: completed
- **Depends on**: Phase 1
- **Description**: Update FindScope and FindC to accept QuAcqTask. Constraint IDs change from `str` to `int`; feature variable operations (already `int`) are unchanged.

## Key Insights
1. **FindScope** operates on feature name variables (strings) for scope, not constraint IDs. The task parameter is used for `partial_config_to_assumptions()`, `violates_clauses()`, `_get_constraint_vars()`, and `remove_from_bias()`. All of these exist on QuAcqTask with same signatures (except bias/constraint_clauses use `int` keys).
2. **FindC** returns a constraint ID (`Optional[str]` -> `Optional[int]`). Internally iterates candidates from `task.get_constraints_with_scope(scope)` which now returns `List[int]`.
3. **_prune_rejecting_partial()** in findscope.py iterates `task.bias` (now `Set[int]`) and looks up clauses via `task.constraint_clauses` (now `Dict[int, ...]`).
4. **_narrow_with_pool()** and **_narrow_with_sat()** in findc.py iterate candidates (`List[str]` -> `List[int]`), look up clauses, and prune. The SAT-based narrowing in `_narrow_with_sat()` uses `task.negated_constraint_map` — must change to `task.negated_clauses`.
5. Feature variables (scope sets, partial assignments) remain `str` names throughout — no change needed for those.

## Requirements

### Functional
- `find_scope()` accepts `QuAcqTask` instead of `InteractiveTask`
- `find_c()` accepts `QuAcqTask`, returns `Optional[int]`
- All constraint candidate operations use `int` assumption IDs
- Feature-variable operations (scope as `Set[str]`) unchanged

### Non-functional
- Minimal changes — mostly type annotations and dict key lookups

## Related Code Files

### Files to Modify
| File | Changes |
|------|---------|
| `conacq/algorithms/interactive/findscope.py` | Task type, constraint ID types |
| `conacq/algorithms/interactive/findc.py` | Task type, return type, candidate types |

## Implementation Steps

### Step 1: Update findscope.py

#### `find_scope()` signature (line 19)
```python
def find_scope(
        e: dict,
        R: set,
        Y: set,
        ask_query: bool,
        fm_clauses: List[List[int]],
        task: QuAcqTask,          # Changed from InteractiveTask
        solver_name: str = 'glucose4',
        profiler: AbstractProfiler = None
) -> List[str]:
```

Return type stays `List[str]` — these are feature NAMES, not constraint IDs. Body unchanged.

#### `_prune_rejecting_partial()` (line 92)
```python
def _prune_rejecting_partial(task: QuAcqTask, e: dict, R: set) -> None:
    """Prune bias constraints that reject partial assignment e[R]."""
    assumptions = task.partial_config_to_assumptions(e, R)
    if not assumptions:
        return

    assignment = {abs(lit): lit > 0 for lit in assumptions}

    pruned = []
    for aid in list(task.bias):                          # Set[int] iteration
        clauses = task.constraint_clauses.get(aid, [])   # Dict[int, ...]
        c_vars = task._get_constraint_vars(aid)          # int key
        if not c_vars.issubset(R):
            continue
        if task.violates_clauses(clauses, assignment):
            pruned.append(aid)

    if pruned:
        task.remove_from_bias(pruned)
```

Import change:
```python
from .quacq_task import QuAcqTask  # Add
# Remove: from .task import InteractiveTask
```

### Step 2: Update findc.py

#### `find_c()` signature (line 22)
```python
def find_c(
        e: dict,
        scope: set,
        task: QuAcqTask,              # Changed from InteractiveTask
        fm_clauses: List[List[int]],
        example_provider: Optional[ExampleProvider],
        solver_name: str = 'glucose4',
        query_mode: str = 'example_only',
        profiler: AbstractProfiler = None
) -> Optional[int]:                    # Changed from Optional[str]
```

Body changes:
- `candidates = task.get_constraints_with_scope(scope)` — returns `List[int]` now
- `task.constraint_clauses.get(aid, [])` instead of `task.constraint_map.get(c_id, [])`
- All `c_id` variables become `aid` (int)

#### `_narrow_with_pool()` (line 96)
```python
def _narrow_with_pool(
        candidates: List[int],         # Changed from List[str]
        task: QuAcqTask,               # Changed from InteractiveTask
        fm_clauses: List[List[int]],
        example_provider: ExampleProvider,
        solver_name: str,
        profiler: AbstractProfiler = None
) -> Optional[int]:                    # Changed from Optional[str]
```

Body changes:
- `task.constraint_clauses.get(c, [])` instead of `task.constraint_map.get(c, [])`
- `task.remove_from_bias([c_id])` — c_id is `int`

#### `_narrow_with_sat()` (line 141)
```python
def _narrow_with_sat(
        candidates: List[int],         # Changed from List[str]
        task: QuAcqTask,               # Changed from InteractiveTask
        fm_clauses: List[List[int]],
        solver_name: str,
        profiler: AbstractProfiler = None
) -> Optional[int]:                    # Changed from Optional[str]
```

Body changes (line 151-183):
```python
for i, c_i in enumerate(candidates):
    for c_j in candidates[i+1:]:
        clauses_i = task.constraint_clauses.get(c_i, [])
        neg_j = task.negated_clauses.get(c_j, [])  # Changed from negated_constraint_map

        all_clauses = list(fm_clauses) + clauses_i + neg_j
        solver = Solver(name=solver_name, bootstrap_with=all_clauses)
        # ... rest unchanged except c_j/c_i are int
```

Import change:
```python
from .quacq_task import QuAcqTask  # Add
# Remove: from .task import InteractiveTask
```

## Todo List
- [ ] Update findscope.py: import QuAcqTask, update find_scope() signature
- [ ] Update findscope.py: update _prune_rejecting_partial() for int IDs
- [ ] Update findc.py: import QuAcqTask, update find_c() signature and return type
- [ ] Update findc.py: update _narrow_with_pool() for int IDs
- [ ] Update findc.py: update _narrow_with_sat() to use task.negated_clauses
- [ ] Verify feature-variable operations (scope as Set[str]) are unchanged

## Success Criteria
- find_scope() accepts QuAcqTask, returns feature names (List[str]) — unchanged return type
- find_c() accepts QuAcqTask, returns Optional[int] — assumption ID of found constraint
- _narrow_with_sat() uses task.negated_clauses (Dict[int, List[List[int]]]) for SAT-based discrimination
- No string constraint IDs in either module

## Risk Assessment
1. **Scope vs constraint ID confusion**: FindScope returns feature NAMES (str), not constraint IDs. This is correct — scope is about variables, not constraints. Must not accidentally change scope types.
2. **negated_clauses availability**: FindC's `_narrow_with_sat()` needs negated clauses per constraint. QuAcqTask.negated_clauses must be populated in Phase 1. Verify field exists.

## Security Considerations
- No changes to external input handling

## Next Steps
- Phase 4: Update InteractiveResult + InteractiveRunner
