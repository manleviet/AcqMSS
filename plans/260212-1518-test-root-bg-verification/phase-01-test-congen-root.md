# Phase 1: Test CONGEN Root in set_b and bg_clauses

## Context Links
- Parent: [plan.md](./plan.md)
- File: `tests/test_congen.py`
- Source: `acqmss/algorithms/task_preparation.py`, `acqmss/algorithms/congen.py`

## Overview
**Priority**: P2 | **Status**: Complete | **Effort**: 20min

Add assertions to existing CONGEN tests to verify root propagation.

## Key Insights
- `create_checker_and_task()` helper at line 67 doesn't pass `root_feature_id` to `CONGENModel.from_bias_and_examples()`
- Need to update helper to pass root, then assert set_b and bg_clauses
- Root feature name from `oracle.get_root_feature()`, ID from `oracle.get_feature_ids()[root_name]`

## Related Code Files
**Modify**: `tests/test_congen.py`

## Implementation Steps

### Step 1: Update `create_checker_and_task()` helper (line 67-110)
1. Extract root: `root_name = oracle.get_root_feature()` and `root_id = oracle.get_feature_ids()[root_name]`
2. Pass `root_feature_id=root_id` to `CONGENModel.from_bias_and_examples()`
3. Return root_id along with checker, task, profiler → `return checker, task, profiler, root_id`

### Step 2: Update callers
All test methods calling `create_checker_and_task()` need to unpack 4 values instead of 3.

### Step 3: Add assertions in existing tests
In `test_congen_incremental_with_rs_examples`:
```python
# Verify root in set_b (incremental: List[int])
assert root_id in task.set_b, "Root should be in set_b"
# Verify bg_clauses in result
assert [root_id] in result.bg_clauses, "Root clause should be in bg_clauses"
```

In `test_congen_non_incremental_with_rs_examples`:
```python
# Verify root in set_b (non-incremental: List[List[List[int]]])
assert [[root_id]] in task.set_b, "Root should be in set_b"
# Verify bg_clauses in result
assert [root_id] in result.bg_clauses, "Root clause should be in bg_clauses"
```

## Todo List
- [x] Update `create_checker_and_task()` to pass root_feature_id
- [x] Update all callers to unpack 4 values
- [x] Add set_b assertions in incremental tests
- [x] Add set_b assertions in non-incremental tests
- [x] Add bg_clauses assertions in result checks

## Success Criteria
- `task.set_b` contains root in both modes
- `result.bg_clauses` contains `[[root_id]]`
- All existing tests still pass
