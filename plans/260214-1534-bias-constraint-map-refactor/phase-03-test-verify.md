# Phase 3: Test & Verify

**Parent plan**: [plan.md](./plan.md)

## Overview

- **Priority**: P3
- **Status**: completed
- **Description**: Run existing tests to verify no regression, lint check

## Implementation Steps

1. Run `ruff check acqmss/bias/data_structures.py` — verify no lint errors
2. Run `ruff check acqmss/algorithms/congen_model_builder.py acqmss/algorithms/interactive/learner.py`
3. Run `PYTHONPATH=. pytest tests/test_interactive.py -v` — interactive tests
4. Run `PYTHONPATH=. pytest tests/test_congen.py -v` — ConGen tests (uses ConGenModelBuilder)
5. Verify no unused imports remain

## Todo

- [ ] Lint check passes
- [ ] `test_interactive.py` all pass
- [ ] `test_congen.py` all pass
- [ ] No unused imports

## Success Criteria

- All tests pass unchanged (pure refactoring — no behavior change)
- No new lint warnings
