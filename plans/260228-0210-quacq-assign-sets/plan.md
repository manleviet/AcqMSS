---
status: completed
date: 2026-02-28
slug: quacq-assign-sets
---

# QuAcq _assign_sets Refactoring

## Summary

Extract `set_b` and `set_c` assignment from `QuAcqTaskPreparation.prepare()` into a dedicated `_assign_sets()` method, matching the structural pattern used in `ConGenTaskPreparation`.

## Context

- `ConGenTaskPreparation.prepare()` delegates set assignment to `_assign_sets(result, bias, tc, tv, has_neg)`
- `QuAcqTaskPreparation.prepare()` assigns `set_b` inline in Step 0 and `set_c` inline in Step 3
- Goal: structural consistency between both preparations

## Files to Modify

- `conacq/algorithms/quacq/task_preparation.py` — the only file

## Implementation Steps

### Step 1: Add `_assign_sets` method to `QuAcqTaskPreparation`

Add after `prepare()`:

```python
def _assign_sets(self, result: QuAcqTask, bias_start_pos: int) -> None:
    """Assign set_b and set_c from assumptions."""
    result.set_b = [result.assumptions[0]]
    result.set_c = list(result.assumptions[bias_start_pos::_ASSUMPTION_PAIR_STRIDE])
```

### Step 2: Update `prepare()` method

1. Remove `result.set_b = [bg_data.assumptions[0]]` from Step 0
2. Replace Step 3 inline `set_c` assignment with `self._assign_sets(result, bias_start_pos)`
3. Move `result.background_clauses` assignment before `_assign_sets` call (cleaner flow)
4. Keep Step 4 (constraint_clauses/negated_clauses loop) inline

### Step 3: Verify

- Run `PYTHONPATH=. pytest tests/test_quacq.py -v` to confirm no behavioral change

## Success Criteria

- [x] `_assign_sets` method exists on `QuAcqTaskPreparation`
- [x] `prepare()` no longer assigns `set_b`/`set_c` inline
- [x] All QuAcq tests pass
- [x] Pattern matches ConGen approach (dedicated method for set assignment)

## Risk Assessment

**Low risk** — pure structural refactoring, no logic change. Same values computed from same data.
