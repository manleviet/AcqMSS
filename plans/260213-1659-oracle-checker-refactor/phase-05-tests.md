# Phase 5: Tests & Verification

## Context Links
- [Parent plan](plan.md)
- [Phase 3](phase-03-refactor-oracle.md) | [Phase 4](phase-04-refactor-quacq.md)

## Overview
- **Priority**: P1
- **Status**: pending
- **Description**: Run existing tests to verify no regressions. Add unit tests for OracleModel and OneShotModel.

## Requirements
- All existing tests pass unchanged
- New tests for OracleModel (constraint_map + variables pattern)
- New tests for OneShotModel one-shot pattern

## Related Code Files
### Files to Create
- `tests/test_oracle_model.py` (~70 lines)

## Implementation Steps

1. Run existing test suite:
   ```bash
   PYTHONPATH=. python -m pytest tests/ -v
   ```

2. Create `tests/test_oracle_model.py`:
   ```python
   """Tests for FMOracleModel and OneShotModel."""

   class TestOracleModel:
       def test_from_fm_creates_valid_model(self):
           """FMOracleModel.from_fm produces valid set_kb and assumptions."""
           # Simple FM: f1 OR f2 (clause [1, 2])
           constraint_map = {"fm": [[1, 2]]}
           variables = {"f1": 1, "f2": 2}
           model = OracleModel.from_fm_data(constraint_map, variables, next_tseitin_var=2)

           assert len(model.get_assumptions()) == 4  # 2 features * 2 (pos+neg)
           assert model.use_incremental is True
           # set_kb = 1 FM clause + 4 guarded clauses
           assert len(model.get_kb()) == 1 + 4

       def test_constraint_map_and_variables(self):
           """Verify constraint_map + variables stored correctly."""
           constraint_map = {"fm": [[1, 2], [-1, 3]]}
           variables = {"f1": 1, "f2": 2, "f3": 3}
           model = OracleModel.from_fm_data(constraint_map, variables, next_tseitin_var=3)

           assert model.constraint_map == constraint_map
           assert model.variables == variables

       def test_config_to_active_assumptions(self):
           """Config dict correctly maps to assumption IDs."""
           constraint_map = {"fm": [[1, 2]]}
           variables = {"f1": 1, "f2": 2}
           model = OracleModel.from_fm_data(constraint_map, variables, next_tseitin_var=2)

           active = model.with_configuration({"f1": True, "f2": False})
           assert len(active) == 2
           assert model._pos_assignment_to_assumption["f1"] in active
           assert model._neg_assignment_to_assumption["f2"] in active

       def test_checker_integration(self):
           """CheckerFactory creates valid checker from FMOracleModel."""
           constraint_map = {"fm": [[1, 2]]}  # f1 OR f2
           variables = {"f1": 1, "f2": 2}
           model = OracleModel.from_fm_data(constraint_map, variables, next_tseitin_var=2)
           checker = CheckerFactory.create_from_model(model, 'glucose4')

           # f1=True, f2=True → SAT (both true satisfies f1 OR f2)
           active = model.with_configuration({"f1": True, "f2": True})
           assert checker.is_consistent(active) is True

           # f1=False, f2=False → UNSAT (neither true violates f1 OR f2)
           active = model.with_configuration({"f1": False, "f2": False})
           assert checker.is_consistent(active) is False

           checker.cleanup()

   class TestOneShotModel:
       def test_bakes_unit_clauses(self):
           """OneShotModel bakes assumptions as unit clauses into set_kb."""
           clauses = [[1, 2], [-1, 3]]
           model = OneShotModel(clauses, [1, -2])

           kb = model.get_kb()
           assert [1] in kb  # unit clause for assumption 1
           assert [-2] in kb  # unit clause for assumption -2
           assert model.get_assumptions() == []
           assert model.use_incremental is False

       def test_oneshot_checker_integration(self):
           """Factory creates NonIncremental checker from OneShotModel."""
           # SAT: [1, 2] with unit [1] → satisfiable
           model = OneShotModel([[1, 2]], [1])
           checker = CheckerFactory.create_from_model(model, 'glucose4')
           assert checker.is_consistent([]) is True
           checker.cleanup()

           # UNSAT: [1] and [-1] → unsatisfiable
           model = OneShotModel([[1], [-1]])
           checker = CheckerFactory.create_from_model(model, 'glucose4')
           assert checker.is_consistent([]) is False
           checker.cleanup()
   ```

3. Run new tests:
   ```bash
   PYTHONPATH=. python -m pytest tests/test_oracle_model.py -v
   ```

4. Run full suite to catch regressions:
   ```bash
   PYTHONPATH=. python -m pytest tests/ -v --tb=short
   ```

## Todo List
- [ ] Run existing test suite — all pass
- [ ] Create test_oracle_model.py
- [ ] Test OracleModel with constraint_map + variables pattern
- [ ] Test config_to_active_assumptions mapping
- [ ] Test OneShotModel unit clause baking
- [ ] Test CheckerFactory integration for both models
- [ ] Full regression run passes

## Success Criteria
- Zero test failures across entire suite
- New tests cover: model creation, constraint_map/variables storage, config mapping, checker integration, SAT/UNSAT correctness
- Both OracleModel and OneShotModel work with CheckerFactory.create_from_model

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Existing interactive tests fail | Medium | High | Run early, fix in Phase 3/4 before this phase |
| Flaky SAT results | Very Low | Medium | Deterministic test cases (simple FM clauses) |

## Next Steps
- All phases complete → ready for code review and merge
