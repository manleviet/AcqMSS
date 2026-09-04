# Phase 3: Refactor FindScope

## Context Links
- [Plan overview](plan.md)
- [QuAcq Internals research](research/researcher-01-quacq-internals.md)
- Source: `conacq/algorithms/quacq/findscope.py` (134 LOC)
- Consumer: `QuAcq.learn()` calls `find_scope()`
- Depends on: Phase 1 (DiscriminatingGenerator already refactored)
<!-- Updated: Validation Session 1 - NEW phase: FindScope refactored to raw params -->

## Overview
- **Priority:** High (blocks Phase 5)
- **Status:** complete
- **Description:** Remove QuAcqTask dependency from `find_scope()`. Accept raw data params + standalone utility functions instead of task methods.

## Key Insights
- `find_scope()` is a module-level function (not a class method)
- Task fields accessed: `partial_config_to_assumptions()`, `_get_constraint_vars()`, `violates_clauses()`, `constraint_clauses` (via `get_clause_map`)
- These are pure computation methods — can be inlined as standalone functions or passed as raw data
- `partial_config_to_assumptions` converts partial config dict → assumption literals using `feature_ids` mapping
- `_get_constraint_vars` extracts variable names from constraint clauses
- `violates_clauses` checks if an assignment violates CNF clauses — pure SAT logic
- `get_clause_map(task)` from `_task_compat` just returns `task.constraint_clauses`

## Requirements

### Functional
- `find_scope()` accepts raw data params instead of `task`
- No import of `QuAcqTask` or `_task_compat` in this file
- Inline or extract task methods as standalone functions
- Signature of `find_scope` changes but internal algorithm logic stays identical

### Non-Functional
- File stays under 150 LOC
- Type hints on all public functions

## Architecture

### Before
```python
def find_scope(e, R, Y, ask_query, oracle, task, remaining_bias, record_query, profiler):
    # uses: task.partial_config_to_assumptions(e, R)
    # uses: task._get_constraint_vars(c_id)
    # uses: task.violates_clauses(clauses, assignment)
    # uses: get_clause_map(task) -> task.constraint_clauses
```

### After
```python
def find_scope(e, R, Y, ask_query, oracle,
               constraint_clauses: Dict[int, List[List[int]]],
               feature_ids: Dict[str, int],
               id_to_feature: Dict[int, str],
               remaining_bias, record_query, profiler):
    # uses: partial_config_to_assumptions(e, R, feature_ids) — standalone
    # uses: get_constraint_vars(c_id, constraint_clauses, id_to_feature) — standalone
    # uses: violates_clauses(clauses, assignment) — standalone
    # uses: constraint_clauses directly
```

### Standalone utility functions (new or extracted)
```python
def partial_config_to_assumptions(config: Dict[str, bool], variables: set,
                                   feature_ids: Dict[str, int]) -> List[int]:
    """Convert partial config to assumption literals."""

def get_constraint_vars(assumption_id: int,
                        constraint_clauses: Dict[int, List[List[int]]],
                        id_to_feature: Dict[int, str]) -> Set[str]:
    """Get variable names involved in a constraint."""

def violates_clauses(clauses: List[List[int]],
                     assignment: Dict[int, bool]) -> bool:
    """Check if assignment violates any clause."""
```

## Related Code Files
- **Modify:** `conacq/algorithms/quacq/findscope.py`
- **Create or modify:** utility module for shared functions (used by FindScope + FindC + DiscrimGen)
- **No change to callers yet** — Phase 5 wires new signature from QuAcq.learn()

## Implementation Steps

1. **Identify shared utilities**: `partial_config_to_assumptions`, `config_to_assumptions`, `get_constraint_vars`, `violates_clauses` are needed by both FindScope and FindC. Extract to a shared utility module (e.g., `conacq/algorithms/quacq/sat_utils.py`).

2. **Create `sat_utils.py`** with standalone implementations:
   - `partial_config_to_assumptions(config, variables, feature_ids)` — from QuAcqTask method
   - `config_to_assumptions(config, feature_ids)` — from QuAcqTask method (needed by FindC)
   - `get_constraint_vars(assumption_id, constraint_clauses, id_to_feature)` — from QuAcqTask._get_constraint_vars
   - `violates_clauses(clauses, assignment)` — from QuAcqTask.violates_clauses
   - `get_constraints_with_scope(scope, candidates, constraint_clauses, id_to_feature)` — from QuAcqTask method (needed by FindC)

3. **Update `find_scope()` signature**: Replace `task` param with `constraint_clauses`, `feature_ids`, `id_to_feature`.

4. **Update `find_scope()` body**: Replace all `task.*` calls with standalone function calls from `sat_utils`.

5. **Remove `_task_compat` import** from findscope.py.

6. **Update docstrings**.

## Todo List
- [ ] Create `conacq/algorithms/quacq/sat_utils.py` with shared utility functions
- [ ] Update `find_scope()` signature — raw params instead of task
- [ ] Replace task method calls with sat_utils function calls
- [ ] Remove `_task_compat` import
- [ ] Update docstrings
- [ ] Verify file under 150 LOC

## Success Criteria
- No `QuAcqTask` or `_task_compat` import in findscope.py
- `find_scope()` accepts raw data params
- All computation via standalone utility functions
- sat_utils.py under 100 LOC

## Risk Assessment
- **Medium risk**: Algorithm logic must produce identical results. Pure function extraction — testable independently.
- **Shared utility creation**: sat_utils.py is new file — must be properly integrated into package.

## Next Steps
- Phase 4 (FindC) uses same sat_utils.py functions
- Phase 5 wires new find_scope() signature from QuAcq.learn()
