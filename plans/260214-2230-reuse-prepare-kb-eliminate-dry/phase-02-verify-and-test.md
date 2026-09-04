# Phase 02: Verify & Test

## Context

- Parent plan: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-replace-with-prepare-kb.md)

## Overview

- Priority: P3
- Status: completed
- Run existing tests to verify refactoring correctness. No new test files needed — existing parameterized tests cover ConGen flow.

## Implementation Steps

### Step 1: Run existing ConGen tests

```bash
PYTHONPATH=. python -m pytest tests/test_congen.py -v
```

All parameterized combinations (incremental/non-incremental, with/without profiling) must pass.

### Step 2: Run type check

```bash
PYTHONPATH=. python -m mypy acqmss/algorithms/task_preparation.py
```

### Step 3: Quick smoke test with app

```bash
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v
```

Verify output matches expected behavior.

## Todo

- [x] Existing tests pass
- [x] Type check passes
- [x] Smoke test produces same results

## Success Criteria

- Zero test regressions
- `constraint_to_assumption` and `assumption_to_constraint` maps identical to pre-refactor values
