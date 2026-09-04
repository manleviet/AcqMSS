# Phase 4: Refactor QuAcq Components

## Context Links
- [Parent plan](plan.md) | [Phase 1](phase-01-checker-model-protocol.md)
- [findscope.py](../../conacq/algorithms/interactive/findscope.py)
- [findc.py](../../conacq/algorithms/interactive/findc.py)
- [quacq.py](../../conacq/algorithms/interactive/quacq.py)

## Overview
- **Priority**: P1
- **Status**: pending
- **Description**: Replace raw PySAT Solver in QuAcq's FM consistency checks with factory-created NonIncrementalPySATChecker. One-shot pattern: bake FM + assumptions as unit clauses into set_kb, use `is_consistent([])`.

## Key Insights
1. QuAcq one-shot checks bake assumptions as **unit clauses** into set_kb — no assumption-guard mechanism needed
2. For one-shot: set_kb = FM clauses + `[[lit] for lit in assumptions]`, assumptions = [], `is_consistent([])` checks SAT
3. Need lightweight model satisfying CheckerModel Protocol for CheckerFactory.create_from_model
4. `_narrow_with_sat()` and `_is_consistent()` in quacq.py keep raw Solver (dynamic clause sets / need get_model)

## Requirements
- Create `OneShotModel` — minimal CheckerModel for one-shot SAT checks
- Replace `_check_partial_consistency()` in findscope with checker
- Replace `_check_fm_consistency()` in findc with checker (keep `_narrow_with_sat()` raw)
- Replace `_check_consistency_with_fm()` in quacq with checker (keep `_is_consistent()` raw)
- Pass profiler through to all components

## Architecture

```
OneShotModel:
  set_kb = fm_clauses + [[lit] for lit in unit_assumptions]
  assumptions = []
  use_incremental = False

CheckerFactory.create_from_model(model) → NonIncrementalPySATChecker
checker.is_consistent([]) → solve set_kb with no assumptions → SAT/UNSAT
```

## Related Code Files
### Files to Create
- Add `OneShotModel` to `acqmss/oracle/oracle_model.py` (colocate with OracleModel, ~15 lines)

### Files to Modify
- `acqmss/algorithms/interactive/findscope.py` — replace `_check_partial_consistency()`
- `acqmss/algorithms/interactive/findc.py` — replace `_check_fm_consistency()`
- `acqmss/algorithms/interactive/quacq.py` — replace `_check_consistency_with_fm()`

### Files NOT Modified (keep raw Solver)
- `findc._narrow_with_sat()` — needs get_model()
- `quacq._is_consistent()` — dynamic clause sets, not FM-specific

## Implementation Steps

### Step 1: Add OneShotModel to oracle_model.py

```python
class OneShotModel:
    """Minimal CheckerModel for one-shot SAT checks.

    Bakes all clauses + unit assumptions into set_kb.
    Satisfies CheckerModel Protocol for CheckerFactory.
    """
    use_incremental = False

    def __init__(self, clauses: List[List[int]], unit_assumptions: List[int] = None):
        self._set_kb = list(clauses)
        if unit_assumptions:
            self._set_kb.extend([lit] for lit in unit_assumptions)

    def get_kb(self) -> List[List[int]]:
        return self._set_kb

    def get_assumptions(self) -> List[int]:
        return []
```

### Step 2: Refactor findscope.py

Replace `_check_partial_consistency(fm_clauses, partial_assumptions, solver_name)`:

```python
def _check_partial_consistency(fm_clauses, partial_assumptions, solver_name, profiler=None):
    model = OneShotModel(fm_clauses, partial_assumptions)
    checker = CheckerFactory.create_from_model(model, solver_name, profiler)
    try:
        return checker.is_consistent([])
    finally:
        checker.cleanup()
```

Update callers to pass `profiler` parameter through.

### Step 3: Refactor findc.py

Replace `_check_fm_consistency(fm_clauses, assumptions, solver_name)`:

```python
def _check_fm_consistency(fm_clauses, assumptions, solver_name, profiler=None):
    model = OneShotModel(fm_clauses, assumptions)
    checker = CheckerFactory.create_from_model(model, solver_name, profiler)
    try:
        return checker.is_consistent([])
    finally:
        checker.cleanup()
```

**Keep `_narrow_with_sat()` unchanged** — it needs `solver.get_model()`.

### Step 4: Refactor quacq.py

Replace `_check_consistency_with_fm(self, fm_clauses, e_assumptions)`:

```python
def _check_consistency_with_fm(self, fm_clauses, e_assumptions):
    model = OneShotModel(fm_clauses, e_assumptions)
    checker = CheckerFactory.create_from_model(model, self.solver_name, self.profiler)
    try:
        return checker.is_consistent([])
    finally:
        checker.cleanup()
```

**Keep `_is_consistent(self, clauses)` unchanged** — generic SAT on dynamic clause sets.

### Step 5: Add imports to all modified files

```python
from conacq.oracle.fm_oracle_model import OneShotModel
from explanation.operations.algorithms.checker import CheckerFactory
```

## Todo List
- [ ] Add OneShotModel to oracle_model.py
- [ ] Refactor findscope._check_partial_consistency → OneShotModel + factory
- [ ] Refactor findc._check_fm_consistency → OneShotModel + factory
- [ ] Refactor quacq._check_consistency_with_fm → OneShotModel + factory
- [ ] Pass profiler through findscope/findc function params
- [ ] Keep _narrow_with_sat and _is_consistent raw Solver unchanged
- [ ] Remove unused PySAT Solver imports where applicable

## Success Criteria
- All QuAcq interactive tests pass
- FM consistency checks return identical results
- Profiler captures timing for refactored checks
- `_narrow_with_sat` and `_is_consistent` unchanged

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| OneShotModel overhead vs raw Solver | Very Low | Very Low | Thin wrapper, same solver lifecycle |
| findscope/findc are module-level functions | Low | Low | Pass profiler as param (default None) |
| Circular import oracle_model ↔ checker | Very Low | Medium | oracle_model imports from explanation (one-way) |

## Next Steps
- Phase 5: Run all tests, verify no regressions
