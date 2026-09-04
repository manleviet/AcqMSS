# Phase 03: Test + Lint

## Context Links

- Tests: `tests/test_evaluation.py`
- Lint: `ruff check .` / `ruff format .`
- Plan: [plan.md](plan.md)

## Overview

- **Priority**: P2
- **Status**: completed
- **Description**: Run existing tests and linter to confirm refactor is behavior-preserving.

## Key Insights

- No direct unit tests for `n_fold_cross_validation()` or `n_fold_cross_validation_interactive()` found in `tests/`
- CV functions tested indirectly via `apps/run_congen_eval.py` and `apps/run_interactive_eval.py` integration
- `tests/test_evaluation.py` tests accuracy/metrics — may import from `acqmss.eval` (verify imports work)
- Ruff check + format ensures code style compliance

## Requirements

- All existing tests pass
- No ruff lint errors
- No ruff format changes needed
- Module imports work (`python -c "from acqmss.eval import n_fold_cross_validation, n_fold_cross_validation_interactive"`)

## Implementation Steps

### Step 1: Lint check

```bash
ruff check acqmss/eval/cross_validation.py
ruff format --check acqmss/eval/cross_validation.py
```

Fix any issues.

### Step 2: Import verification

```bash
PYTHONPATH=. python -c "from acqmss.eval import n_fold_cross_validation, n_fold_cross_validation_interactive; print('OK')"
```

### Step 3: Run evaluation tests

```bash
PYTHONPATH=. pytest tests/test_evaluation.py -v
```

### Step 4: Run full test suite

```bash
PYTHONPATH=. pytest tests/ -v
```

### Step 5: Verify line count

```bash
wc -l acqmss/eval/cross_validation.py
# Target: ~250 lines (down from 470)
```

## Todo List

- [ ] Run `ruff check` on modified file
- [ ] Run `ruff format --check` on modified file
- [ ] Verify imports work
- [ ] Run `tests/test_evaluation.py`
- [ ] Run full test suite
- [ ] Confirm file is under 270 lines

## Success Criteria

- All tests pass (same results as before refactor)
- Zero ruff errors/warnings
- File under 270 lines
- Import check passes

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hidden test failure | Medium | Run full suite, not just eval tests |
| Import cycle from lazy import | Low | Lazy import pattern already used in current code |

## Next Steps

- Refactor complete. Update docs if needed (likely not — internal refactor only).
