# Phase 2: Fix BG Handling in `_find_conflict` and `QueryGenerator`

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-bg-clauses-field.md)
- Review: Issue #1 + #4

## Overview
- **Priority**: Critical
- **Status**: complete
- **Description**: Update `_find_conflict` and `QueryGenerator._try_generate_for_constraint` to use `background_clauses` for QuAcqTask instead of misinterpreting assumption IDs as SAT literals.

## Related Code Files

- **Modify**: `conacq/algorithms/interactive/quacq.py` (lines 352-357)
- **Modify**: `conacq/example_generators/query_generator.py` (lines 78, 104-109)

## Implementation Steps

### 1. Fix `_find_conflict` in quacq.py (lines 350-357)

Replace:
```python
bg_clauses = task.get_kb_clauses()

if task.background:
    if isinstance(task.background[0], int):
        for lit in task.background:
            bg_clauses.append([lit])
    else:
        bg_clauses.extend(task.background)
```

With:
```python
bg_clauses = task.get_kb_clauses()

if hasattr(task, 'background_clauses') and task.background_clauses:
    bg_clauses.extend(task.background_clauses)
elif task.background:
    if isinstance(task.background[0], int):
        for lit in task.background:
            bg_clauses.append([lit])
    else:
        bg_clauses.extend(task.background)
```

### 2. Fix `QueryGenerator.generate()` — pass raw clauses (query_generator.py line 78)

Replace:
```python
bg_clauses=task.background,
```

With:
```python
bg_clauses=(task.background_clauses if hasattr(task, 'background_clauses') and task.background_clauses else task.background),
```

### 3. Fix `_try_generate_for_constraint` (query_generator.py lines 104-109)

The `bg_clauses` parameter now receives either raw clauses (from QuAcqTask) or the old format. Update:

Replace:
```python
if bg_clauses:
    if isinstance(bg_clauses[0], int):
        for lit in bg_clauses:
            all_clauses.append([lit])
    else:
        all_clauses.extend(bg_clauses)
```

With:
```python
if bg_clauses:
    if isinstance(bg_clauses[0], int):
        # Legacy InteractiveTask: background is list of feature variable IDs
        for lit in bg_clauses:
            all_clauses.append([lit])
    else:
        # QuAcqTask: background_clauses is list of raw CNF clauses
        all_clauses.extend(bg_clauses)
```

Note: The `_try_generate_for_constraint` body itself doesn't need structural change — the fix is in the caller (step 2) which now passes the correct data. The branch logic is preserved for backward compat with legacy InteractiveTask.

## Todo

- [x] Fix `_find_conflict` BG handling
- [x] Fix `QueryGenerator.generate()` to pass `background_clauses`
- [x] Verify `_try_generate_for_constraint` receives correct clause format

## Success Criteria

- QuAcqTask oracle-mode: BG clauses correctly included in SAT formulas
- Legacy InteractiveTask: unchanged behavior (still wraps int as unit clause)
- REDUCE path: unchanged (still uses `task.background` assumption IDs)

## Risk Assessment

- **Medium**: Behavioral change in oracle-mode path — BG constraints now enforced
- **Verify**: Run oracle-mode tests to confirm queries respect BG constraints
