# Phase 1: Inject Checker into FindScope/FindC

## Context Links

- [Brainstorm report](../reports/brainstorm-260228-0620-findscope-findc-checker-refactor.md)
- [plan.md](plan.md)
- Source: `conacq/algorithms/quacq/findscope.py`, `conacq/algorithms/quacq/findc.py`
- Reference pattern: `QuAcq._prune_rejecting_constraints` in `conacq/algorithms/quacq/quacq.py` (lines 282-298)

## Overview

- **Priority**: P2
- **Status**: complete
- **Description**: Replace `violates_clauses()` with `checker.is_consistent()` in both FindScope and FindC. Inject `ConsistencyChecker` + `QuAcqModel` via constructor. Add `root_assumption` param to `run()`.

## Key Insights

- `QuAcq._prune_rejecting_constraints` already uses the exact pattern: `checker.is_consistent([root] + config_assumptions + [aid])`
- `model.config_to_assumptions(config)` converts feature config dict to Part 4 assignment assumption IDs — replaces manual `partial_config_to_assumptions` + `violates_clauses` combo
- FindScope scope filter `c_vars.issubset(R)` is unnecessary with SAT — solver handles unassigned vars by exploring all values. UNSAT with partial assignment = constraint truly conflicts regardless of free variables. Stronger pruning.
- FindC already builds full `e_assumptions` from complete example `e` — maps directly to `model.config_to_assumptions(e)`

## Requirements

### Functional
- FindScope._prune_rejecting_partial uses `checker.is_consistent([root] + partial_assumptions + [c_id])`
- FindC.run filter uses `checker.is_consistent([root] + e_assumptions + [c_id])`
- Both share QuAcq's existing checker instance
- Behavior correctness: SAT catches all violations that Boolean eval catches, plus implied ones

### Non-Functional
- No new solver instances (share existing)
- Minimal signature changes (additive only)

## Architecture

### Before (Boolean eval)
```
FindScope.__init__(oracle)
FindScope._prune_rejecting_partial:
  assumptions = partial_config_to_assumptions(e, R, feature_ids)
  assignment = {abs(lit): lit > 0 for lit in assumptions}
  for c_id in remaining_bias:
    c_vars = get_constraint_vars(c_id, ...)
    if not c_vars.issubset(R): continue    # <-- scope filter (removed)
    if violates_clauses(clauses, assignment): prune
```

### After (SAT-based)
```
FindScope.__init__(oracle, checker, model)
FindScope._prune_rejecting_partial:
  config_assumptions = model.config_to_assumptions({k: e[k] for k in R if k in e})
  base = [root_assumption] + config_assumptions
  for c_id in remaining_bias:
    if not checker.is_consistent(base + [c_id]): prune
```

## Related Code Files

### Modify
- `conacq/algorithms/quacq/findscope.py` — inject checker+model, rewrite _prune_rejecting_partial
- `conacq/algorithms/quacq/findc.py` — inject checker+model, rewrite rejecting filter

### Reference (read-only)
- `conacq/algorithms/quacq/quacq.py` — `_prune_rejecting_constraints` (lines 282-298) as pattern
- `conacq/algorithms/quacq/quacq_model.py` — `config_to_assumptions()` (lines 116-128)
- `explanation/operations/algorithms/checker.py` — `ConsistencyChecker.is_consistent()`

## Implementation Steps

### Step 1: Update FindScope

1. **Constructor**: Change `__init__(self, oracle)` to `__init__(self, oracle, checker, model)`
   - `checker`: `ConsistencyChecker` — shared from QuAcq
   - `model`: `QuAcqModel` — for `config_to_assumptions()`

2. **run() signature**: Add `root_assumption: int` parameter (after `record_query`)

