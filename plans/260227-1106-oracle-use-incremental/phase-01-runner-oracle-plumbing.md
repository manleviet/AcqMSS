# Phase 1: Runner + Oracle Plumbing

## Context
- Parent: [plan.md](plan.md)
- Brainstorm: [brainstorm report](../reports/brainstorm-260227-1111-oracle-use-incremental.md)

## Overview
- Priority: P1
- Status: complete
- Pass `use_incremental` from runner config through BaseRunner to Oracle

## Key Insights
- `BaseRunner.__init__()` hardcodes `use_incremental=False` — no technical reason
- `ConGenRunner` already has `use_incremental` param but doesn't pass to `super().__init__()`
- `InteractiveRunner` has no `use_incremental` param at all

## Related Code Files
- `conacq/runners/base_runner.py` — modify `__init__` signature
- `conacq/runners/congen_runner.py` — pass `use_incremental` to `super().__init__()`
- `conacq/runners/interactive_runner.py` — add param, pass to `super().__init__()`

## Implementation Steps

1. **`BaseRunner.__init__`** — add `use_incremental: bool = True` param, pass to `FeatureModelOracle`
   ```python
   def __init__(self, bias_path, fm_path, solver_name='glucose4', use_incremental=True):
       ...
       self.oracle = FeatureModelOracle(
           fm_path, solver_name=solver_name, use_incremental=use_incremental)
   ```

2. **`ConGenRunner.__init__`** — pass `use_incremental` to `super().__init__()`
   ```python
   super().__init__(bias_path, fm_path, solver_name, use_incremental=use_incremental)
   ```

3. **`InteractiveRunner.__init__`** — add `use_incremental: bool = True` param, pass to `super().__init__()`
   ```python
   def __init__(self, ..., use_incremental: bool = True):
       super().__init__(bias_path, fm_path, solver_name, use_incremental=use_incremental)
   ```

## Todo
- [x] Update BaseRunner.__init__ signature + Oracle creation
- [x] Update ConGenRunner super().__init__() call
- [x] Add use_incremental to InteractiveRunner, pass to super()

## Success Criteria
- Oracle receives configured `use_incremental` value from both runners
- Default True matches FeatureModelOracle's own default
- Backward compatible (no callers break)
