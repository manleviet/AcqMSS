# Phase 2: Rewrite DiscriminatingGenerator with DI Pattern

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-model-method.md) (get_constraint_vars)
- Reference pattern: FindScope/FindC DI in `findscope.py`, `findc.py`

## Overview
- **Priority**: High (core change)
- **Status**: Complete
- **Description**: Replace raw PySAT solver usage with ConsistencyChecker DI pattern

## Key Insights
- KB already contains both original + negated clauses gated by separate assumptions
- `negation_map[original_id] = negated_id` links constraint → negation assumption
- `_compute_delta()` in checker auto-disables all assumptions not in set_c
- `model.model_to_config()` already exists — replaces private `_model_to_config()`

## Requirements
- New constructor: `__init__(checker, model, root_assumption)`
- `generate()` signature unchanged: `(c_i, c_j, learned_kb, scope) -> Optional[Dict[str, bool]]`
- No raw PySAT imports remain
- Import ConsistencyChecker from explanation.operations.algorithms.checker

## Related Code Files
- **Modify**: `conacq/algorithms/quacq/discriminating_generator.py` (full rewrite)
- **Reference**: `conacq/algorithms/quacq/findscope.py` (DI pattern)
- **Reference**: `conacq/algorithms/quacq/findc.py` (DI pattern)

## Implementation Steps

1. Replace imports:
   - Remove: `from pysat.solvers import Solver`
   - Remove: `from .sat_utils import get_constraint_vars`
   - Add: `from explanation.operations.algorithms.checker import ConsistencyChecker`

2. Rewrite constructor:
   ```python
   def __init__(self, checker: ConsistencyChecker, model, root_assumption: int) -> None:
       self.checker = checker
       self.model = model
       self.root_assumption = root_assumption
   ```

3. Rewrite `generate()`:
   ```python
   def generate(self, c_i: int, c_j: int,
                learned_kb: List[int], scope: Set[str]) -> Optional[Dict[str, bool]]:
       # C_L[Y]: learned constraints in scope
       cl_y = [c_id for c_id in learned_kb
               if self.model.get_constraint_vars(c_id).issubset(scope)]

       # Get negated assumption for c_j
       negation_map = self.model.get_negation_map()
       neg_j = negation_map.get(c_j)
       if neg_j is None:
           return None

       # SAT: BG + C_L[Y] + c_i + neg(c_j)
       set_c = [self.root_assumption] + cl_y + [c_i, neg_j]

       if self.checker.is_consistent(set_c):
           return self.model.model_to_config(self.checker.get_model())
       return None
   ```

4. Remove private methods:
   - Delete `_get_learned_clauses_in_scope()`
   - Delete `_model_to_config()`

5. Update module docstring to reflect DI pattern

## Todo
- [x] Replace imports (remove PySAT, add ConsistencyChecker)
- [x] Rewrite constructor with DI
- [x] Rewrite generate() with assumption-based SAT
- [x] Remove _get_learned_clauses_in_scope()
- [x] Remove _model_to_config()
- [x] Update docstrings

## Success Criteria
- No `pysat.solvers` import in file
- generate() uses checker.is_consistent() + get_model()
- generate() return type unchanged
- File under 60 lines (significantly smaller than current ~80 lines)

## Risk Assessment
- **Medium**: SAT model may differ from raw solver (both correct, different valid assignments)
- **Mitigation**: Tests verify functional equivalence (learned constraints match expected)
