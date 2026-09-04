---
parent: plan.md
phase: 1
status: completed
completed: 2026-02-28
---

# Phase 1: Extract `prune_rejecting` and Rewire Callers

## Overview

- **Priority:** P3
- **Description:** Extract shared pruning loop into `sat_utils.prune_rejecting()`, convert both callers to thin wrappers
- **Implementation status:** Completed
- **Review status:** Completed

## Key Insights

- Core loop is identical: `config_to_assumptions → base = [root] + config → iterate bias → is_consistent check → collect pruned → mutate set`
- Both classes already hold same deps (`self.checker: ConsistencyChecker`, `self.model: QuAcqModel`)
- `sat_utils.py` already hosts shared functions (`config_to_assumptions`, `get_constraints_with_scope`, etc.) — natural home
- Neither findscope.py nor quacq.py currently imports from sat_utils

## Related Code Files

### Modify
- `conacq/algorithms/quacq/sat_utils.py` — add `prune_rejecting()`
- `conacq/algorithms/quacq/findscope.py` — rewire `_prune_rejecting_partial` as thin wrapper
- `conacq/algorithms/quacq/quacq.py` — rewire `_prune_rejecting_constraints` as thin wrapper

### No changes needed
- Tests — no direct tests for private methods; validated indirectly via existing test suite

## Implementation Steps

### Step 1: Add `prune_rejecting` to `sat_utils.py`

Add after the last existing function:

```python
def prune_rejecting(
        checker,
        model,
        remaining_bias: set,
        assignment: dict,
        root_assumption: int,
) -> list:
    """Remove constraints from remaining_bias that reject the given assignment.

    A constraint is pruned if KB + root + assignment_assumptions + constraint is UNSAT.

    Returns list of pruned constraint assumption IDs.
    Mutates remaining_bias in-place.
    """
    config_assumptions = model.config_to_assumptions(assignment)
    base = [root_assumption] + config_assumptions
    pruned = []
    for c_id in list(remaining_bias):
        if not checker.is_consistent(base + [c_id]):
            pruned.append(c_id)
    remaining_bias -= set(pruned)
    return pruned
```

### Step 2: Rewire `FindScope._prune_rejecting_partial`

Replace body to delegate to shared function. Preserve: partial extraction, empty guard, debug logging.

```python
def _prune_rejecting_partial(self, remaining_bias, e, R, root_assumption):
    """Prune bias constraints that reject partial assignment e[R]."""
    partial = {k: e[k] for k in R if k in e}
    if not partial:
        return

    pruned = prune_rejecting(self.checker, self.model, remaining_bias, partial, root_assumption)
    if pruned:
        logging.debug('FindScope pruned %d constraints from partial query', len(pruned))
```

Add import: `from .sat_utils import prune_rejecting`

### Step 3: Rewire `QuAcq._prune_rejecting_constraints`

Replace body to delegate. Preserve: `@count_calls` decorator, return value.

```python
@count_calls('prune_calls')
def _prune_rejecting_constraints(self, remaining_bias, positive_example, root_assumption):
    """Remove constraints from remaining_bias that reject the positive example."""
    return prune_rejecting(self.checker, self.model, remaining_bias, positive_example, root_assumption)
```

Add import: `from .sat_utils import prune_rejecting`

### Step 4: Run tests

```bash
PYTHONPATH=. pytest tests/ -v
```

## Todo List

- [x] Add `prune_rejecting()` to sat_utils.py
- [x] Rewire FindScope._prune_rejecting_partial
- [x] Rewire QuAcq._prune_rejecting_constraints
- [x] Run full test suite — all pass

## Success Criteria

- All tests pass unchanged
- Zero behavior change — same pruning results, same side effects
- Single source of truth for the pruning loop

## Risk Assessment

- **Low risk**: Private methods, no external API change, tested indirectly through existing suite
- **Mitigation**: Run full test suite after changes
