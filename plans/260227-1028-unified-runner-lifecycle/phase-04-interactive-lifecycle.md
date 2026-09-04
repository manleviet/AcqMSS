# Phase 04: Align InteractiveRunner to Build-Once Lifecycle

## Context
- Parent: [plan.md](plan.md)
- Depends on: Phase 03

## Overview
- **Priority**: High
- **Status**: Complete
- **Progress**: 100%
- **Description**: Move InteractiveRunner's model creation from run() to __init__(), matching ConGenRunner's build-once pattern

## Key Insights
- InteractiveModel and FeatureModelOracle are safe to reuse (confirmed by reusability analysis)
- QuAcqTask accumulates state but `model.prepare(oracle)` creates fresh task each run
- ConGenRunner pattern: build model+oracle in __init__, call model.prepare() per fold
- InteractiveRunner currently: creates model+oracle per run (wasteful for CV)
- Oracle already moved to BaseRunner.__init__() in Phase 03

## Requirements
- Move `InteractiveModel.from_bias(bias_path)` to __init__()
- Keep `model.prepare(oracle)` in run() (creates fresh task per fold)
- Remove per-run oracle creation (handled by BaseRunner)
- Profiler remains per-run (created in run() scope)
- Oracle for QuAcq learning: use self.oracle (from BaseRunner), not per-run instance

## Related Code Files
- **Modify**: `conacq/runners/interactive_runner.py`

## Implementation Steps

1. Move `InteractiveModel.from_bias(self.bias_path)` to `__init__()`
2. Store as `self.model`
3. In `run()`: call `model.prepare(oracle)` with `self.oracle` (from BaseRunner)
4. Profiler: still created per-run in `run()` scope (passed to QuAcq, not oracle)
5. Oracle profiler: InteractiveRunner currently passes profiler to FeatureModelOracle constructor. After refactor, oracle is created without profiler in BaseRunner. Need to assess if oracle needs profiler for QuAcq runs. If yes, use `oracle.set_profiler(profiler)` pattern or pass profiler separately.
6. Remove `self.bias_path` / `self.fm_path` storage (moved to BaseRunner)
7. Update `feature_ids` to use `self.model.feature_ids` (or similar)
8. Update cleanup() to call `super().cleanup()`
9. Update `_run_oracle_mode` and `_run_example_mode` to use `self.oracle`

## Todo
- [x] Move InteractiveModel creation to __init__()
- [x] Update run() to use self.oracle and self.model
- [x] Handle profiler for oracle (assess if needed)
- [x] Update _run_oracle_mode and _run_example_mode
- [x] Remove per-run oracle creation
- [x] Remove no-op cleanup() (inherited from BaseRunner)

## Completion Summary
- InteractiveModel created in __init__() and stored as self.model
- run() calls model.prepare(oracle) with self.oracle from BaseRunner
- Per-run oracle creation removed (now handled by BaseRunner)
- Profiler created per-run in run() scope (passed to QuAcq, not oracle)
- _run_oracle_mode and _run_example_mode use self.oracle and self.model
- cleanup() inherited from BaseRunner (no override needed)
- InteractiveRunner now follows identical build-once lifecycle as ConGenRunner

## Success Criteria
- InteractiveRunner follows build-once lifecycle
- model.prepare(oracle) called per fold (fresh task)
- Oracle shared across folds (not recreated)
- All interactive tests pass

## Risk Assessment
- **Oracle profiler**: InteractiveRunner currently passes profiler to FeatureModelOracle. Without profiler, oracle metrics (SAT calls inside oracle) won't be captured. Evaluate if these metrics are needed. If yes, consider `oracle.profiler = profiler` setter per-run.
- **Model state**: InteractiveModel must not accumulate state between runs. Confirmed safe by analysis.

## Next Steps
- Phase 05 cleans up CV loop to use typed BaseRunner
