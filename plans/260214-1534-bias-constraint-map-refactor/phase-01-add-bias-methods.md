# Phase 1: Add Methods to Bias Class

**Parent plan**: [plan.md](./plan.md)

## Overview

- **Priority**: P3
- **Status**: completed
- **Description**: Add `to_constraint_map()`, `feature_ids`, `id_to_feature`, `max_variable_id`, and `to_constraint_maps_with_negation()` to `Bias` class

## Key Insights

- `Bias` currently has `to_cnf()` (flat list of all clauses) but no dict-based mapping
- `Bias` has `features: List[Feature]` with `.name` and `.id` — perfect for `feature_ids` property
- The `max_variable_id` property is needed by `ConGenModelBuilder` to compute `next_tseitin_var`
- `negate_cnf_tseitin` import from `explanation.operations.algorithms.utils` is safe (no circular dependency)

## Related Code Files

- **Modify**: `acqmss/bias/data_structures.py` (lines 76-101, Bias class)

## Implementation Steps

1. Add import for `Tuple` (already imported) and `negate_cnf_tseitin` at module top
2. Add `feature_ids` property:
   ```python
   @property
   def feature_ids(self) -> Dict[str, int]:
       """Feature name to SAT variable ID mapping."""
       return {f.name: f.id for f in self.features}
   ```
3. Add `id_to_feature` property:
   ```python
   @property
   def id_to_feature(self) -> Dict[int, str]:
       """SAT variable ID to feature name mapping."""
       return {f.id: f.name for f in self.features}
   ```
4. Add `to_constraint_map()` method:
   ```python
   def to_constraint_map(self) -> Dict[str, List[List[int]]]:
       """Convert bias constraints to {constraint_id: clauses} mapping."""
       return {c.id: c.clauses for c in self.constraints}
   ```
5. Add `max_variable_id` property:
   ```python
   @property
   def max_variable_id(self) -> int:
       """Max absolute literal value across all constraint clauses and feature IDs."""
       max_var = max((f.id for f in self.features), default=0)
       for c in self.constraints:
           for clause in c.clauses:
               for lit in clause:
                   max_var = max(max_var, abs(lit))
       return max_var
   ```
6. Add `to_constraint_maps_with_negation()` method:
   ```python
   def to_constraint_maps_with_negation(
       self, tseitin_start: int
   ) -> Tuple[Dict[str, List[List[int]]], Dict[str, List[List[int]]], int]:
       """Convert bias to constraint map and negated constraint map.

       Args:
           tseitin_start: Starting variable ID for Tseitin transformation

       Returns:
           Tuple of (constraint_map, negated_constraint_map, next_tseitin_var)
       """
       constraint_map = {}
       negated_constraint_map = {}
       tseitin_var = tseitin_start

       for c in self.constraints:
           constraint_map[c.id] = c.clauses
           neg_clauses, tseitin_var = negate_cnf_tseitin(c.clauses, tseitin_var)
           negated_constraint_map[c.id] = neg_clauses

       return constraint_map, negated_constraint_map, tseitin_var
   ```

## Todo

- [ ] Add `negate_cnf_tseitin` import to `data_structures.py`
- [ ] Add `feature_ids` property
- [ ] Add `id_to_feature` property
- [ ] Add `to_constraint_map()` method
- [ ] Add `max_variable_id` property
- [ ] Add `to_constraint_maps_with_negation()` method

## Success Criteria

- All 5 methods/properties exist on `Bias` class
- Type hints and docstrings present
- No new linting errors
