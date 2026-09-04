# Phase 2: Rename background → set_b Across Codebase

## Context
- Parent plan: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-refactor-quacqtask.md)

## Overview
- **Priority**: High (must follow Phase 1)
- **Description**: Replace all `task.background` / `self.task.background` refs with `task.set_b` / `self.task.set_b`
- **Status**: completed

## Related Code Files

All changes are `background` → `set_b` renames:

### conacq/algorithms/interactive/quacq.py (2 refs)
- Line 309: `set_bg=task.background` → `set_bg=task.set_b`
- Line 462-463: `if task.background: for lit in task.background:` → `if task.set_b: for lit in task.set_b:`

### conacq/algorithms/interactive/learner.py (1 ref)
- Line 312: `self.task.background` → `self.task.set_b` (2 occurrences on same line)

### conacq/algorithms/interactive/_task_compat.py (3 refs)
- Line 34: `task.background` → `task.set_b`
- Line 35: `task.background[0]` → `task.set_b[0]`
- Line 36: `task.background` → `task.set_b`

### conacq/example_generators/query_generator.py (1 ref)
- Line 67: `task.background` → `task.set_b`

### conacq/algorithms/interactive/task.py (deprecated InteractiveTask)
- Line 54-55: `background` field declaration → rename to `set_b` for consistency
- Line 197: `background=self.background.copy()` → `set_b=self.set_b.copy()` in clone()
- Update docstring attribute name

## Implementation Steps

1. Rename in quacq.py (2 locations)
2. Rename in learner.py (1 location)
3. Rename in _task_compat.py (3 locations)
4. Rename in query_generator.py (1 location)
5. Rename in task.py InteractiveTask (field + clone + docstring)

## Todo List
- [x] quacq.py: 2 renames
- [x] learner.py: 1 rename
- [x] _task_compat.py: 3 renames
- [x] query_generator.py: 1 rename
- [x] task.py (InteractiveTask): field + clone + docstring

## Success Criteria
- No remaining references to `.background` (except `background_clauses`)
- All code uses `.set_b` for BG assumption IDs
