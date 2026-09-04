# Phase 4: Refactor FindC

## Context Links
- [Plan overview](plan.md)
- [QuAcq Internals research](research/researcher-01-quacq-internals.md)
- Source: `conacq/algorithms/quacq/findc.py` (208 LOC)
- Consumer: `QuAcq.learn()` calls `find_c()`
- Depends on: Phase 1 (DiscriminatingGenerator), Phase 3 (sat_utils.py created)
<!-- Updated: Validation Session 1 - NEW phase: FindC refactored to raw params -->

## Overview
- **Priority:** High (blocks Phase 5)
- **Status:** complete
- **Description:** Remove QuAcqTask dependency from `find_c()`. Accept raw data params + sat_utils functions.

## Key Insights
- `find_c()` is a module-level function
- Task fields accessed: `get_constraints_with_scope()`, `config_to_assumptions()`, `violates_clauses()`, `constraint_clauses` (via `get_clause_map`)
- Uses `generator.generate(c_i, c_j, learned_kb, scope)` — generator already refactored in Phase 1
- `get_constraints_with_scope()` filters candidates by scope overlap — pure function on constraint_clauses + id_to_feature
- `config_to_assumptions()` converts full config → assumption literals
- All needed utilities already in `sat_utils.py` from Phase 3

## Requirements

### Functional
- `find_c()` accepts raw data params instead of `task`
- No import of `QuAcqTask` or `_task_compat` in this file
- Use `sat_utils` functions for computation
- `generator` param unchanged (already refactored DiscriminatingGenerator)

### Non-Functional
- File stays under 220 LOC
- Type hints on all public functions

## Architecture

### Before
```python
def find_c(e, scope, task, remaining_bias, record_query, oracle, learned_kb,
           generator, profiler, description_provider=None, ...):
    # uses: task.get_constraints_with_scope(scope, remaining_bias)
    # uses: task.config_to_assumptions(e)
    # uses: task.violates_clauses(clauses, assignment)
    # uses: get_clause_map(task) -> task.constraint_clauses
```

### After
```python
def find_c(e, scope,
           constraint_clauses: Dict[int, List[List[int]]],
           feature_ids: Dict[str, int],
           id_to_feature: Dict[int, str],
           remaining_bias, record_query, oracle, learned_kb,
           generator, profiler, description_provider=None, ...):
    # uses: get_constraints_with_scope(scope, remaining_bias, constraint_clauses, id_to_feature)
    # uses: config_to_assumptions(e, feature_ids)
    # uses: violates_clauses(clauses, assignment)
    # uses: constraint_clauses directly
```

## Related Code Files
- **Modify:** `conacq/algorithms/quacq/findc.py`
- **Use:** `conacq/algorithms/quacq/sat_utils.py` (created in Phase 3)

## Implementation Steps

1. **Import sat_utils**: `from .sat_utils import config_to_assumptions, get_constraints_with_scope, violates_clauses`

2. **Update `find_c()` signature**: Replace `task` with `constraint_clauses`, `feature_ids`, `id_to_feature`.

3. **Update `find_c()` body**:
   - Replace `task.get_constraints_with_scope(scope, remaining_bias)` → `get_constraints_with_scope(scope, remaining_bias, constraint_clauses, id_to_feature)`
   - Replace `task.config_to_assumptions(e)` → `config_to_assumptions(e, feature_ids)`
   - Replace `task.violates_clauses(clauses, assignment)` → `violates_clauses(clauses, assignment)`
   - Replace `get_clause_map(task)` → `constraint_clauses` directly

4. **Update internal helper `_narrow_with_generator`** if it passes task — verify and update.

5. **Remove `_task_compat` import**.

6. **Update docstrings**.

## Todo List
- [ ] Import sat_utils functions
- [ ] Update `find_c()` signature — raw params instead of task
- [ ] Replace task method calls with sat_utils calls
- [ ] Update `_narrow_with_generator` if needed
- [ ] Remove `_task_compat` import
- [ ] Update docstrings
- [ ] Verify file under 220 LOC

## Success Criteria
- No `QuAcqTask` or `_task_compat` import in findc.py
- `find_c()` accepts raw data params
- Algorithm produces identical results

## Risk Assessment
- **Medium risk**: `find_c` has more complex logic than `find_scope` (pool-based narrowing + SAT fallback). Must verify all paths use sat_utils correctly.
- **Low coupling risk**: generator.generate() unchanged, oracle.is_valid() unchanged.

## Next Steps
- Phase 5 wires new find_c() signature from QuAcq.learn()
