# Phase 3: Simplify FindC

## Context Links

- Phase 2: `phase-02-update-quacq.md`
- Source: `conacq/algorithms/quacq/findc.py` (192 LOC)
- Paper: Algorithm 3 (FindC uses DiscriminatingGenerator only)

## Overview

- **Date**: 2026-02-28
- **Priority**: P2
- **Status**: completed
- **Description**: Remove `_narrow_with_pool` and `example_provider` param from FindC. Paper Algorithm 3 uses only DiscriminatingGenerator for narrowing candidates.

## Key Insights

- Paper Algorithm 3 does NOT use pool in FindC -- only DiscriminatingGenerator (C_L[Y])
- `_narrow_with_pool` (lines 113-152) uses ExampleProvider which is being deleted
- `query_mode` param only controlled whether to use generator after pool -- with pool removed, generator is always used
- After removing pool narrowing, FindC flow: get candidates -> filter rejecting -> use DiscriminatingGenerator -> return first

## Requirements

### Functional
- Remove `_narrow_with_pool` function entirely (lines 113-152)
- Remove `example_provider` parameter from `find_c()`
- Remove `query_mode` parameter from `find_c()`
- Always use `_narrow_with_generator` when len(rejecting) > 1
- Remove ExampleProvider import

### Non-Functional
- File drops from 192 LOC to ~130 LOC
- Simpler API: fewer params, fewer code paths

## Architecture

Before:
```
find_c(..., example_provider=None, query_mode='example_only'):
    candidates = get_constraints_with_scope(...)
    rejecting = [c for c in candidates if violates(e, c)]
    if example_provider: _narrow_with_pool(...)
    if query_mode == 'example_first': _narrow_with_generator(...)
    return remaining[0]
```

After:
```
find_c(..., generator):
    candidates = get_constraints_with_scope(...)
    rejecting = [c for c in candidates if violates(e, c)]
    if generator: _narrow_with_generator(...)
    return remaining[0]
```

## Related Code Files

### Files to modify
- `conacq/algorithms/quacq/findc.py`

## Implementation Steps

### Step 1: Remove ExampleProvider import (line 19)

Delete:
```python
from conacq.example_generators import ExampleProvider
```

### Step 2: Update find_c signature (lines 23-37)

Replace entire signature:
```python
def find_c(
        e: dict,
        scope: set,
        constraint_clauses: Dict[int, List[List[int]]],
        feature_ids: Dict[str, int],
        id_to_feature: Dict[int, str],
        remaining_bias: set,
        record_query,
        oracle,
        learned_kb: list,
        generator,
        profiler: AbstractProfiler = None
):
```

Remove: `example_provider`, `query_mode` params.

### Step 3: Update find_c docstring (lines 38-61)

Remove `example_provider` and `query_mode` from Args. Update description:

```python
    """
    Find constraint with given scope violated by e.

    Uses DiscriminatingGenerator to narrow down which constraint
    in the scope is the one in the target (paper Algorithm 3).

    Args:
        e: Negative example
        scope: Variable scope from FindScope (set of feature names)
        constraint_clauses: assumption_id -> raw CNF clauses
        feature_ids: Feature name -> SAT variable ID
        id_to_feature: SAT variable ID -> feature name
        remaining_bias: Mutable set of remaining bias assumption IDs
        record_query: Callback(config, answer, source) to record queries
        oracle: Oracle with is_valid(Dict[str, bool]) -> bool
        learned_kb: Currently learned constraint IDs (for DiscriminatingGenerator)
        generator: DiscriminatingGenerator instance
        profiler: Optional profiler

    Returns:
        Constraint ID (int) or None
    """
```

### Step 4: Simplify narrowing logic (lines 90-110)

Replace the entire block after `if len(rejecting) == 1: return rejecting[0]`:

```python
    # Use DiscriminatingGenerator to narrow down
    remaining = list(rejecting)

    if generator is not None:
        result = _narrow_with_generator(
            remaining, remaining_bias, record_query, oracle,
            learned_kb, generator, scope)
        if result is not None:
            return result

    # If we can't discriminate further, return first remaining candidate
    logging.debug('FindC: returning first of %d candidates', len(remaining))
    return remaining[0]
```

### Step 5: Delete `_narrow_with_pool` function (lines 113-152)

Remove the entire function:
```python
def _narrow_with_pool(
        candidates: list,
        constraint_clauses: Dict[int, List[List[int]]],
        feature_ids: Dict[str, int],
        remaining_bias: set,
        record_query,
        oracle,
        example_provider: ExampleProvider
):
    ...
```

This removes ~40 LOC.

### Step 6: Keep `_narrow_with_generator` unchanged (lines 155-191)

No changes needed to this function -- it uses DiscriminatingGenerator correctly per paper Algorithm 3.

## Todo List

- [ ] Remove ExampleProvider import
- [ ] Remove `example_provider` and `query_mode` from find_c signature
- [ ] Update docstring
- [ ] Simplify narrowing logic (always use generator when available)
- [ ] Delete `_narrow_with_pool` function

## Success Criteria

- FindC no longer references ExampleProvider
- FindC has no `query_mode` parameter
- `_narrow_with_pool` deleted
- DiscriminatingGenerator narrowing always attempted when generator provided
- Matches paper Algorithm 3

## Risk Assessment

- **Behavioral change**: FindC no longer uses pool examples for narrowing. Paper says this is correct. Pool-based narrowing was an optimization not in paper.
- **Low risk**: Internal refactoring, FindC callers already updated in Phase 2

## Security Considerations

- No new external interfaces

## Next Steps

- Phase 4: Update runner and consumers
