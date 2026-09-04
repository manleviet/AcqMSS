# Phase 1: Update ConGenTask & Merge Function

## Context Links

- [Impact Analysis](reports/impact-analysis.md)
- [plan.md](plan.md)

## Overview

- **Priority**: High (foundation for phases 2-3)
- **Status**: complete
- **Description**: Remove `set_ne` field from `ConGenTask`, fix docstring to reflect `set_neg_tv` usage, update `merge_ne_into_task()`.

## Key Insights

- `set_neg_tv` already inherited from `TestCaseTask` (explanation/models/task_preparation.py:119)
- `ConGenTask` docstring at line 38-39 says `set_neg_tv` has "no use" — must correct
- `merge_ne_into_task()` writes to `task.set_ne` — must write to `task.set_neg_tv`
- `ConGenModel.get_ne()` returns `task.set_ne` — remove it, `get_neg_tv()` already exists

## Requirements

### Functional
- Remove `set_ne` field from `ConGenTask` dataclass
- Update `merge_ne_into_task()` to populate `task.set_neg_tv`
- Remove `ConGenModel.get_ne()` method
- Update ConGenModel docstrings

### Non-Functional
- No behavioral changes
- Backward-compatible data flow (same assumption IDs, same list)

## Architecture

```
Before: ConGenTask has both set_neg_tv (unused) AND set_ne (used)
After:  ConGenTask uses inherited set_neg_tv (no set_ne)

merge_ne_into_task():
  Before: task.set_ne = ne_result.assumption_ids
  After:  task.set_neg_tv = ne_result.assumption_ids
```

## Related Code Files

### Modify
- `acqmss/algorithms/task_preparation.py` — ConGenTask class
- `acqmss/algorithms/generate_ne.py` — merge_ne_into_task()
- `acqmss/algorithms/congen_model.py` — get_ne() removal

### Reference Only
- `explanation/models/task_preparation.py` — TestCaseTask.set_neg_tv definition (no change)

## Implementation Steps

### Step 1: Update ConGenTask (task_preparation.py)

1. Remove line 51: `set_ne: List[int] = field(default_factory=list)`
2. Update docstring (lines 28-49):
   - Remove "Inherits from TestCaseTask but no use: - set_neg_tv" (lines 38-39)
   - Add under inherited fields: `- set_neg_tv: Negated negative examples (NE) - populated by GenerateNE`
   - Remove "Additional ConGen-specific fields: - set_ne: NE assumption IDs (computed by GenerateNE)" (lines 43-44)

### Step 2: Update merge_ne_into_task (generate_ne.py)

1. Line 128: Change docstring `- set_ne: NE assumption IDs` to `- set_neg_tv: NE assumption IDs`
2. Line 138: Change `task.set_ne = ne_result.assumption_ids` to `task.set_neg_tv = ne_result.assumption_ids`

### Step 3: Update ConGenModel (congen_model.py)

1. Remove `get_ne()` method (lines 162-170)
2. Update `prepare()` docstring line 189: `ConGenTask with set_ne already populated` -> `ConGenTask with set_neg_tv already populated`

## Todo List

- [ ] Remove `set_ne` field from ConGenTask dataclass
- [ ] Fix ConGenTask docstring (remove "no use" for set_neg_tv, document it properly)
- [ ] Update merge_ne_into_task() to write to set_neg_tv
- [ ] Remove ConGenModel.get_ne() method
- [ ] Update ConGenModel.prepare() docstring

## Success Criteria

- `ConGenTask` no longer has `set_ne` attribute
- `merge_ne_into_task()` writes to `task.set_neg_tv`
- `ConGenModel` has `get_neg_tv()` but no `get_ne()`
- No runtime errors when ConGenModel.prepare() is called

## Risk Assessment

- **Low**: Pure field removal + rename. `set_neg_tv` already exists on parent.
- **Dependency**: Phase 2 must complete before tests pass (callers still reference `task.set_ne`)

## Security Considerations

- None — internal data structure refactoring only

## Next Steps

Phase 2: Update all algorithm parameter names and caller sites.
