# Phase 1: Refactor bias_generator.py

## Context Links
- Parent plan: `plans/260216-1425-bias-package-refactoring/plan.md`
- Brainstorm: `plans/reports/brainstorm-260216-1425-bias-package-improvements.md`
- Source: `acqmss/bias/bias_generator.py` (282 LOC → target ~260 LOC)

## Overview
- **Priority**: P2
- **Status**: pending
- **Description**: Extract helper methods from `generate_cross_tree_constraints()` (93 LOC monolith) and cache constraints for `get_statistics()` reuse.

## Key Insights
- `generate_cross_tree_constraints()` has two distinct branches: specific pairs (lines 142-168) vs. combinations mode (lines 169-215). Each should be its own method.
- `get_statistics()` (lines 253-282) regenerates all constraints via `generate_hierarchical_constraints()` + `generate_cross_tree_constraints()`. Wasteful when `generate_bias()` was already called.
- Constraint counter gets incremented during statistics generation, causing counter drift — a subtle bug if `get_statistics()` is called before `generate_bias()`.

## Related Code Files
- **Modify**: `acqmss/bias/bias_generator.py`
- **Read**: `acqmss/bias/data_structures.py` (Feature, Constraint types)

## Implementation Steps

### Step 1: Extract `_generate_from_specific_pairs()` (lines 142-168)
Extract the `specific_pairs` branch into a private method:
```python
def _generate_from_specific_pairs(self, allowed_ops: list) -> List[Constraint]:
```
Move lines 143-168 into this method. Returns list of constraints.

### Step 2: Extract `_generate_from_combinations()` (lines 169-215)
Extract the combinations branch into a private method:
```python
def _generate_from_combinations(self, allowed_ops: list) -> List[Constraint]:
```
Move lines 170-213 into this method. Gets cross-tree features internally via `self.config.get_cross_tree_features()`.

### Step 3: Simplify `generate_cross_tree_constraints()`
After extraction, the method becomes:
```python
def generate_cross_tree_constraints(self) -> List[Constraint]:
    allowed_ops = self.config.cross_tree_config.get_allowed_operators()
    if self.config.cross_tree_config.specific_pairs:
        return self._generate_from_specific_pairs(allowed_ops)
    return self._generate_from_combinations(allowed_ops)
```

### Step 4: Add constraint caching in `generate_bias()`
Add `self._cached_bias = None` in `__init__`. After generating bias in `generate_bias()`, store:
```python
self._cached_bias = bias
```

### Step 5: Refactor `get_statistics()` to use cache
```python
def get_statistics(self) -> Dict[str, any]:
    if self._cached_bias is None:
        bias = self.generate_bias()
    else:
        bias = self._cached_bias

    op_counts = Counter(c.operator.value for c in bias.constraints)
    ...
```
This avoids counter drift and redundant generation.

## Todo
- [ ] Extract `_generate_from_specific_pairs()`
- [ ] Extract `_generate_from_combinations()`
- [ ] Simplify `generate_cross_tree_constraints()`
- [ ] Add `_cached_bias` field and caching in `generate_bias()`
- [ ] Refactor `get_statistics()` to use cache

## Success Criteria
- [ ] `generate_cross_tree_constraints()` is <15 LOC (delegation only)
- [ ] Each extracted method is <50 LOC
- [ ] `get_statistics()` reuses cached bias
- [ ] No public API changes
- [ ] File total ≤270 LOC

## Risk Assessment
- **Low**: Pure internal extraction, no behavioral change
- **Counter drift**: Fixed by caching — `get_statistics()` no longer increments counter
