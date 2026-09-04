# Phase 4: QuAcqModel get_kb()/get_assumptions() Include Part 4

## Context Links
- [Phase 3](phase-03-quacq-task-part4.md) (prerequisite)
- Source: `conacq/algorithms/quacq/quacq_model.py` lines 91-106

## Overview
- **Priority**: P1
- **Status**: complete
- **Description**: QuAcqModel.get_kb() and get_assumptions() return combined Part 3+4+5+6 data

## Key Insights
- CheckerFactory.create_from_model(model) calls `model.get_kb()` and `model.get_assumptions()`
- Currently get_kb() returns `task.set_kb` (Parts 5-6 bias + Part 3 root BG)
- Currently get_assumptions() returns `task.assumptions` (Parts 3+5+6)
- Need to include Part 4 assignment_clauses in KB and assignment_assumptions in assumptions
- This makes the checker aware of feature assignment guards

### Why this works
ConsistencyChecker._compute_delta(set_c):
- `enabled` = set_c (passed assumptions)
- `disabled` = self.assumptions \ set_c
- Disabled assumptions get negated: solver sees `-disabled_id`
- Guarded clause `[-disabled_id, fid]` becomes `[True, fid]` = trivially satisfied
- Only enabled assignment assumptions impose constraints

## Requirements

### Functional
- `get_kb()` returns `task.set_kb + task.assignment_clauses`
- `get_assumptions()` returns `list(task.assumptions) + task.assignment_assumptions`

### Non-functional
- CheckerModel protocol preserved (same method signatures)
- No new fields on QuAcqModel

## Architecture

```
Before:
  get_kb()          -> task.set_kb (Part 3 root + Parts 5-6 bias)
  get_assumptions() -> task.assumptions (Part 3 + Parts 5-6)

After:
  get_kb()          -> task.set_kb + task.assignment_clauses (Part 3 + Parts 5-6 + Part 4)
  get_assumptions() -> task.assumptions + task.assignment_assumptions (Parts 3+5+6 + Part 4)
```

## Related Code Files
- **Modify**: `conacq/algorithms/quacq/quacq_model.py` (lines 91-106)

## Implementation Steps

### Step 1: Update get_kb() (line 91-93)

Current:
```python
def get_kb(self) -> List[List]:
    """Get the full knowledge base with assumptions."""
    return self._require_task().set_kb
```

New:
```python
def get_kb(self) -> List[List]:
    """Get full KB: bias + root BG + Part 4 assignment clauses."""
    task = self._require_task()
    return task.set_kb + task.assignment_clauses
```

### Step 2: Update get_assumptions() (line 104-106)

Current:
```python
def get_assumptions(self) -> List:
    """Get the list of assumption literals."""
    return self._require_task().assumptions
```

New:
```python
def get_assumptions(self) -> List:
    """Get all assumptions: bias + root BG + Part 4 assignments."""
    task = self._require_task()
    return list(task.assumptions) + task.assignment_assumptions
```

Note: `list(task.assumptions)` creates a copy (task.assumptions is a mutable list from DiagnosisTask).

## Todo List
- [ ] Update get_kb() to include assignment_clauses
- [ ] Update get_assumptions() to include assignment_assumptions
- [ ] Update docstrings
- [ ] Verify CheckerFactory.create_from_model(model) still works

## Success Criteria
- `model.get_kb()` includes Part 4 unit clauses
- `model.get_assumptions()` includes Part 4 assignment IDs
- CheckerFactory creates checker with combined KB+assumptions
- Checker.is_consistent([root_assumption] + [pos_map[feat]...] + [aid]) works correctly

## Risk Assessment
- **Medium**: This changes checker behavior -- Part 4 clauses now in KB
- Disabled Part 4 assumptions auto-satisfy their guarded clauses (by checker's _compute_delta)
- Must verify Reduce still works (Part 4 all disabled = no effect on bias consistency)

### Mitigation
- Part 4 guarded clauses are unit implications: `[-a, fid]` or `[-a, -fid]`
- When a is disabled (-a is true), clause trivially satisfied
- Reduce only passes `set_b_prime` (learned bias) + `set_bg` (root BG) -- no Part 4 IDs
- So Part 4 assumptions all disabled during Reduce = no effect

## Security Considerations
- None

## Next Steps
- Phase 5: Replace violates_clauses with checker.is_consistent in _prune
