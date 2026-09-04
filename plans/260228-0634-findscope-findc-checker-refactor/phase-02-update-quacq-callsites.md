# Phase 2: Update QuAcq Callsites

## Context Links

- [Phase 1](phase-01-inject-checker-into-findscope-findc.md)
- [plan.md](plan.md)
- Source: `conacq/algorithms/quacq/quacq.py` (lines 207-230)

## Overview

- **Priority**: P2
- **Status**: complete
- **Description**: Update FindScope/FindC instantiation in QuAcq.learn() to pass checker+model. Pass root_assumption to run() calls. Clean up unused imports.

## Key Insights

- QuAcq already has `self.checker` and `self.model` — just forward them
- `root_assumption` is `set_b[0]` (already used in `_prune_rejecting_constraints` at line 197)
- FindScope/FindC instantiated fresh each negative-example iteration (lines 207, 221) — no caching concern

## Requirements

### Functional
- FindScope/FindC receive checker+model from QuAcq
- root_assumption passed to both run() calls
- Unused params removed from run() call args

### Non-Functional
- No new dependencies
- QuAcq constructor unchanged

## Related Code Files

### Modify
- `conacq/algorithms/quacq/quacq.py` — update FindScope/FindC instantiation and run() calls

### Reference (read-only)
- Phase 1 output: updated FindScope/FindC signatures

## Implementation Steps

### Step 1: Update FindScope instantiation (line 207)

**Before:**
```python
find_scope = FindScope(self.oracle)
```

**After:**
```python
find_scope = FindScope(self.oracle, self.checker, self.model)
```

### Step 2: Update FindScope.run() call (lines 208-216)

**Before:**
```python
scope_vars = find_scope.run(
    e=query, R=set(), Y=all_variables,
    ask_query=False,
    constraint_clauses=constraint_clauses,
    feature_ids=feature_ids,
    id_to_feature=id_to_feature,
    remaining_bias=remaining_bias,
    record_query=record_query,
)
```

**After:**
```python
scope_vars = find_scope.run(
    e=query, R=set(), Y=all_variables,
    ask_query=False,
    remaining_bias=remaining_bias,
    record_query=record_query,
    root_assumption=set_b[0],
)
```

Remove `constraint_clauses`, `feature_ids`, `id_to_feature` — no longer needed by FindScope.

### Step 3: Update FindC instantiation (line 221)

**Before:**
```python
find_c = FindC(self.oracle, self.discriminating_generator)
```

**After:**
```python
find_c = FindC(self.oracle, self.checker, self.model, self.discriminating_generator)
```

### Step 4: Update FindC.run() call (lines 222-230)

**Before:**
```python
c_id = find_c.run(
    e=query, scope=scope,
    constraint_clauses=constraint_clauses,
    feature_ids=feature_ids,
    id_to_feature=id_to_feature,
    remaining_bias=remaining_bias,
    record_query=record_query,
    learned_kb=learned_kb,
)
```

**After:**
```python
c_id = find_c.run(
    e=query, scope=scope,
    constraint_clauses=constraint_clauses,
    id_to_feature=id_to_feature,
    remaining_bias=remaining_bias,
    record_query=record_query,
    learned_kb=learned_kb,
    root_assumption=set_b[0],
)
```

Remove `feature_ids` (no longer needed by FindC). Keep `constraint_clauses` and `id_to_feature` (still needed by `get_constraints_with_scope`).

### Step 5: Clean up QuAcq imports

Check if `violates_clauses` import at line 23 is still needed. It's used only in `_prune_rejecting_constraints_legacy` (line 308). If legacy method is kept, keep import. Otherwise remove.

Current import (line 22-23):
```python
from .sat_utils import (
    config_to_assumptions, violates_clauses
)
```

`config_to_assumptions` — used in `_prune_rejecting_constraints_legacy` (line 307). Keep if legacy kept.

Decision: Keep both imports (legacy method still exists). No import changes needed in quacq.py.

### Step 6: Guard against missing model

Add a guard in learn() before the negative-example path. If `self.model is None`, FindScope/FindC can't use SAT-based pruning. For safety:

```python
if self.model is None:
    raise ValueError("model required for FindScope/FindC SAT-based checking")
```

Place this in `_validate_mode()` or at the top of the negative-example branch. Best location: `_validate_mode()`, add:
```python
if self.model is None:
    raise ValueError("model is required (for FindScope/FindC consistency checking)")
```

Actually, review existing usage — `_prune_rejecting_constraints` already assumes `self.model` is set (line 291: `self.model.config_to_assumptions`). So model is already effectively required. Making it explicit in validation is good practice.

## Todo List

- [ ] Update FindScope instantiation: pass self.checker, self.model
- [ ] Update FindScope.run() args: remove constraint_clauses/feature_ids/id_to_feature, add root_assumption
- [ ] Update FindC instantiation: pass self.checker, self.model
- [ ] Update FindC.run() args: remove feature_ids, add root_assumption
- [ ] Add model-required validation in _validate_mode() or learn()
- [ ] Verify no unused imports introduced

## Success Criteria

- FindScope/FindC receive checker+model from QuAcq
- root_assumption=set_b[0] passed to both run() calls
- Removed params no longer passed
- Tests pass (Phase 3)

## Risk Assessment

- **Very low**: Mechanical callsite updates
- **Guard**: `set_b[0]` requires non-empty `set_b` — already guaranteed by QuAcqTask preparation (root BG always present)

## Security Considerations

- No external input changes

## Next Steps

- Phase 3: Update tests
