# Phase 3: Refactor bias_io.py

## Context Links
- Parent plan: `plans/260216-1425-bias-package-refactoring/plan.md`
- Source: `acqmss/bias/bias_io.py` (222 LOC → target ~210 LOC)

## Overview
- **Priority**: P2
- **Status**: pending
- **Description**: Extract JSON building helpers from `save_to_json()` and `load_from_json()`.

## Key Insights
- `save_to_json()` (lines 84-129) has inline dict comprehensions for features and constraints. The constraint serialization (lines 115-125) is a good extraction target.
- `load_from_json()` (lines 131-176) has inline constraint reconstruction (lines 161-174) that mirrors the save logic — should be a symmetric `_constraint_from_dict()`.
- `save_to_cnf()` (lines 17-81) is already well-structured with sequential write operations — harder to extract without making it less readable.
- `save_statistics()` (lines 178-222) is straightforward — no extraction needed.

## Related Code Files
- **Modify**: `acqmss/bias/bias_io.py`
- **Read**: `acqmss/bias/data_structures.py` (Feature, Constraint, Bias)

## Implementation Steps

### Step 1: Extract `_constraint_to_dict()` helper
```python
@staticmethod
def _constraint_to_dict(constraint: Constraint) -> dict:
    return {
        'id': constraint.id,
        'operator': constraint.operator.value if constraint.operator else None,
        'parent': constraint.parent.name if constraint.parent else None,
        'children': [ch.name for ch in constraint.children],
        'clauses': constraint.clauses,
        'description': constraint.description
    }
```
Replace lines 116-124 in `save_to_json()` with call to this helper.

### Step 2: Extract `_constraint_from_dict()` helper
```python
@staticmethod
def _constraint_from_dict(c_data: dict, feature_map: dict) -> Constraint:
    parent = feature_map.get(c_data['parent']) if c_data['parent'] else None
    children = [feature_map[name] for name in c_data['children']]
    return Constraint(
        id=c_data['id'],
        operator=OperatorType(c_data['operator']) if c_data['operator'] else None,
        parent=parent,
        children=children,
        clauses=c_data['clauses'],
        description=c_data['description']
    )
```
Replace lines 163-174 in `load_from_json()` with call to this helper.

### Step 3: Simplify `save_to_json()` and `load_from_json()`
Both methods use the new helpers, reducing inline dict comprehension complexity.

## Todo
- [ ] Extract `_constraint_to_dict()` static method
- [ ] Extract `_constraint_from_dict()` static method
- [ ] Simplify `save_to_json()` to use `_constraint_to_dict()`
- [ ] Simplify `load_from_json()` to use `_constraint_from_dict()`

## Success Criteria
- [ ] Symmetric serialization/deserialization via shared helpers
- [ ] No public API changes
- [ ] `load_from_json()` round-trip still works correctly
- [ ] File total ≤215 LOC

## Risk Assessment
- **Low**: Pure extraction, same data format preserved
- **Verify**: JSON round-trip (save → load → compare) must produce identical bias
