# Phase 5: Replace violates_clauses with checker.is_consistent

## Context Links
- [Phase 4](phase-04-quacq-model-combined-kb.md) (prerequisite)
- Source: `conacq/algorithms/quacq/quacq.py` lines 287-304

## Overview
- **Priority**: P1 (core behavioral change)
- **Status**: complete
- **Description**: `_prune_rejecting_constraints` uses `self.checker.is_consistent()` instead of `violates_clauses()`

## Key Insights

### Current prune logic (lines 287-304)
```python
def _prune_rejecting_constraints(self, constraint_clauses, feature_ids,
                                  remaining_bias, positive_example):
    assumptions_list = config_to_assumptions(positive_example, feature_ids)
    assignment = {abs(lit): lit > 0 for lit in assumptions_list}
    pruned = []
    for aid in list(remaining_bias):
        clauses = constraint_clauses.get(aid, [])
        if violates_clauses(clauses, assignment):
            pruned.append(aid)
    remaining_bias -= set(pruned)
    return pruned
```

### New prune logic
```python
def _prune_rejecting_constraints(self, remaining_bias, positive_example,
                                  root_assumption, pos_map, neg_map):
    config_assumptions = [pos_map[feat] if val else neg_map[feat]
                          for feat, val in positive_example.items()]
    base = [root_assumption] + config_assumptions
    pruned = []
    for aid in list(remaining_bias):
        if not self.checker.is_consistent(base + [aid]):
            pruned.append(aid)
    remaining_bias -= set(pruned)
    return pruned
```

### Why this is correct
- `base = [root_assumption] + config_assumptions` enables root BG + feature assignment guards
- `base + [aid]` additionally enables bias constraint `aid`
- All other assumptions disabled by checker._compute_delta
- Disabled Part 4 assumptions: their guarded clauses auto-satisfy
- If UNSAT: the bias constraint `aid` conflicts with the example under BG knowledge
- This catches implied violations that pure Boolean `violates_clauses` misses

## Requirements

### Functional
- `_prune_rejecting_constraints` signature changes: remove `constraint_clauses`, `feature_ids`; add `root_assumption`, `pos_map`, `neg_map`
- Uses `self.checker.is_consistent()` instead of `violates_clauses()`
- learn() passes new params from its arguments

### Non-functional
- Prune is slightly slower (SAT call vs Boolean eval) but catches more violations
- May result in smaller remaining_bias (more aggressive pruning)

## Architecture

```
Before:  violates_clauses(raw_clauses, {var: bool})  -- pure Boolean eval
After:   checker.is_consistent([root] + [assignments] + [aid])  -- SAT with BG
```

## Related Code Files
- **Modify**: `conacq/algorithms/quacq/quacq.py`

## Implementation Steps

### Step 1: Update learn() signature (line 100)

Add 3 new params after `negated_clauses`:
```python
def learn(self,
          set_c: List[int],
          set_b: List[int],
          negation_map: Dict[int, int],
          background_clauses: List[List[int]],
          feature_ids: Dict[str, int],
          id_to_feature: Dict[int, str],
          constraint_clauses: Dict[int, List[List[int]]],
          negated_clauses: Dict[int, List[List[int]]],
          pos_assignment_to_assumption: Dict[str, int] = None,
          neg_assignment_to_assumption: Dict[str, int] = None,
          root_assumption: int = None,
          mode: Literal['oracle', 'example_only', 'example_first'] = 'oracle',
          max_queries: int = 1000,
          ) -> QuAcqResult:
```

Default `None` for backward compat (tests with minimal params). If None, fall back to old behavior.

### Step 2: Update learn() body -- prune call (around line 198)

Current:
```python
pruned = self._prune_rejecting_constraints(
    constraint_clauses, feature_ids, remaining_bias, query)
```

New:
```python
if pos_assignment_to_assumption and root_assumption is not None:
    pruned = self._prune_rejecting_constraints(
        remaining_bias, query,
        root_assumption, pos_assignment_to_assumption,
        neg_assignment_to_assumption)
else:
    # Fallback: pure Boolean eval (backward compat for tests)
    pruned = self._prune_rejecting_constraints_legacy(
        constraint_clauses, feature_ids, remaining_bias, query)
```

### Step 3: Rename old method, add new one

Rename existing `_prune_rejecting_constraints` to `_prune_rejecting_constraints_legacy`.

Add new `_prune_rejecting_constraints`:
```python
@count_calls('prune_calls')
def _prune_rejecting_constraints(self,
                                  remaining_bias: set,
                                  positive_example: Dict[str, bool],
                                  root_assumption: int,
                                  pos_map: Dict[str, int],
                                  neg_map: Dict[str, int]) -> List[int]:
    """Remove constraints from remaining_bias that reject the positive example.

    Uses SAT-based consistency checking with Part 4 feature assignment
    assumptions, catching implied violations beyond pure Boolean evaluation.
    """
    config_assumptions = [pos_map[feat] if val else neg_map[feat]
                          for feat, val in positive_example.items()]
    base = [root_assumption] + config_assumptions
    pruned = []
    for aid in list(remaining_bias):
        if not self.checker.is_consistent(base + [aid]):
            pruned.append(aid)
    remaining_bias -= set(pruned)
    return pruned
```

### Step 4: Update docstring for learn() Args section

Add:
```
pos_assignment_to_assumption: Feature name -> pos assignment assumption ID (Part 4)
neg_assignment_to_assumption: Feature name -> neg assignment assumption ID (Part 4)
root_assumption: Root BG assumption ID (enables root constraint)
```

### Step 5: Remove unused import

After all tests pass, consider removing `violates_clauses` from imports if `_legacy` method is removed. Keep for now since tests may still use it.

## Todo List
- [ ] Add 3 new params to learn() with None defaults
- [ ] Rename old _prune to _legacy
- [ ] Add new _prune using checker.is_consistent()
- [ ] Add dispatch logic in learn() body
- [ ] Update docstrings
- [ ] Keep violates_clauses import (still used by _legacy and tests)

## Success Criteria
- With Part 4 data: prune uses checker.is_consistent()
- Without Part 4 data (None): falls back to violates_clauses (backward compat)
- Prune catches same or more violations than before
- All existing tests pass

## Risk Assessment
- **Medium**: core behavioral change
- SAT-based prune is slower per call but semantically stronger
- Fallback ensures backward compat during transition

### Mitigation
- Keep legacy method as fallback
- Unit test both paths

## Security Considerations
- None

## Next Steps
- Phase 6: Update _learn_params_from_task in runner
