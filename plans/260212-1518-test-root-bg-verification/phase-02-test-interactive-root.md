# Phase 2: Test InteractiveTask Background

## Context Links
- Parent: [plan.md](./plan.md)
- File: `tests/test_interactive.py`
- Source: `acqmss/algorithms/interactive/learner.py`

## Overview
**Priority**: P2 | **Status**: Complete | **Effort**: 15min

Verify `_build_task_from_bias()` sets `background=[root_id]`.

## Key Insights
- `interactive_task` fixture at line 53-79 constructs task manually with `background=[]`
- Tests using `InteractiveLearner.from_files()` already get root via `_build_task_from_bias()`
- Need to: (a) update fixture or (b) add separate assertion in learner tests

## Related Code Files
**Modify**: `tests/test_interactive.py`

## Implementation Steps

### Step 1: Add assertion in `test_learner_from_files`
After `learner = InteractiveLearner.from_files(...)`, assert:
```python
# Verify root in background
assert len(learner.task.background) > 0, "Background should contain root"
root_name = oracle.get_root_feature()
root_id = oracle.get_feature_ids()[root_name]
assert root_id in learner.task.background, "Root feature ID should be in background"
```

### Step 2: Add dedicated test `test_build_task_from_bias_includes_root`
```python
def test_build_task_from_bias_includes_root(self, oracle, bias):
    """Verify _build_task_from_bias sets background with root."""
    task = InteractiveLearner._build_task_from_bias(bias, oracle)
    root_name = oracle.get_root_feature()
    root_id = oracle.get_feature_ids()[root_name]
    assert task.background == [root_id]
```

## Todo List
- [x] Add root assertion in `test_learner_from_files`
- [x] Add `test_build_task_from_bias_includes_root`
- [x] Verify fixture-based tests unaffected

## Success Criteria
- `task.background == [root_id]` from `_build_task_from_bias()`
- All interactive tests pass