3. **Remove imports**: Drop `get_constraint_vars`, `violates_clauses` from sat_utils import. Keep `partial_config_to_assumptions` ONLY if still needed (it won't be — model.config_to_assumptions handles partial configs via dict comprehension). Actually, remove `partial_config_to_assumptions` too since we use model.config_to_assumptions with a filtered dict.

4. **Add imports**: Add `ConsistencyChecker` from `explanation.operations.algorithms.checker`

5. **Rewrite `_prune_rejecting_partial`**:
   - Remove params: `constraint_clauses`, `feature_ids`, `id_to_feature` (no longer needed)
   - Keep params: `remaining_bias`, `e`, `R`, `root_assumption`
   - New body:
     ```python
     def _prune_rejecting_partial(self, remaining_bias, e, R, root_assumption):
         partial = {k: e[k] for k in R if k in e}
         if not partial:
             return
         config_assumptions = self.model.config_to_assumptions(partial)
         base = [root_assumption] + config_assumptions
         pruned = []
         for c_id in list(remaining_bias):
             if not self.checker.is_consistent(base + [c_id]):
                 pruned.append(c_id)
         if pruned:
             remaining_bias -= set(pruned)
             logging.debug('FindScope pruned %d constraints from partial query', len(pruned))
     ```

6. **Update `run()` call to `_prune_rejecting_partial`**: Remove `constraint_clauses`, `feature_ids`, `id_to_feature` args. Pass `root_assumption` instead.

7. **Update recursive `run()` calls**: Pass `root_assumption` through both recursive calls.

8. **Simplify `run()` params**: Remove `constraint_clauses`, `feature_ids`, `id_to_feature` from run() signature (no longer needed by _prune). Keep `remaining_bias` and `record_query`.

### Step 2: Update FindC

1. **Constructor**: Change `__init__(self, oracle, generator=None)` to `__init__(self, oracle, checker, model, generator=None)`

2. **run() signature**: Add `root_assumption: int` parameter

3. **Remove imports**: Drop `violates_clauses` from sat_utils import. Keep `config_to_assumptions` ONLY if still needed — it won't be, use model.config_to_assumptions. Keep `get_constraints_with_scope`.

4. **Add imports**: Add `ConsistencyChecker` from `explanation.operations.algorithms.checker`

5. **Rewrite rejecting filter in `run()`** (lines 70-78 currently):
   ```python
   # Filter to constraints that actually reject e
   rejecting = []
   e_assumptions = self.model.config_to_assumptions(e)
   base = [root_assumption] + e_assumptions
   for c_id in candidates:
       if not self.checker.is_consistent(base + [c_id]):
           rejecting.append(c_id)
   ```

6. **Remove unused code**: Drop `assignment` dict creation, `config_to_assumptions` import (replaced by model method).

7. **Simplify `run()` params**: Remove `feature_ids` from signature (no longer needed). Keep `constraint_clauses`, `id_to_feature` (still needed by `get_constraints_with_scope`). Keep `remaining_bias`, `record_query`, `learned_kb`.

## Todo List

- [ ] FindScope: add checker+model to __init__
- [ ] FindScope: add root_assumption to run()
- [ ] FindScope: rewrite _prune_rejecting_partial with checker.is_consistent
- [ ] FindScope: remove scope filter (c_vars.issubset)
- [ ] FindScope: clean imports (remove violates_clauses, get_constraint_vars, partial_config_to_assumptions)
- [ ] FindScope: remove unused params from run() (constraint_clauses, feature_ids, id_to_feature)
- [ ] FindC: add checker+model to __init__
- [ ] FindC: add root_assumption to run()
- [ ] FindC: rewrite rejecting filter with checker.is_consistent
- [ ] FindC: clean imports (remove violates_clauses, config_to_assumptions)
- [ ] FindC: remove feature_ids from run() signature
- [ ] Verify module docstrings updated

## Success Criteria

- FindScope/FindC use `checker.is_consistent()` instead of `violates_clauses()`
- No `violates_clauses` or `get_constraint_vars` imports in findscope.py or findc.py
- No `c_vars.issubset(R)` scope filter in FindScope
- Both classes accept checker+model via constructor
- Both run() accept root_assumption param

## Risk Assessment

- **Low risk**: Same proven pattern as QuAcq._prune_rejecting_constraints
- **SAT call volume**: FindScope recurses O(|S| * log|X|) — each level prunes, so SAT calls scale with binary search depth. IncrementalPySATChecker handles this efficiently via assumption toggle.
- **Mitigation**: Existing tests validate correctness end-to-end

## Security Considerations

- No external input changes
- No new file I/O

## Next Steps

- Phase 2: Update QuAcq callsites to pass checker+model+root_assumption to FindScope/FindC
