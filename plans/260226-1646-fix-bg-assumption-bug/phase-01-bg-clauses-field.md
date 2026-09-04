# Phase 1: Add `background_clauses` Field + Populate

## Context
- Parent: [plan.md](plan.md)
- Review: `plans/reports/code-reviewer-260226-1637-quacq-assumption-migration.md` Issue #1

## Overview
- **Priority**: Critical
- **Status**: complete
- **Description**: Add `background_clauses` field to `QuAcqTask` for raw BG CNF clauses. Populate from `bg_data.set_kb` in `InteractiveTaskPreparation.prepare()`.

## Key Insights

- `bg_data.set_kb` contains assumption-guarded clauses: `[...lits..., -assumption_id]`
- `bg_data.assumptions = (root_aid, neg_root_aid)` — pair of IDs
- For raw SAT path, only root constraint clauses needed (not negated form)
- Filter by `clause[-1] == -root_aid` to get only root constraint clauses, then strip guard

## Related Code Files

- **Modify**: `conacq/algorithms/interactive/quacq_task.py` (lines 48-49, 163-180)
- **Modify**: `conacq/algorithms/interactive/interactive_task_preparation.py` (lines 50-58)

## Implementation Steps

### 1. Add field to `QuAcqTask` (quacq_task.py)

After line 49 (`background: List[int]`), add:
```python
# Raw BG clauses (WITHOUT assumption guards, for SAT discrimination paths)
background_clauses: List[List[int]] = field(default_factory=list)
```

### 2. Update `clone()` method (quacq_task.py line ~171)

Add to clone:
```python
background_clauses=[c.copy() for c in self.background_clauses],
```

### 3. Populate in `InteractiveTaskPreparation.prepare()` (interactive_task_preparation.py)

After line 57 (`result.background = list(bg_data.assumptions)`), add:
```python
# Extract raw BG clauses: strip assumption guard from root constraint clauses only
root_aid = bg_data.assumptions[0]
result.background_clauses = [
    clause[:-1] for clause in bg_data.set_kb
    if clause[-1] == -root_aid
]
```

This filters `bg_data.set_kb` to only include clauses guarded by the root assumption ID (not the negated root), then strips the guard literal.

## Todo

- [x] Add `background_clauses` field to QuAcqTask
- [x] Update `clone()` to copy `background_clauses`
- [x] Populate `background_clauses` in InteractiveTaskPreparation.prepare()

## Success Criteria

- `QuAcqTask.background_clauses` contains raw root constraint clauses (no guards)
- `QuAcqTask.background` still contains assumption IDs (unchanged)
- Existing tests pass unchanged

## Risk Assessment

- **Low**: Additive change — new field with default empty list, no existing behavior altered
- **Verify**: `bg_data.set_kb` clause guard format matches `[-assumption_id]` pattern
