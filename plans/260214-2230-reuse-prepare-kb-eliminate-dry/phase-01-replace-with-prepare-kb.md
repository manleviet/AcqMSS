# Phase 01: Replace _prepare_bias_constraints with prepare_kb

## Context

- Parent plan: [plan.md](plan.md)
- `prepare_kb`: `explanation/models/task_preparation.py:242-287`
- `_prepare_bias_constraints`: `acqmss/algorithms/task_preparation.py:63-112`
- Caller: `ConGenTaskPreparation.prepare()` at line 232

## Overview

- Priority: P3
- Status: completed
- Replace `_prepare_bias_constraints` with `prepare_kb` from explanation module, then build bidirectional maps in post-processing.

## Key Insights

- `prepare_kb` handles Optional `negated_constraint_map` with `is not None` check — compatible
- ID assignment is deterministic: each constraint gets +1, each negated form gets +1
- `ConGenTask` inherits all fields `prepare_kb` accesses (`set_kb`, `assumptions`, `neg_c_map`)

## Related Code Files

**Modify:**
- `acqmss/algorithms/task_preparation.py`

**No changes needed:**
- `explanation/models/task_preparation.py`

## Implementation Steps

### Step 1: Add `prepare_kb` to imports

In `acqmss/algorithms/task_preparation.py`, add `prepare_kb` to the existing import block:

```python
from explanation.models.task_preparation import (
    TestCaseTask,
    TestCaseTaskPreparationStrategy,
    DescriptionProvider,
    PreparationOutput,
    prepare_testsuite_with_negation,
    prepare_kb,  # ADD THIS
)
```

### Step 2: Create post-processing helper

Add a new function `_build_constraint_maps` that builds bidirectional maps from sequential IDs:

```python
def _build_constraint_maps(
        result: ConGenTask,
        constraint_map: Dict[str, List[List[int]]],
        negated_constraint_map: Optional[Dict[str, List[List[int]]]],
        start_id: int
) -> None:
    """Build bidirectional constraint-assumption maps from sequential IDs.

    Must mirror prepare_kb's ID assignment: +1 per constraint, +1 per negated form.
    """
    aid = start_id
    for name in constraint_map:
        result.constraint_to_assumption[name] = aid
        result.assumption_to_constraint[aid] = name
        aid += 1
        # Skip negated form's ID if it exists
        if negated_constraint_map is not None:
            negated_key = f"NOT({name})"
            if negated_key in negated_constraint_map:
                aid += 1
```

### Step 3: Update `ConGenTaskPreparation.prepare()`

Replace lines 232-234:

**Before:**
```python
id_assumption = _prepare_bias_constraints(
    result, provider, model.constraint_map,
    model.negated_constraint_map, id_assumption)
```

**After:**
```python
bias_start_id = id_assumption
id_assumption = prepare_kb(
    result, provider, model.constraint_map,
    bias_start_id, model.negated_constraint_map)
_build_constraint_maps(
    result, model.constraint_map,
    model.negated_constraint_map, bias_start_id)
```

Note: `prepare_kb` signature is `(result, provider, constraint_map, id_assumption, negated_constraint_map)` — `id_assumption` is 4th param (before negated map).

### Step 4: Remove `_prepare_bias_constraints`

Delete the entire function (lines 63-112).

### Step 5: Add Optional to imports

`_build_constraint_maps` uses `Optional` — add to typing imports if not already present.

## Todo

- [x] Add `prepare_kb` to imports
- [x] Create `_build_constraint_maps` helper
- [x] Update caller in `ConGenTaskPreparation.prepare()`
- [x] Remove `_prepare_bias_constraints`
- [x] Verify Optional is imported

## Success Criteria

- `_prepare_bias_constraints` fully removed
- `prepare_kb` reused from explanation module
- Both `constraint_to_assumption` and `assumption_to_constraint` populated correctly
- All existing tests pass unchanged

## Risk Assessment

- **ID mismatch**: If `prepare_kb` changes ID assignment order, maps will be wrong. Mitigate: test assertion comparing old vs new behavior.
- **Import cycle**: Already importing from `explanation.models.task_preparation` — no new cycle risk.
