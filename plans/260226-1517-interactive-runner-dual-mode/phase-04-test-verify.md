# Phase 04: Test + Verify Both Modes

## Context Links

- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-refactor-runner.md), [Phase 02](phase-02-update-run-interactive.md), [Phase 03](phase-03-update-cross-validation.md)

## Overview

- **Priority**: High
- **Status**: complete
- **Description**: Run existing tests, verify both oracle and example modes work end-to-end.

## Implementation Steps

### 1. Run full test suite

```bash
PYTHONPATH=. pytest tests/ -v
```

All existing tests must pass. Key test files:
- `tests/test_interactive.py` — QuAcq, InteractiveLearner, QueryGenerator
- `tests/test_congen.py` — ConGen pipeline (should be unaffected)
- Any tests importing `InteractiveRunner` or `n_fold_cross_validation_interactive`

### 2. Verify oracle mode (standalone)

```bash
python -m apps.run_interactive apps/conf/run_interactive_config.toml -v
```

Expected: runs automated QuAcq, prints results, saves JSON to `data/results/interactive/`.

### 3. Verify example mode (CV)

```bash
python -m apps.run_cv apps/conf/run_cv_config.toml -v
```

With `algorithm = "interactive"` in config. Expected: n-fold CV completes, accuracy reported.

### 4. Verify import compatibility

```bash
PYTHONPATH=. python -c "from conacq.runners import InteractiveRunner, InteractiveRunResult; print('OK')"
PYTHONPATH=. python -c "from conacq.eval import InteractiveRunner, InteractiveRunResult; print('backward compat OK')"
```

## Todo List

- [ ] Run `pytest tests/ -v` — all pass
- [ ] Run `run_interactive.py` — oracle mode works
- [ ] Run `run_cv.py` with `algorithm=interactive` — example mode works
- [ ] Verify imports from both `conacq.runners` and `conacq.eval`
- [ ] Check JSON output has `bg_clauses` field

## Success Criteria

- Zero test failures
- Both entry points produce valid output
- `InteractiveRunResult` contains `bg_clauses` and `profiler_data`
- No regressions in ConGen pipeline

## Risk Assessment

- **Low**: Test config files may need `algorithm = "interactive"` to trigger interactive path
- **Low**: If no interactive test config exists, may need to temporarily modify `run_cv_config.toml`
