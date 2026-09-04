# Phase 2: Create OracleModel + Preparation

## Context Links
- [Parent plan](plan.md) | [Phase 1](phase-01-checker-model-protocol.md)
- [CONGENModel](../../conacq/algorithms/congen_model.py) — reference pattern (constraint_map + variables + prepare)
- [CONGENTaskPreparation](../../conacq/algorithms/task_preparation.py) — reference pattern
- [DiagnosisModel](../../explanation/models/pysat_diagnosis_model.py) — same data structure
- [fm_oracle.py](../../conacq/oracle/fm_oracle.py) — current Oracle

## Overview
- **Priority**: P1 (blocks Phase 3)
- **Status**: pending
- **Description**: Create `OracleModel` following CONGENModel's data structure pattern: `constraint_map` + `variables` + `prepare()`. Replaces the old plan's custom `fm_clauses`/`feature_ids` approach.

## Key Insights
1. **CONGENModel pattern**: `constraint_map: Dict[str, List[List[int]]]`, `variables: Dict[str, int]`, `next_tseitin_var: int`, `prepare()` delegates to TaskPreparation
2. **Same data structures**: `constraint_map` ≡ fm_clauses (structured), `variables` ≡ feature_ids
3. **FM clauses → direct in set_kb** (always active, NOT assumption-guarded)
4. **Feature assignments → assumption-guarded**: `[-a_pos_i, fid]` (if a_pos active → feature true), `[-a_neg_i, -fid]` (if a_neg active → feature false)
5. **Assumption IDs** start after `next_tseitin_var` to avoid variable conflicts
6. `is_valid(config)` → activate relevant feature assumptions → `checker.is_consistent(active)`

## Requirements
- OracleModel has `constraint_map`, `variables`, `next_tseitin_var` (same fields as CONGENModel/DiagnosisModel)
- After `prepare()`: satisfies CheckerModel Protocol (`get_kb()`, `get_assumptions()`, `use_incremental`)
- `config_to_active_assumptions(config)` maps `Dict[str, bool]` → `List[int]`
- OracleModel lives in `acqmss/oracle/` (near the Oracle it serves)

## Architecture

```
Input (same data structure as CONGENModel):
  constraint_map = {"fm": [[1,-2], [3,4], ...]}  # FM constraints
  variables = {"f1": 1, "f2": 2, "f3": 3}        # feature_name → var_id
  next_tseitin_var = N  (max var in FM)

After prepare() (assumption vars start at N+1):
  a_pos_1 = N+1, a_neg_1 = N+2    (for f1)
  a_pos_2 = N+3, a_neg_2 = N+4    (for f2)
  a_pos_3 = N+5, a_neg_3 = N+6    (for f3)

set_kb:
  [1,-2], [3,4], ...           # FM clauses (direct, always active)
  [-N-1, 1]                    # if a_pos_1 active → f1=true
  [-N-2, -1]                   # if a_neg_1 active → f1=false
  [-N-3, 2]                    # if a_pos_2 active → f2=true
  [-N-4, -2]                   # if a_neg_2 active → f2=false
  ...

assumptions = [N+1, N+2, N+3, N+4, N+5, N+6]  # all feature assumptions

is_valid({f1:T, f2:F, f3:T}):
  activate = [N+1, N+4, N+5]  # a_pos_1, a_neg_2, a_pos_3
  checker.is_consistent(activate)
  → _compute_delta splits: enabled=[N+1,N+4,N+5], disabled=[N+2,N+3,N+6]
  → f1=T enforced, f1=F deactivated, f2=T deactivated, f2=F enforced, ...
```

## Related Code Files
### Files to Create
- `acqmss/oracle/oracle_model.py` (~90 lines) — OracleModel + OracleTaskPreparation

### Files NOT Modified
- No existing files changed in this phase

## Implementation Steps

1. Create `acqmss/oracle/oracle_model.py`

