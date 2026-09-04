# Phase 5: Cleanup Exports and Docs

## Context Links

- [plan.md](plan.md) -- overview
- [explanation/models/__init__.py](/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/__init__.py) -- explanation model exports
- [acqmss/algorithms/__init__.py](/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/__init__.py) -- algorithm exports
- [docs/codebase-summary.md](/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md) -- codebase documentation
- [docs/system-architecture.md](/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md) -- architecture documentation
- [docs/code-standards.md](/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md) -- code standards

## Overview

- **Priority**: P3
- **Status**: complete
- **Description**: Remove all remaining references to deleted classes from `__init__.py` exports, docstrings, and project documentation. Final sweep to ensure clean codebase.

## Key Insights

1. `__init__.py` exports already handled in phases 1-3. This phase is a verification pass.
2. Documentation files reference the old class hierarchy and need updating.
3. Module-level docstring in `task_preparation.py` lists the old hierarchy.

## Requirements

### Functional
- No stale references to removed classes anywhere in codebase
- Documentation accurately reflects simplified hierarchy

### Non-functional
- Clean `grep` results for all 6 class names

## Related Code Files

### Files to Verify/Update

| File | Change |
|------|--------|
| `explanation/models/__init__.py` | Verify cleaned (Phase 3) |
| `acqmss/algorithms/__init__.py` | Verify cleaned (Phase 1) |
| `explanation/models/task_preparation.py` | Update module docstring (lines 1-12) to reflect simplified hierarchy |
| `docs/codebase-summary.md` | Update task hierarchy description, LOC counts |
| `docs/system-architecture.md` | Update `CONGENTask` class documentation, remove references to Incremental/NonIncremental task variants |
| `docs/code-standards.md` | No changes expected (examples use builders, not task subclasses) |

## Implementation Steps

1. **Final codebase sweep** -- verify no stale references:
   ```bash
   grep -rn "IncrementalDiagnosisTask\|NonIncrementalDiagnosisTask" acqmss/ explanation/ tests/ apps/ docs/
   grep -rn "IncrementalTestCaseTask\|NonIncrementalTestCaseTask" acqmss/ explanation/ tests/ apps/ docs/
   grep -rn "IncrementalCONGENTask\|NonIncrementalCONGENTask" acqmss/ explanation/ tests/ apps/ docs/
   ```

2. **Update module docstring** in `explanation/models/task_preparation.py`:
   - Old (lines 6-12):
     ```
     Strategy hierarchy:
     - DiagnosisTaskPreparationStrategy: For diagnosis/conflict operations
       - IncrementalDiagnosisTaskPreparation
       - NonIncrementalDiagnosisTaskPreparation
     - TestCaseTaskPreparationStrategy: For operations with test cases
       - IncrementalTestCaseTaskPreparation
       - NonIncrementalTestCaseTaskPreparation
     ```
   - Keep as-is since preparation **strategies** are NOT removed, only task **dataclasses**

3. **Update `docs/codebase-summary.md`**:
   - Line 22: Update `task.py` description to mention simplified hierarchy
   - Remove references to `IncrementalCONGENTask`, `NonIncrementalCONGENTask`

4. **Update `docs/system-architecture.md`**:
   - Lines 198-212: Update `CONGENTask` class documentation
   - Remove `IncrementalTaskType` references if any
   - Update "Task classes for both incremental and non-incremental modes" wording

5. **Verify `__init__.py` files** are clean:
   - `explanation/models/__init__.py` -- no removed class names
   - `acqmss/algorithms/__init__.py` -- no removed class names

## Todo List

- [ ] Run final grep sweep for all 6 removed class names
- [ ] Update module docstring in `task_preparation.py` (if needed)
- [ ] Update `docs/codebase-summary.md`
- [ ] Update `docs/system-architecture.md`
- [ ] Verify `__init__.py` exports are clean
- [ ] Run full test suite one final time: `PYTHONPATH=. pytest tests/ -v`

## Success Criteria

- `grep -rn "IncrementalDiagnosisTask\|NonIncrementalDiagnosisTask\|IncrementalTestCaseTask\|NonIncrementalTestCaseTask\|IncrementalCONGENTask\|NonIncrementalCONGENTask" acqmss/ explanation/ tests/ apps/` returns zero results
- Documentation reflects simplified hierarchy
- Full test suite passes

## Risk Assessment

- **Very Low**: Documentation-only changes, no runtime impact

## Security Considerations

None.

## Next Steps

- Refactoring complete
- Future opportunity: merge duplicated preparation strategy methods (incremental and non-incremental `_prepare_configuration`, `_assign_sets`, `_prepare_testsuite_with_negation` are now identical in logic)
