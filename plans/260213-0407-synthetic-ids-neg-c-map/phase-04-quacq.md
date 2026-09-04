# Phase 4: Update QuAcq

## Context Links
- [Phase 1: Checker Interface](phase-01-checker-interface.md)
- [Phase 3: Algorithm Simplification](phase-03-algorithm-simplification.md)
- Source: `acqmss/algorithms/interactive/quacq.py`

## Overview
- **Priority**: Medium
- **Status**: COMPLETE
- **Description**: QuAcq creates its own `NonIncrementalPySATChecker` and
  builds ad-hoc `neg_map` for Reduce. Update to use assumption-based checker
  and simplified Reduce signature.

## Key Insights
- QuAcq's `_reduce_kb()` (line 379) builds `neg_map` from `task.constraint_map`
  and `task.negated_constraint_map`. Currently uses string keys.
- QuAcq creates `NonIncrementalPySATChecker` at line 384 for its Reduce call.
  After Phase 1, this needs `set_kb`/`assumptions`.
- QuAcq's interactive task (`InteractiveTask`) has its own preparation.
  It may need assumption-based output too.
- After Phase 3, Reduce expects `neg_map: Dict[int, int]` only.

## Requirements
1. `_reduce_kb()` builds assumption-based `set_kb`/`assumptions` for checker
2. `neg_map` becomes `Dict[int, int]`
3. Reduce call uses simplified signature (no side maps)
4. Reverse mapping from assumption IDs to constraint names for results

## Related Code Files
- **Modify**: `acqmss/algorithms/interactive/quacq.py` -- `QuAcq._reduce_kb()`

## Implementation Steps

### Step 1: Rewrite `_reduce_kb()` to build assumption-based data

```python
def _reduce_kb(self, task):
    neg_map = {}              # Dict[int, int]
    id_to_name = {}           # For reverse mapping results
    set_kb = []               # Clauses with embedded assumptions
    assumptions = []
    set_b_prime = []          # KB assumption IDs
    assumption_counter = 1

    for c_id in task.learned_kb:
        if c_id not in task.constraint_map:
            continue
        if c_id not in task.negated_constraint_map:
            continue

        clauses = task.constraint_map[c_id]
        neg_clauses = task.negated_constraint_map[c_id]

        # Embed original constraint
        orig_id = assumption_counter
        assumption_counter += 1
        for clause in clauses:
            set_kb.append(clause + [-orig_id])
        assumptions.append(orig_id)
        set_b_prime.append(orig_id)
        id_to_name[orig_id] = c_id

        # Embed negated constraint
        neg_id = assumption_counter
        assumption_counter += 1
        for neg_clause in neg_clauses:
            set_kb.append(neg_clause + [-neg_id])
        assumptions.append(neg_id)

        neg_map[orig_id] = neg_id

    # BG as assumptions
    set_bg = []
    if task.root_feature_id is not None:
        bg_id = assumption_counter
        assumption_counter += 1
        set_kb.append([task.root_feature_id, -bg_id])
        assumptions.append(bg_id)
        set_bg.append(bg_id)

    # Create checker with assumption data
    checker = NonIncrementalPySATChecker(
        set_kb, assumptions, 'glucose4', self.profiler)
    reduce = Reduce(checker, self.profiler)

    redundant, non_redundant = reduce.reduce(
        set_b_prime=set_b_prime,
        set_ne=[],
        set_bg=set_bg,
        neg_map=neg_map
    )

    checker.cleanup()

    # Map back to constraint names
    non_redundant_names = [id_to_name[a] for a in non_redundant
                           if a in id_to_name]
    return non_redundant_names
```

### Step 2: Update callers of `_reduce_kb()`
Verify the return value format hasn't changed (list of constraint names).
Callers should work as-is.

## Todo List
- [x] Rewrite `_reduce_kb()` with assumption-based data
- [x] Verify interactive tests pass
- [x] Verify learned KB constraint names resolve correctly

## Success Criteria
- `_reduce_kb()` uses assumption-based checker
- Reduce receives `Dict[int, int]` neg_map
- No string keys in any map
- Interactive eval produces same KB as before

## Risk Assessment
- **No dedicated unit tests for `_reduce_kb()`**: rely on integration tests.
- **InteractiveTask structure**: may need `set_kb`/`assumptions` if used
  elsewhere. Currently `_reduce_kb()` builds its own -- self-contained.
