# Phase 2: Update Callers

**Parent plan**: [plan.md](./plan.md)

## Overview

- **Priority**: P3
- **Status**: completed
- **Description**: Replace 4 inline conversion sites with calls to new Bias methods

## Related Code Files

- **Modify**: `acqmss/algorithms/congen_model_builder.py`
- **Modify**: `acqmss/algorithms/interactive/learner.py`
- **Modify**: `tests/test_interactive.py`

## Implementation Steps

### 1. `ConGenModelBuilder.build()` (congen_model_builder.py:117-125)

**Before:**
```python
bias_constraints = {c.id: c.clauses for c in bias.constraints}
max_var = max(feature_ids.values()) if feature_ids else 0
for clauses in bias_constraints.values():
    for clause in clauses:
        for lit in clause:
            max_var = max(max_var, abs(lit))
model.constraint_map = bias_constraints
model.next_tseitin_var = max_var + 1
```

**After:**
```python
model.constraint_map = bias.to_constraint_map()
model.next_tseitin_var = bias.max_variable_id + 1
```

Note: `max_variable_id` already includes feature IDs (from `bias.features`), so the separate `max(feature_ids.values())` computation is covered.

### 2. `InteractiveLearner.from_bias()` (learner.py:133-150)

**Before:**
```python
feature_ids = {f.name: f.id for f in bias.features}
id_to_feature = {f.id: f.name for f in bias.features}

constraint_map = {}
negated_constraint_map = {}
tseitin_var = max(f.id for f in bias.features) + 1
for constraint in bias.constraints:
    c_id = constraint.id
    constraint_map[c_id] = constraint.clauses
    neg_clauses, tseitin_var = negate_cnf_tseitin(constraint.clauses, tseitin_var)
    negated_constraint_map[c_id] = neg_clauses
```

**After:**
```python
feature_ids = bias.feature_ids
id_to_feature = bias.id_to_feature

tseitin_start = bias.max_variable_id + 1
constraint_map, negated_constraint_map, _ = bias.to_constraint_maps_with_negation(tseitin_start)
```

### 3. `InteractiveLearner._build_task_from_bias()` (learner.py:176-185)

**Before:**
```python
constraint_map = {}
negated_constraint_map = {}
tseitin_var = max(feature_ids.values()) + 1
for constraint in bias.constraints:
    c_id = constraint.id
    constraint_map[c_id] = constraint.clauses
    neg_clauses, tseitin_var = negate_cnf_tseitin(constraint.clauses, tseitin_var)
    negated_constraint_map[c_id] = neg_clauses
```

**After:**
```python
tseitin_start = max(feature_ids.values()) + 1
constraint_map, negated_constraint_map, _ = bias.to_constraint_maps_with_negation(tseitin_start)
```

### 4. `test_interactive.py` fixture `interactive_task` (lines 55-64)

**Before:**
```python
constraint_map = {}
negated_constraint_map = {}
for constraint in bias.constraints:
    c_id = constraint.id
    constraint_map[c_id] = constraint.clauses
    if constraint.clauses:
        negated_constraint_map[c_id] = [[-lit] for lit in constraint.clauses[0]]
```

**After** — use `to_constraint_map()` for constraint_map; keep simplified negation inline (test-specific logic, not Tseitin):
```python
constraint_map = bias.to_constraint_map()
negated_constraint_map = {}
for constraint in bias.constraints:
    if constraint.clauses:
        negated_constraint_map[constraint.id] = [[-lit] for lit in constraint.clauses[0]]
```

### 5. `test_congen.py` (line 308)

**Before:**
```python
bias_ids = {f.name: f.id for f in bias.features}
```

**After:**
```python
bias_ids = bias.feature_ids
```

### 6. Remove unused imports

In `learner.py`, check if `negate_cnf_tseitin` import can be removed (only if no other usage remains in file).

## Todo

- [ ] Update `ConGenModelBuilder.build()` — use `to_constraint_map()` + `max_variable_id`
- [ ] Update `InteractiveLearner.from_bias()` — use `feature_ids`, `id_to_feature`, `to_constraint_maps_with_negation()`
- [ ] Update `InteractiveLearner._build_task_from_bias()` — use `to_constraint_maps_with_negation()`
- [ ] Update `test_interactive.py` fixture — use `to_constraint_map()`
- [ ] Update `test_congen.py` — use `bias.feature_ids`
- [ ] Remove unused `negate_cnf_tseitin` import from `learner.py` if applicable

## Success Criteria

- No inline `{c.id: c.clauses}` or `{f.name: f.id}` patterns remain outside Bias class
- All existing tests pass with no behavior change
