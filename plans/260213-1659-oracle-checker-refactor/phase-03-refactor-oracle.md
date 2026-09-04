from conacq.algorithms.quacq.quacq_model import _model_to_config

# Phase 3: Refactor FeatureModelOracle

## Context Links
- [Parent plan](plan.md) | [Phase 2](phase-02-oracle-model.md)
- [fm_oracle.py](../../conacq/oracle/fm_oracle.py) — current implementation
- [checker.py](../../explanation/operations/algorithms/checker.py) — CheckerFactory

## Overview
- **Priority**: P1
- **Status**: pending
- **Description**: Replace raw PySAT Solver in FeatureModelOracle with ConsistencyChecker created via `CheckerFactory.create_from_model(OracleModel)`. Build OracleModel using `constraint_map` + `variables` from FM data that Oracle already parses.

## Key Insights
1. Oracle already parses FM → `cnf_clauses` + `feature_ids`. These map directly to `constraint_map` + `variables`.
2. `is_valid()` → checker.is_consistent() with feature assumption activation
3. `get_valid_configuration()` → keep raw Solver (needs `get_model()`)
4. `max_var` calculation: `max(abs(lit) for clause in cnf_clauses for lit in clause)` → `next_tseitin_var`

## Requirements
- `is_valid()` uses checker.is_consistent() with profiling
- `get_valid_configuration()` keeps raw Solver (needs model extraction)
- Add `profiler` and `solver_name` constructor params
- Backward compatible: `FeatureModelOracle(fm_path)` still works

## Related Code Files
### Files to Modify
- `acqmss/oracle/fm_oracle.py`

### Dependencies
- `acqmss/oracle/oracle_model.py` (Phase 2)
- `explanation/operations/algorithms/checker.py` (Phase 1)

## Implementation Steps

1. Add imports to `fm_oracle.py`:
   ```python
   from conacq.oracle.fm_oracle_model import FMOracleModel
   from explanation.operations.algorithms.checker import CheckerFactory
   from explanation.utils.profiler import get_global_profiler, AbstractProfiler
   ```

2. Update `__init__` signature:
   ```python
   def __init__(self, fm_path: str, solver_name: str = 'glucose4',
                profiler: AbstractProfiler = None):
   ```

3. In `__init__`, after parsing FM (cnf_clauses, feature_ids available), replace raw Solver creation:
   ```python
   # REMOVE: self.solver = Solver(name='glucose4')
   # REMOVE: for clause in self.cnf_clauses: self.solver.add_clause(clause)

   # NEW: Build FMOracleModel using constraint_map + variables pattern
   self.solver_name = solver_name
   self.profiler = profiler if profiler is not None else get_global_profiler()

   constraint_map = {"fm": self.cnf_clauses}
   max_var = max(abs(lit) for clause in self.cnf_clauses for lit in clause)
   self._oracle_model = OracleModel.from_fm_data(
       constraint_map=constraint_map,
       variables=self.feature_ids,
       next_tseitin_var=max_var
   )
   self.checker = CheckerFactory.create_from_model(
       self._oracle_model, solver_name, self.profiler
   )
   ```

4. Refactor `is_valid()`:
   ```python
   def is_valid(self, assignments: Dict[str, bool]) -> bool:
       active = self._oracle_model.with_configuration(assignments)
       return self.checker.is_consistent(active)
   ```

5. Refactor `get_valid_configuration()` to use fresh raw Solver (needs get_model):
   ```python
   def get_valid_configuration(self, assumptions=None):
       solver = Solver(name=self.solver_name, bootstrap_with=self.cnf_clauses)
       try:
           if solver.solve(assumptions=assumptions or []):
               return _model_to_config(solver.get_model())
           return None
       finally:
           solver.delete()
   ```
   Note: `_model_to_config` extracts config dict from solver model (reuse existing loop logic).

6. Update `cleanup()` / `__del__`:
   ```python
   def cleanup(self):
       if hasattr(self, 'checker') and self.checker is not None:
           self.checker.cleanup()
           self.checker = None

   def __del__(self):
       self.cleanup()
   ```

7. Remove old `self.solver` references.

## Todo List
- [ ] Add imports (OracleModel, CheckerFactory, profiler)
- [ ] Update `__init__` with solver_name, profiler params
- [ ] Build constraint_map from cnf_clauses, variables from feature_ids
- [ ] Replace raw Solver with OracleModel.from_fm + CheckerFactory
- [ ] Refactor `is_valid()` to use checker.is_consistent()
- [ ] Keep `get_valid_configuration()` with raw Solver (needs get_model)
- [ ] Update cleanup/del methods
- [ ] Verify all Oracle callers still work

## Success Criteria
- `oracle.is_valid(config)` returns identical results as before
- `oracle.get_valid_configuration()` returns identical results as before
- Profiler captures solver timing for `is_valid()` calls
- No breaking changes to Oracle API

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Oracle callers pass unexpected params | Low | Low | Default values preserve backward compat |
| get_valid_configuration perf regression (fresh solver) | Low | Low | Called rarely (example generation only) |
| Feature name mismatch between FM and config | Low | Medium | Same behavior as before (KeyError) |

## Next Steps
- Phase 4: Refactor QuAcq components
