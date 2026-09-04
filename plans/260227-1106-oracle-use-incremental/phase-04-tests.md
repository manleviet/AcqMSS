# Phase 4: Tests

## Context
- Parent: [plan.md](plan.md)
- Depends on: Phase 1, 2, 3

## Overview
- Priority: P1
- Status: complete
- Verify both incremental/non-incremental modes work for both runners

## Related Code Files
- `tests/test_interactive.py` — existing test file for interactive tests

## Implementation Steps

1. Run existing test suite to verify no regressions:
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```

2. Verify InteractiveRunner accepts and passes `use_incremental`:
   - Check that `InteractiveRunner(use_incremental=True)` creates oracle with incremental checker
   - Check that `InteractiveRunner(use_incremental=False)` creates oracle with non-incremental checker

3. Verify ConGenRunner's oracle now respects `use_incremental`:
   - ConGenRunner already had param — now oracle should match

## Todo
- [x] Run full test suite — no regressions
- [x] Verify Oracle checker type matches use_incremental setting

## Success Criteria
- All existing tests pass
- Oracle uses configured use_incremental in both runners
