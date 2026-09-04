# Phase 1: Add get_constraint_vars() to QuAcqModel

## Context
- Parent: [plan.md](plan.md)
- Brainstorm: [brainstorm report](../reports/brainstorm-260228-0709-discriminating-generator-checker-refactor.md)
- Ref: `sat_utils.get_constraint_vars()` — same logic, encapsulated in model

## Overview
- **Priority**: High (blocks Phase 2)
- **Status**: Complete
- **Description**: Add `get_constraint_vars(assumption_id)` method to QuAcqModel for scope filtering

## Key Insights
- `sat_utils.get_constraint_vars()` takes 3 args: assumption_id, constraint_clauses, id_to_feature
- Model already has access to task.constraint_clauses and task.id_to_feature via `_require_task()`
- Encapsulating in model eliminates need for raw data dict passing

## Requirements
- Method signature: `get_constraint_vars(self, assumption_id: int) -> Set[str]`
- Returns set of feature names used by constraint
- Uses task.constraint_clauses and task.id_to_feature internally
- Type hints mandatory (code-standards)

## Related Code Files
- **Modify**: `conacq/algorithms/quacq/quacq_model.py` (add method after `config_to_assumptions`)
- **Reference**: `conacq/algorithms/quacq/sat_utils.py` lines 33-44 (existing logic)

## Implementation Steps
1. Add `Set` to typing imports in quacq_model.py (if not already imported)
2. Add `get_constraint_vars()` method to QuAcqModel class after `config_to_assumptions()`
3. Implementation:
   ```python
   def get_constraint_vars(self, assumption_id: int) -> Set[str]:
       """Get feature names for constraint by assumption ID."""
       task = self._require_task()
       clauses = task.constraint_clauses.get(assumption_id, [])
       return {task.id_to_feature[abs(lit)]
               for clause in clauses for lit in clause
               if abs(lit) in task.id_to_feature}
   ```

## Todo
- [x] Add `Set` to imports
- [x] Add `get_constraint_vars()` method
- [x] Verify no syntax errors

## Success Criteria
- Method returns correct feature name set for given assumption_id
- Type hints present
- No import errors
