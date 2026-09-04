# Phase 4: Update Tests

## Context Links

- [plan.md](plan.md) -- overview
- [tests/test_diagnosis.py](/Users/manleviet/Development/GitHub/AcqMSS/tests/test_diagnosis.py) -- diagnosis algorithm tests
- [tests/test_congen.py](/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py) -- CONGEN tests

## Overview

- **Priority**: P2
- **Status**: complete
- **Description**: Update test files to remove references to deleted subclasses and verify all tests pass after phases 1-3.

## Key Insights

1. `test_congen.py` imports `IncrementalCONGENTaskPreparation` and `NonIncrementalCONGENTaskPreparation` -- these preparation **strategies** are NOT being removed (only the task dataclasses). No change needed for these imports.
2. `test_diagnosis.py` does NOT directly import any of the 6 removed classes. It uses `DiagnosisModelBuilder` and `PySATDiagnosisBuilder` which abstract away task creation.
3. No `isinstance` checks against the removed classes exist in test code.
4. The tests should pass without modification after phases 1-3, since they interact with tasks through the preparation strategies and builder pattern, not by direct instantiation.

## Requirements

### Functional
- All existing tests pass without modification (validation phase)
- No references to removed classes remain in test files

### Non-functional
- Test coverage unchanged

## Related Code Files

### Files to Verify (likely no changes needed)

| File | Notes |
|------|-------|
| `tests/test_congen.py` | Uses `IncrementalCONGENTaskPreparation` / `NonIncrementalCONGENTaskPreparation` (NOT removed). No direct refs to `IncrementalCONGENTask` or `NonIncrementalCONGENTask`. |
| `tests/test_diagnosis.py` | Uses builder pattern; no direct refs to removed classes |
| `tests/test_interactive.py` | Uses `InteractiveLearner`; unrelated to removed classes |
| `tests/test_evaluation.py` | Uses `CONGENRunner`; indirectly affected but no direct refs |

## Implementation Steps

1. Search all test files for references to removed classes:
   ```bash
   grep -rn "IncrementalDiagnosisTask\|NonIncrementalDiagnosisTask\|IncrementalTestCaseTask\|NonIncrementalTestCaseTask\|IncrementalCONGENTask\|NonIncrementalCONGENTask" tests/
   ```
2. If any references found, update imports and usage to use base classes
3. Run full test suite:
   ```bash
   PYTHONPATH=. pytest tests/ -v
   ```
4. Verify both incremental and non-incremental modes pass:
   ```bash
   PYTHONPATH=. pytest tests/test_diagnosis.py -v
   PYTHONPATH=. pytest tests/test_congen.py -v
   ```

## Todo List

- [ ] Verify no test files reference removed classes
- [ ] Run `PYTHONPATH=. pytest tests/test_diagnosis.py -v` -- passes
- [ ] Run `PYTHONPATH=. pytest tests/test_congen.py -v` -- passes
- [ ] Run `PYTHONPATH=. pytest tests/ -v` -- full suite passes
- [ ] Update any test imports if needed (likely none)

## Success Criteria

- Full test suite passes: `PYTHONPATH=. pytest tests/ -v`
- Zero references to removed classes in `tests/` directory
- Both incremental and non-incremental parameterized tests pass

## Risk Assessment

- **Very Low**: Tests don't directly reference the removed classes. They use preparation strategies and builders.
- **Low**: Parameterized tests with `('incremental', ...), ('non_incremental', ...)` patterns work through checker classes, not task subclasses.

## Security Considerations

None.

## Next Steps

- Phase 5: Cleanup exports and docs
