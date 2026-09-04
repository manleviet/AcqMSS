# Phase 02: Update run_interactive.py to Use InteractiveRunner

## Context Links

- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-refactor-runner.md)

## Overview

- **Priority**: High
- **Status**: complete
- **Description**: Replace direct `InteractiveLearner` usage in `run_interactive.py` with `InteractiveRunner`, eliminating duplicate profiler/memory/save logic.

## Key Insights

- `run_interactive.py` currently does: `InteractiveLearner.from_files()` → `learner.learn(mode)` → manual profiler + verbose + save
- After refactoring: `InteractiveRunner(bias_path, fm_path)` → `runner.run(mode='automated')` → save from result
- Verbose output currently reads `learner.task.bias` and `learner.task.background` — need alternative source
- `runner.bias_clauses` provides bias size; `runner.feature_ids` provides features count
- `bg_clauses` now comes from `InteractiveRunResult.bg_clauses`

## Related Code Files

| File | Action | Current LOC |
|------|--------|-------------|
| `apps/run_interactive.py` | **Rewrite** `process_model()` + simplify `main()` | 205 |

## Implementation Steps

### 1. Replace imports

```python
# Remove:
from conacq.algorithms.interactive import InteractiveLearner

# Add:
from conacq.runners import InteractiveRunner
```

### 2. Rewrite `process_model()`

**Before** (current):
```python
learner = InteractiveLearner.from_files(fm_path, bias_path, solver_name)
result = learner.learn(mode=mode, max_queries=max_queries)
bg_clauses = [[lit] for lit in learner.task.background]
save_kb_result(kb_constraints=result.kb_constraints, ...)
```

**After**:
```python
runner = InteractiveRunner(bias_path=model_config.bias, fm_path=model_config.oracle,
                           solver_name=solver_name, max_queries=max_queries)
run_result = runner.run(mode=mode)
save_kb_result(kb_constraints=run_result.kb_constraints,
               bg_clauses=run_result.bg_clauses, ...)
runner.cleanup()
```

### 3. Adapt verbose output

**Before**: reads `learner.task.bias`, `learner.task.feature_ids`
**After**: reads `runner.bias_clauses`, `runner.feature_ids`

```python
if verbose:
    print(f"  Bias constraints: {len(runner.bias_clauses)}")
    print(f"  Features: {len(runner.feature_ids)}")
```

### 4. Simplify profiler usage

Remove `use_global_profiler()` + `profiler.start()/stop()` from `main()` — runner handles profiler via `profiler_session` internally. Keep only top-level timing for summary if desired.

### 5. Update save_kb_result call

Use fields from `InteractiveRunResult` directly:
- `run_result.kb_constraints`
- `run_result.bg_clauses` (new field, no manual extraction)
- `run_result.n_kb`, `run_result.n_queries`, etc.

## Todo List

- [ ] Replace imports
- [ ] Rewrite `process_model()` to use `InteractiveRunner`
- [ ] Adapt verbose output to use runner attributes
- [ ] Simplify/remove global profiler from `main()`
- [ ] Update `save_kb_result()` call with new result fields
- [ ] Return `run_result` (or wrapper) from `process_model()`

## Success Criteria

- `python -m apps.run_interactive apps/conf/run_interactive_config.toml -v` works
- `--interactive` flag still routes to user prompt mode
- Output JSON has same structure as before
- No `InteractiveLearner` import in `run_interactive.py`

## Risk Assessment

- **Low**: Verbose output before `run()` needs bias/feature counts — available from `runner.bias_clauses`/`runner.feature_ids`
- **Low**: Global profiler removal may change summary output format — acceptable

## Next Steps

→ Phase 03: Update `cross_validation.py` caller
