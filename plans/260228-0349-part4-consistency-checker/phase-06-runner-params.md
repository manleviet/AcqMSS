# Phase 6: Update _learn_params_from_task and Fix Runner Bugs

## Context Links
- [Phase 5](phase-05-prune-with-checker.md) (prerequisite)
- Source: `conacq/runners/quacq_runner.py` lines 51-64, 232-284

## Overview
- **Priority**: P1
- **Status**: complete
- **Description**: Update runner to pass Part 4 params + fix pre-existing bugs

## Key Insights

### Bug 1: _learn_params_from_task has stale keys
Current (line 51-64) includes `set_kb` and `assumptions` which were removed from learn() signature in working tree changes. These would cause TypeError on `**task_data` expansion.

### Bug 2: _run_oracle_mode missing checker
Line 248: `QuAcq.for_oracle(learn_oracle, query_gen, discrim_gen, profiler=profiler)` -- missing `checker` as first arg. The factory now requires `checker` as first positional argument (working tree change).

### New: Pass Part 4 data
`_learn_params_from_task` must include `pos_assignment_to_assumption`, `neg_assignment_to_assumption`, and `root_assumption`.

## Requirements

### Functional
- Fix `_learn_params_from_task`: remove `set_kb`, `assumptions`; add Part 4 fields
- Fix `_run_oracle_mode`: pass `checker` to `QuAcq.for_oracle()`
- `root_assumption` = `task.set_b[0]` (first BG assumption = root)

### Non-functional
- Both oracle and example mode paths pass Part 4 data

## Architecture

```
_learn_params_from_task(task) -> dict matching learn() signature:
  set_c, set_b, negation_map, background_clauses,
  feature_ids, id_to_feature, constraint_clauses, negated_clauses,
  pos_assignment_to_assumption, neg_assignment_to_assumption, root_assumption
```

## Related Code Files
- **Modify**: `conacq/runners/quacq_runner.py`

## Implementation Steps

### Step 1: Fix _learn_params_from_task (line 51-64)

Replace entire function:
```python
def _learn_params_from_task(task) -> dict:
    """Extract flat learn() params from QuAcqTask."""
    return dict(
        set_c=task.set_c,
        set_b=task.set_b,
        negation_map=task.negation_map,
        background_clauses=task.background_clauses,
        feature_ids=task.feature_ids,
        id_to_feature=task.id_to_feature,
        constraint_clauses=task.constraint_clauses,
        negated_clauses=task.negated_clauses,
        pos_assignment_to_assumption=task.pos_assignment_to_assumption,
        neg_assignment_to_assumption=task.neg_assignment_to_assumption,
        root_assumption=task.set_b[0] if task.set_b else None,
    )
```

### Step 2: Fix _run_oracle_mode (line 248)

Current (broken):
```python
quacq = QuAcq.for_oracle(learn_oracle, query_gen, discrim_gen, profiler=profiler)
```

Fixed:
```python
quacq = QuAcq.for_oracle(checker, learn_oracle, query_gen, discrim_gen, profiler=profiler)
```

### Step 3: Fix test helper _learn_params_from_task in test_quacq.py (line 43-56)

Same changes as Step 1. The test file has its own copy of this function.

## Todo List
- [ ] Fix _learn_params_from_task in runner: remove set_kb/assumptions, add Part 4
- [ ] Fix _run_oracle_mode: pass checker as first arg
- [ ] Fix _learn_params_from_task in test_quacq.py
- [ ] Verify both mode paths work end-to-end

## Success Criteria
- `_learn_params_from_task` keys match learn() params exactly
- `_run_oracle_mode` passes checker to QuAcq.for_oracle()
- No TypeError on `**task_data` expansion
- Both oracle and example modes pass Part 4 data to learn()

## Risk Assessment
- **Medium**: fixing existing bugs + adding new params
- Must update test helper in sync

### Mitigation
- The test helper must match runner helper exactly
- Run full test suite after changes

## Security Considerations
- None

## Next Steps
- Phase 7: Update tests
