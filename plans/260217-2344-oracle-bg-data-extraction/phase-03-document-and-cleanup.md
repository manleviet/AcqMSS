# Phase 3: Document ID Layout + Cleanup

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 2](phase-02-refactor-congen-task-preparation.md)

## Overview
- **Priority**: Medium
- **Status**: complete
- **Description**: Document shared assumption ID layout in Oracle and ConGen classes, clean up dead code

## Implementation Steps

### 1. Add ID layout docstring to `OracleTaskPreparation.prepare()` in `fm_oracle_model.py`
```python
"""Prepare assumption-guarded clauses for Oracle FM validation.

Shared Assumption ID Layout (Oracle owns Parts 1-4):
  Part 1: Feature variable IDs (1..n)               <- FmToDiagPysat
  Part 2: Tseitin vars (negated FM constraints)      <- FmToDiagPysat
  Part 3: FM constraint assumptions (paired)         <- This method
           [root, NOT(root), c2, NOT(c2), ...]
  Part 4: Variable assignment assumptions (paired)   <- This method
           [f1=true, f1=false, f2=true, ...]

ConGen continues from Part 5 onward (see ConGenTaskPreparation).
BGData extracts Part 3's first pair (root BG) + end-of-Part-4 ID.
"""
```

### 2. Add ID layout docstring to `ConGenTaskPreparation.prepare()` in `task_preparation.py`
```python
"""Prepare ConGen task from model. BG from Oracle, oracle for GenerateNE.

Shared Assumption ID Layout (ConGen owns Parts 5-8):
  Parts 1-4: Owned by Oracle (see OracleTaskPreparation)
  Part 5: Tseitin vars (negated bias constraints)    <- This method
  Part 6: Bias constraint assumptions (paired)       <- This method
  Part 7: Positive test case assumptions (paired)    <- This method
  Part 8: NE + negated NE                            <- This method

ConGen starts from bg_data.next_available_id (end of Oracle Part 4).
Root BG (Part 3 first pair) is copied from Oracle via BGData.
"""
```

### 3. Clean up dead imports/references
- Verify no other files import `_prepare_bg` (it was module-private)
- Verify `FMData` imports remain only where needed (learner.py, fm_oracle.py, base.py, __init__.py)
- Remove any stale comments referencing old skip arithmetic

### 4. Update `conacq/oracle/__init__.py`
Ensure `BGData` is properly exported alongside existing types.

## Todo
- [ ] Add ID layout docstring to OracleTaskPreparation
- [ ] Add ID layout docstring to ConGenTaskPreparation
- [ ] Clean up dead imports/references
- [ ] Update oracle __init__.py exports
- [ ] Verify no stale comments

## Success Criteria
- ID layout documented in both Oracle and ConGen preparation classes
- No dead imports or stale references
- Code reads clearly without needing external context to understand ID allocation
