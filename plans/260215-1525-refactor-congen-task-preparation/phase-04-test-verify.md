# Phase 4: Run Full Tests & Verify

## Context

- Parent plan: [plan.md](plan.md)
- Depends on: Phase 1 + Phase 2 + Phase 3 complete

## Overview

- **Priority**: High
- **Status**: pending
- **Description**: Verify refactoring preserves exact behavior via existing + new test suite

## Implementation Steps

1. **Run full test suite**
   - `PYTHONPATH=. pytest tests/test_congen.py tests/test_diagnosis.py -v`
   - All existing + new tests must pass

2. **Run type check**
   - `PYTHONPATH=. python -m mypy acqmss/algorithms/task_preparation.py`
   - `PYTHONPATH=. python -m mypy acqmss/algorithms/congen_model.py`

3. **Run linter**
   - `ruff check acqmss/algorithms/task_preparation.py acqmss/algorithms/congen_model.py`

4. **Verify file size**
   - `task_preparation.py` should be ≤ 300 lines
   - `prepare()` method body ≤ 50 lines

## Todo

- [ ] All tests pass
- [ ] Type check passes
- [ ] Linter passes
- [ ] File size within target

## Success Criteria

- Zero test failures
- Zero type errors
- Zero lint errors
- Code is cleaner and more maintainable
