# Phase 1: Create DiscriminatingGenerator

## Context

- Brainstorm: `plans/reports/brainstorm-260227-1614-findscope-findc-oracle-refactor.md`
- Paper: IJCAI 2013 Algorithm 3, line 5: `choose e' in sol(C_L[Y])`

## Overview

- **Priority**: P1 (blocks Phases 2-5)
- **Status**: completed
- **Effort**: 30min

New standalone class that generates discriminating examples from **learned KB restricted to scope** (C_L[Y]) instead of FM clauses (ground truth). This is the core correctness fix.

## Key Insight

Paper says: `e' in sol(C_L[Y])` where C_L = learned constraints. Current code uses `fm_clauses + c_i + neg_j` which leaks ground truth to the learner.

Resolved decision: Include BG clauses in SAT formula (`BG + C_L[Y] + c_i + neg_j`) to avoid generating examples that trivially violate background constraints.

## Requirements

### Functional
- Generate example satisfying: `BG + C_L[Y] + c_i + neg_c_j`
- C_L[Y] = learned constraint clauses whose variables are all within scope Y
- Return `Dict[str, bool]` config or `None` if UNSAT

### Non-functional
- Standalone, no oracle dependency (pure SAT)
- ~50 LOC max

## Architecture

```
DiscriminatingGenerator
  .__init__(task: QuAcqTask, solver_name: str)
  .generate(c_i: int, c_j: int, learned_kb: List[int], scope: set) -> Optional[Dict[str, bool]]
  ._get_learned_clauses_in_scope(learned_kb, scope) -> List[List[int]]
```

SAT formula: `BG_clauses + C_L[Y]_clauses + constraint_clauses[c_i] + negated_clauses[c_j]`

## Related Code Files

### Create
- `conacq/algorithms/quacq/discriminating_generator.py` (~50 LOC)

### Read (dependencies)
- `conacq/algorithms/quacq/task_preparation.py` — QuAcqTask fields: `background_clauses`, `constraint_clauses`, `negated_clauses`, `_get_constraint_vars()`, `model_to_config()`

## Implementation Steps

1. Create `conacq/algorithms/quacq/discriminating_generator.py`
2. Import `Solver` from pysat, `QuAcqTask` type hint
3. Implement `__init__(self, task, solver_name='glucose4')` — store task and solver_name
4. Implement `_get_learned_clauses_in_scope(self, learned_kb, scope)`:
   - For each `c_id` in `learned_kb`, get vars via `task._get_constraint_vars(c_id)`
   - If vars subset of scope, extend result with `task.constraint_clauses[c_id]`
5. Implement `generate(self, c_i, c_j, learned_kb, scope)`:
   - Get `cl_y` = `_get_learned_clauses_in_scope(learned_kb, scope)`
   - Get `bg` = `list(task.background_clauses)`
   - Get `clauses_i` = `task.constraint_clauses[c_i]`
   - Get `neg_j` = `task.negated_clauses[c_j]`
   - Create solver with `bg + cl_y + clauses_i + neg_j`
   - If SAT: return `task.model_to_config(solver.get_model())`
   - Else: return `None`
   - Always `solver.delete()` in finally block
6. Add export to `conacq/algorithms/quacq/__init__.py`

## Implementation Code

```python
"""
DiscriminatingGenerator: Paper Algorithm 3 line 5.

Generates discriminating examples from C_L[Y] (learned KB restricted to scope)
+ BG clauses, NOT from FM clauses (ground truth).
"""

from typing import Dict, List, Optional, Set

from pysat.solvers import Solver

from .task_preparation import QuAcqTask


class DiscriminatingGenerator:
    """Generate discriminating examples from learned KB restricted to scope.

    Paper Algorithm 3 line 5: choose e' in sol(C_L[Y]) s.t. e' |= c_i, e' |/= c_j.
    SAT formula: BG + C_L[Y] + c_i + neg(c_j).

    Args:
        task: QuAcqTask with constraint/negated clause maps and BG clauses
        solver_name: PySAT solver name
    """

    def __init__(self, task: QuAcqTask, solver_name: str = 'glucose4') -> None:
        self._task = task
        self._solver_name = solver_name

    def generate(self, c_i: int, c_j: int,
                 learned_kb: List[int], scope: Set[str]) -> Optional[Dict[str, bool]]:
        """Find e' s.t. e' in sol(BG + C_L[Y]) and e' |= c_i and e' |/= c_j.

        Args:
            c_i: Constraint ID that e' must satisfy
            c_j: Constraint ID that e' must violate
            learned_kb: Currently learned constraint IDs
            scope: Variable scope Y (feature names)

        Returns:
            Config dict if SAT, None if UNSAT
        """
        cl_y = self._get_learned_clauses_in_scope(learned_kb, scope)
        bg = list(self._task.background_clauses)
        clauses_i = self._task.constraint_clauses.get(c_i, [])
        neg_j = self._task.negated_clauses.get(c_j, [])

        solver = Solver(name=self._solver_name,
                        bootstrap_with=bg + cl_y + clauses_i + neg_j)
        try:
            if solver.solve():
                return self._task.model_to_config(solver.get_model())
        finally:
            solver.delete()
        return None

    def _get_learned_clauses_in_scope(self, learned_kb: List[int],
                                       scope: Set[str]) -> List[List[int]]:
        """C_L[Y]: learned constraint clauses restricted to scope Y."""
        clauses: List[List[int]] = []
        for c_id in learned_kb:
            c_vars = self._task._get_constraint_vars(c_id)
            if c_vars.issubset(scope):
                clauses.extend(self._task.constraint_clauses.get(c_id, []))
        return clauses
```

## Todo

- [x] Create `discriminating_generator.py` with class above
- [x] Add to `__init__.py` exports
- [x] Write unit test for DiscriminatingGenerator (SAT case, UNSAT case, empty learned_kb)
- [x] Verify: `task._get_constraint_vars()` and `task.model_to_config()` work correctly

## Success Criteria

- `DiscriminatingGenerator.generate()` returns valid config when SAT
- Returns `None` when no discriminating example exists
- Uses BG + C_L[Y] (not FM clauses)
- Unit tests pass

## Risk Assessment

- **Low risk**: Standalone new class, no existing code modified
- **Mitigation**: Tested in isolation before integration
