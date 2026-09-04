from conacq.algorithms.quacq.quacq_model import _model_to_config

# Phase 2: Implement complete_configuration() in FeatureModelOracle

## Context Links
- [FMOracle](../../conacq/oracle/fm_oracle.py) -- target file
- [ExampleGenerator._generate_valid_config()](../../conacq/example_generators/base.py#L61-L109) -- SAT logic to extract
- [FeatureFrequency._generate_valid_config_for_coverage()](../../conacq/example_generators/feature_frequency.py#L172-L229) -- similar SAT logic

## Overview
- **Priority**: P2
- **Status**: Complete
- **Description**: Move SAT-solving configuration completion logic from generators into FeatureModelOracle

## Key Insights
- `_generate_valid_config()` in base.py creates a temp Solver, loads `get_cnf_clauses()`, solves with partial assumptions, extracts model. This is oracle-layer responsibility.
- `_generate_valid_config_for_coverage()` in feature_frequency.py does the same thing with different assumption building
- Both share identical pattern: create solver -> add CNF -> solve with assumptions -> extract config from model -> delete solver
- The new `complete_configuration()` should handle the core SAT solve + config extraction; assumption building stays in generators (that's sampling policy)

## Requirements

### Functional
- `complete_configuration(partial)` takes a partial assignment dict `{feature_name: True/False}` (subset of features)
- Converts partial dict to SAT assumptions: `fid` if True, `-fid` if False
- Creates temp Solver with raw FM CNF clauses
- Solves with assumptions; if SAT, returns full config dict
- If UNSAT with assumptions, retries WITHOUT assumptions (fallback)
- If still UNSAT, returns None
- Cleans up solver in finally block

### Non-Functional
- FeatureModelOracle stays under 200 lines
- Method should be ~30 lines

## Architecture

```python
def complete_configuration(self, partial: Dict[str, bool]) -> Optional[Dict[str, bool]]:
    """Complete a partial configuration to a full valid one via SAT solving.

    Args:
        partial: Partial assignment {feature_name: True/False} for subset of features

    Returns:
        Full valid configuration dict, or None if no valid completion exists
    """
    assumptions = []
    for name, value in partial.items():
        fid = self._oracle_model.variables[name]
        assumptions.append(fid if value else -fid)

    solver = Solver(name='glucose4')
    for clause in self.get_cnf_clauses():
        solver.add_clause(clause)

    try:
        if solver.solve(assumptions=assumptions):
            return _model_to_config(solver.get_model())
        # Fallback: try without assumptions
        if solver.solve():
            return _model_to_config(solver.get_model())
    finally:
        solver.delete()

    return None


def _model_to_config(self, model: List[int]) -> Dict[str, bool]:
    """Convert SAT model to feature config dict."""
    return {name: fid in model
            for name, fid in self._oracle_model.variables.items()}
```

## Related Code Files

### Files to Modify
- `acqmss/oracle/fm_oracle.py` -- add `complete_configuration()` and `_model_to_config()` helper

### Files NOT Modified (yet)
- `acqmss/example_generators/base.py` -- Phase 3
- `acqmss/example_generators/feature_frequency.py` -- Phase 3

## Implementation Steps

1. **Add import** in `fm_oracle.py`: `from pysat.solvers import Solver` (at top, third-party section)

2. **Add `_model_to_config()` private helper** after `get_constraint_descriptions()`:
   - Converts SAT model (List[int]) to Dict[str, bool] using `self._oracle_model.variables`

3. **Add `complete_configuration()`** after `is_valid()` (in the Oracle ABC implementation section):
   - Convert partial dict to SAT literal assumptions
   - Create temp Solver with raw FM CNF
   - Solve with assumptions; fallback without; return None if UNSAT
   - Use `_model_to_config()` to extract result

4. **Verify**: `PYTHONPATH=. python -c "from acqmss.oracle import FeatureModelOracle; o = FeatureModelOracle('data/fms/REAL-FM-7.uvl'); print(o.complete_configuration({'IDE': True}))"`

## Todo List

- [x] Add `Solver` import to fm_oracle.py
- [x] Implement `_model_to_config()` helper
- [x] Implement `complete_configuration()`
- [x] Manual smoke test with REAL-FM-7

## Success Criteria
- `FeatureModelOracle.complete_configuration({'IDE': True})` returns full valid config
- `FeatureModelOracle.complete_configuration({})` returns any valid config (empty partial = no constraints)
- Method handles unknown feature names gracefully (KeyError from variables dict)
- fm_oracle.py stays under 200 lines

## Risk Assessment
- **Low**: Logic extracted directly from working generator code
- **Solver lifecycle**: temp solver created and deleted per call (same pattern as generators today). Not a performance concern since generators already do this.

## Security Considerations
- None (SAT solving is CPU-bound, no I/O beyond existing FM data)

## Next Steps
- Phase 3: Refactor generators to use `oracle.complete_configuration()`
