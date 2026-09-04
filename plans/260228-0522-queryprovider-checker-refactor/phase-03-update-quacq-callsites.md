---
title: "Phase 3: Update QuAcq.learn() Call Sites"
status: complete
priority: P1
effort: 20m
created: 2026-02-28
completed: 2026-02-28
---

# Phase 3: Update QuAcq.learn() Call Sites

## Context Links

- [Phase 2: QueryProvider refactor](phase-02-refactor-query-provider.md)
- Source: `conacq/algorithms/quacq/quacq.py`

## Overview

- **Priority**: P1
- **Status**: complete
- Update all QueryProvider call sites in `QuAcq.learn()` to use new signatures
- Replace `kb_clauses` + `bg_clauses` params with `learned_kb` + `set_b`
- Pass `negation_map` instead of `negated_clauses`

## Key Insights

- `learn()` already has `learned_kb` (local var) and `set_b` (param)
- `negation_map` already a param of `learn()`
- Remove `get_kb_clauses()` call since checker handles KB via assumptions
- `negated_clauses` param no longer needed by QueryProvider (but still needed by DiscriminatingGenerator)

## Requirements

- All 3 mode branches must be updated
- No new params needed on learn() — all data already available

## Related Code Files

- **Modify**: `conacq/algorithms/quacq/quacq.py` (lines ~160-188)

## Implementation Steps

### 1. Remove kb_cls computation (line 167)

**Before (inside while loop):**
```python
kb_cls = get_kb_clauses(learned_kb, constraint_clauses)
```

**After:** Delete this line. No longer needed — checker uses assumption IDs.

### 2. Update oracle mode call (lines 170-174)

**Before:**
```python
if mode == 'oracle':
    query, tested_c_id = self.query_provider.generate_from_sat(
        remaining_bias=remaining_bias, learned_kb=learned_kb,
        kb_clauses=kb_cls, negated_clauses=negated_clauses,
        bg_clauses=background_clauses, feature_ids=feature_ids,
        id_to_feature=id_to_feature, n_bg=len(set_b))
```

**After:**
```python
if mode == 'oracle':
    query, tested_c_id = self.query_provider.generate_from_sat(
        remaining_bias=remaining_bias,
        learned_kb=learned_kb,
        set_b=set_b,
        negation_map=negation_map,
        id_to_feature=id_to_feature)
```

### 3. Update example_only mode call (lines 175-180)

**Before:**
```python
elif mode == 'example_only':
    query, tested_c_id = self.query_provider.generate_from_pool(
        remaining_bias=remaining_bias, kb_clauses=kb_cls,
        bg_clauses=background_clauses,
        constraint_clauses=constraint_clauses,
        feature_ids=feature_ids)
```

**After:**
```python
elif mode == 'example_only':
    query, tested_c_id = self.query_provider.generate_from_pool(
        remaining_bias=remaining_bias,
        learned_kb=learned_kb,
        set_b=set_b,
        constraint_clauses=constraint_clauses,
        feature_ids=feature_ids)
```

### 4. Update example_first mode call (lines 181-188)

**Before:**
```python
else:  # example_first
    query, tested_c_id = self.query_provider.generate(
        remaining_bias=remaining_bias, learned_kb=learned_kb,
        kb_clauses=kb_cls, negated_clauses=negated_clauses,
        bg_clauses=background_clauses, feature_ids=feature_ids,
        id_to_feature=id_to_feature,
        constraint_clauses=constraint_clauses,
        n_bg=len(set_b))
```

**After:**
```python
else:  # example_first
    query, tested_c_id = self.query_provider.generate(
        remaining_bias=remaining_bias,
        learned_kb=learned_kb,
        set_b=set_b,
        negation_map=negation_map,
        constraint_clauses=constraint_clauses,
        feature_ids=feature_ids,
        id_to_feature=id_to_feature)
```

### 5. Clean up imports

**Remove from imports (if no longer used elsewhere in file):**
```python
from .sat_utils import get_kb_clauses  # Remove if only used for kb_cls
```

Check: `get_kb_clauses` is still used? Grep file. If only used in the deleted `kb_cls = get_kb_clauses(...)` line, remove import. Keep `config_to_assumptions` and `violates_clauses` if still used by prune methods.

### 6. Keep learn() params unchanged

`negated_clauses` param stays — still needed by `_prune_rejecting_constraints_legacy()` and also passed to DiscriminatingGenerator. `background_clauses` stays — still used by FindScope/FindC and DiscriminatingGenerator.

## Todo List

- [ ] Remove `kb_cls = get_kb_clauses(...)` line
- [ ] Update oracle mode: generate_from_sat(remaining_bias, learned_kb, set_b, negation_map, id_to_feature)
- [ ] Update example_only mode: generate_from_pool(remaining_bias, learned_kb, set_b, constraint_clauses, feature_ids)
- [ ] Update example_first mode: generate(remaining_bias, learned_kb, set_b, negation_map, constraint_clauses, feature_ids, id_to_feature)
- [ ] Clean unused imports
- [ ] Run: `PYTHONPATH=. pytest tests/test_quacq.py -v`

## Success Criteria

- All 3 mode branches use new QueryProvider signatures
- No raw clause construction (`kb_clauses + bg_clauses`) in learn()
- Existing params like `negated_clauses`, `background_clauses` retained for other uses

## Risk Assessment

- **Low**: Mechanical signature change, all data already available in learn()
- **Param omission**: Easy to miss a param. Verify each call matches Phase 2 signatures.

## Security Considerations

N/A.

## Next Steps

Phase 4: QuacqRunner passes checker + model to QueryProvider.