2. Define `OracleModel` (follows CONGENModel pattern):
   ```python
   class OracleModel:
       """Model for Oracle FM validation via ConsistencyChecker.

       Uses constraint_map + variables pattern (same as DiagnosisModel/ConGenModel).
       Satisfies CheckerModel Protocol after prepare().
       """

       def __init__(self):
           # Same data structure as ConGenModel/DiagnosisModel
           self.constraint_map: Dict[str, List[List[int]]] = {}
           self.variables: Dict[str, int] = {}
           self.next_tseitin_var: int = 0
           self.use_incremental: bool = True

           # Populated after prepare()
           self._set_kb: List[List[int]] = []
           self._assumptions: List[int] = []
           self._feature_to_pos_assumption: Dict[str, int] = {}
           self._feature_to_neg_assumption: Dict[str, int] = {}

       def get_kb(self) -> List[List[int]]:
           return self._set_kb

       def get_assumptions(self) -> List[int]:
           return self._assumptions

       def config_to_active_assumptions(self, config: Dict[str, bool]) -> List[int]:
           """Convert feature config to list of assumption IDs to activate."""
           active = []
           for name, value in config.items():
               if value:
                   active.append(self._feature_to_pos_assumption[name])
               else:
                   active.append(self._feature_to_neg_assumption[name])
           return active

       def prepare(self) -> 'FMOracleModel':
           """Build set_kb + assumptions. Delegates to OracleTaskPreparation."""
           OracleTaskPreparation.prepare(self)
           return self

       @classmethod
       def from_fm(cls, constraint_map: Dict[str, List[List[int]]],
                   variables: Dict[str, int],
                   next_tseitin_var: int) -> 'FMOracleModel':
           """Factory method: create from FM data and prepare."""
           model = cls()
           model.constraint_map = constraint_map
           model.variables = variables
           model.next_tseitin_var = next_tseitin_var
           return model.prepare()
   ```

3. Define `OracleTaskPreparation`:
   ```python
   class OracleTaskPreparation:
       """Prepare assumption-guarded clauses for Oracle FM validation.

       FM constraints → direct in set_kb (always active).
       Feature assignments → assumption-guarded unit clauses.
       """

       @staticmethod
       def prepare(model: 'FMOracleModel') -> None:
           set_kb = []
           assumptions = []

           # Step 1: FM constraints from constraint_map → direct in set_kb
           for clauses in model.constraint_map.values():
               set_kb.extend(clauses)

           # Step 2: Feature assignments → assumption-guarded
           id_assumption = model.next_tseitin_var + 1
           feature_to_pos = {}
           feature_to_neg = {}

           for name, fid in model.variables.items():
               # a_pos: if active → feature must be true
               a_pos = id_assumption
               set_kb.append([-a_pos, fid])
               assumptions.append(a_pos)
               feature_to_pos[name] = a_pos
               id_assumption += 1

               # a_neg: if active → feature must be false
               a_neg = id_assumption
               set_kb.append([-a_neg, -fid])
               assumptions.append(a_neg)
               feature_to_neg[name] = a_neg
               id_assumption += 1

           model._set_kb = set_kb
           model._assumptions = assumptions
           model._pos_assignment_to_assumption = feature_to_pos
           model._neg_assignment_to_assumption = feature_to_neg
   ```

4. Add exports to `acqmss/oracle/__init__.py` if needed.

## Todo List
- [ ] Create `oracle_model.py` with OracleModel + OracleTaskPreparation
- [ ] OracleModel uses `constraint_map` + `variables` (same as CONGENModel)
- [ ] After `prepare()`: satisfies CheckerModel Protocol (get_kb, get_assumptions, use_incremental)
- [ ] FM clauses from constraint_map → direct in set_kb (always active)
- [ ] Feature assignments derived from variables → assumption-guarded
- [ ] `config_to_active_assumptions` converts Dict[str, bool] → List[int]
- [ ] Assumption IDs start after next_tseitin_var
- [ ] File under ~100 lines

## Success Criteria
- `OracleModel.from_fm(constraint_map, variables, next_tseitin_var)` creates valid model
- `CheckerFactory.create_from_model(oracle_model)` returns IncrementalPySATChecker
- `checker.is_consistent(model.config_to_active_assumptions(config))` returns same as raw `Solver.solve(assumptions=[...])`

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Assumption ID collision with FM vars | Low | High | next_tseitin_var + 1 start ensures no overlap |
| Feature not in variables | Low | Medium | KeyError naturally raised, same as current Oracle |
| Performance: 2 extra clauses per feature | Very Low | Very Low | Negligible overhead |

## Next Steps
- Phase 3 uses OracleModel in FeatureModelOracle
