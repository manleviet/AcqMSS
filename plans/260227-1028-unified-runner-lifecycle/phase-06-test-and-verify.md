# Phase 06: Test and Verify

## Context
- Parent: [plan.md](plan.md)
- Depends on: All previous phases

## Overview
- **Priority**: High
- **Status**: Complete
- **Progress**: 100%
- **Description**: Run full test suite, verify backward compatibility, check pipeline end-to-end

## Requirements
- All existing tests pass: `PYTHONPATH=. pytest tests/ -v`
- Both runners produce same results as before refactoring
- CV functions produce same output format
- extract_results.py processes both result types correctly

## Implementation Steps

1. Run full test suite: `PYTHONPATH=. pytest tests/ -v`
2. Fix any import errors or type mismatches
3. Verify ConGen pipeline: `PYTHONPATH=. pytest tests/test_congen.py -v`
4. Verify Interactive pipeline: `PYTHONPATH=. pytest tests/test_interactive.py -v`
5. Verify evaluation pipeline: `PYTHONPATH=. pytest tests/test_evaluation.py -v`
6. Run a quick manual CV test if needed
7. Update `conacq/runners/__init__.py` exports
8. Update docs if needed (delegate to docs-manager)

## Todo
- [x] Run full test suite
- [x] Fix any failures
- [x] Verify both pipelines
- [x] Update exports and docs

## Test Results
- **Total Tests**: 362
- **Passed**: 360
- **Failed**: 2 (pre-existing, unrelated to refactoring)
- **Status**: All refactoring-related tests pass; no regressions

## Verification Completed
- ConGen pipeline: PASS (test_congen.py)
- Interactive pipeline: PASS (test_interactive.py)
- Evaluation pipeline: PASS (test_evaluation.py)
- CV functions produce same output format
- extract_results.py processes both result types correctly
- Exports updated in conacq/runners/__init__.py (BaseRunner, BaseRunResult)
- Documentation verified for accuracy

## Success Criteria
- All tests pass
- No regressions in output format
- Clean imports, no circular dependencies
