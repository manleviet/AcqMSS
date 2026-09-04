# Phase 3: Update Tests

## Context
- Parent plan: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-refactor-quacqtask.md), [Phase 2](phase-02-rename-background.md)

## Overview
- **Priority**: High (validates refactoring)
- **Description**: Update test_interactive.py to use `set_b` instead of `background`, verify all tests pass
- **Status**: completed

## Related Code Files
- **Modify**: `tests/test_interactive.py`

## Rename Locations (7 refs)

- Line 325: `learner.task.background` → `learner.task.set_b`
- Line 328: `learner.task.background` → `learner.task.set_b`
- Line 342: `task.background` → `task.set_b`
- Line 343: `task.background` → `task.set_b`
- Line 701: `task.background` → `task.set_b`
- Line 703: `task.background` → `task.set_b`
- Line 934: `task.background` → `task.set_b`

Also update any `QuAcqTask(background=...)` constructor calls:
- Line ~786, ~893, ~930, ~939, ~944: change kwarg `background=` → `set_b=`

## Implementation Steps

1. Rename all `.background` → `.set_b` in assertions and references
2. Rename all `background=` kwargs in QuAcqTask constructors to `set_b=`
3. Run full test suite: `PYTHONPATH=. pytest tests/ -v`
4. Verify all tests pass

## Todo List
- [x] Rename 7 `.background` references to `.set_b`
- [x] Rename QuAcqTask constructor kwargs `background=` → `set_b=`
- [x] Run tests and verify all pass

## Success Criteria
- `PYTHONPATH=. pytest tests/test_interactive.py -v` — all tests pass
- `PYTHONPATH=. pytest tests/ -v` — full suite passes
- No remaining references to `.background` except `background_clauses`
