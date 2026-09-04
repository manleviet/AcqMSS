# Phase 3: Remove Diagnosis Task Subclasses

## Context Links

- [plan.md](plan.md) -- overview
- [explanation/models/task_preparation.py](/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/task_preparation.py) -- defines `IncrementalDiagnosisTask`, `NonIncrementalDiagnosisTask`
- [explanation/models/pysat_diagnosis_model.py](/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/pysat_diagnosis_model.py) -- imports `IncrementalDiagnosisTask`

## Overview

- **Priority**: P2
- **Status**: complete
- **Description**: Remove `IncrementalDiagnosisTask` and `NonIncrementalDiagnosisTask`. Both add only `assumptions: List`. Move `assumptions` to `DiagnosisTask`. Also remove `DiagnosisTask`'s `ABC` base since it has no abstract methods.

## Key Insights

1. Both subclasses add identical field: `assumptions: List = field(default_factory=list)`
2. `DiagnosisTask` currently inherits from `ABC` but has NO abstract methods -- `ABC` can be dropped
3. After this phase, `TestCaseTask` already has `assumptions` from Phase 2, but `DiagnosisTask` also needs it
4. **Important**: If `assumptions` is added to both `DiagnosisTask` and `TestCaseTask`, there's a duplicate. Since `TestCaseTask` inherits `DiagnosisTask`, adding `assumptions` to `DiagnosisTask` alone is sufficient. Phase 2 should add it to `TestCaseTask` only if Phase 3 hasn't been done.

**Recommended execution order**: Phase 3 first (add to `DiagnosisTask`), then Phase 2 (no need to add to `TestCaseTask` since inherited), then Phase 1 (trivial deletion).

## Requirements

### Functional
- `assumptions` field available on `DiagnosisTask` base class
- `IncrementalDiagnosisTaskPreparation.prepare()` returns `DiagnosisTask` (not subclass)
- `NonIncrementalDiagnosisTaskPreparation.prepare()` returns `DiagnosisTask` (not subclass)
- `IncrementalKBPreparator` type hints updated
- `IncrementalTaskType` alias removed or simplified to just `DiagnosisTask`

### Non-functional
- No behavioral change

## Architecture

Before:
```
DiagnosisTask (ABC, no abstract methods)
  ├── IncrementalDiagnosisTask (assumptions)      <-- REMOVE
  ├── NonIncrementalDiagnosisTask (assumptions)    <-- REMOVE
  └── TestCaseTask
```

After:
```
DiagnosisTask (assumptions, no ABC)
  └── TestCaseTask (inherits assumptions)
```

## Related Code Files

### Files to Modify

| File | Change |
|------|--------|
| `explanation/models/task_preparation.py` | (1) Remove `ABC` from `DiagnosisTask`; (2) Add `assumptions: List = field(default_factory=list)` to `DiagnosisTask`; (3) Delete `IncrementalDiagnosisTask` and `NonIncrementalDiagnosisTask`; (4) Remove/simplify `IncrementalTaskType`; (5) Update `IncrementalKBPreparator` type hints; (6) Update preparation strategies to instantiate `DiagnosisTask()` |
| `explanation/models/__init__.py` | Remove `IncrementalDiagnosisTask`, `NonIncrementalDiagnosisTask` from imports and `__all__` |
| `explanation/models/pysat_diagnosis_model.py` | Remove `IncrementalDiagnosisTask` import (line 11); update docstring (line 263) |

### All references to update

| Location | Current | New |
|----------|---------|-----|
| task_preparation.py:103-109 | `IncrementalDiagnosisTask` class | DELETE |
| task_preparation.py:113-118 | `NonIncrementalDiagnosisTask` class | DELETE |
| task_preparation.py:163-166 | `IncrementalTaskType` alias | Remove or change to `DiagnosisTask` |
| task_preparation.py:300 | `prepare_kb(result: IncrementalTaskType, ...)` | `prepare_kb(result: DiagnosisTask, ...)` |
| task_preparation.py:351 | `prepare_configuration(result: IncrementalDiagnosisTask, ...)` | `prepare_configuration(result: DiagnosisTask, ...)` |
| task_preparation.py:414 | `result = IncrementalDiagnosisTask()` | `result = DiagnosisTask()` |
| task_preparation.py:445 | `_assign_sets(self, result: IncrementalDiagnosisTask, ...)` | `_assign_sets(self, result: DiagnosisTask, ...)` |
| task_preparation.py:501 | `result = NonIncrementalDiagnosisTask()` | `result = DiagnosisTask()` |
| task_preparation.py:529 | `_prepare_configuration(self, result: NonIncrementalDiagnosisTask, ...)` | `_prepare_configuration(self, result: DiagnosisTask, ...)` |
| task_preparation.py:553 | `_assign_sets(self, result: NonIncrementalDiagnosisTask, ...)` | `_assign_sets(self, result: DiagnosisTask, ...)` |
| pysat_diagnosis_model.py:11 | `IncrementalDiagnosisTask,` import | Remove |
| pysat_diagnosis_model.py:263 | Docstring mentioning subclasses | Update text |

## Implementation Steps

1. In `explanation/models/task_preparation.py`:
   a. Remove `ABC` import and `ABC` base from `DiagnosisTask` -- the class has no abstract methods, so `ABC` is unnecessary
   b. Add `assumptions: List = field(default_factory=list)` to `DiagnosisTask` (after `neg_c_map`)
   c. Delete `IncrementalDiagnosisTask` class (lines 102-109)
   d. Delete `NonIncrementalDiagnosisTask` class (lines 112-118)
   e. Remove or simplify `IncrementalTaskType` -- replace with `DiagnosisTask` since all tasks now have `assumptions`
   f. Update `IncrementalKBPreparator.prepare_kb()` type hint: `result: IncrementalTaskType` -> `result: DiagnosisTask`
   g. Update `IncrementalKBPreparator.prepare_configuration()` type hint: `result: IncrementalDiagnosisTask` -> `result: DiagnosisTask`
   h. Update `IncrementalDiagnosisTaskPreparation.prepare()`: `result = IncrementalDiagnosisTask()` -> `result = DiagnosisTask()`
   i. Update `IncrementalDiagnosisTaskPreparation._assign_sets()` type hint
   j. Update `NonIncrementalDiagnosisTaskPreparation.prepare()`: `result = NonIncrementalDiagnosisTask()` -> `result = DiagnosisTask()`
   k. Update `NonIncrementalDiagnosisTaskPreparation._prepare_configuration()` type hint
   l. Update `NonIncrementalDiagnosisTaskPreparation._assign_sets()` type hint

2. In `explanation/models/__init__.py`:
   - Remove `IncrementalDiagnosisTask` and `NonIncrementalDiagnosisTask` from import and `__all__`

3. In `explanation/models/pysat_diagnosis_model.py`:
   - Remove `IncrementalDiagnosisTask` from import (line 11)
   - Update docstring at line 263 to remove subclass references

## Todo List

- [ ] Remove `ABC` from `DiagnosisTask` base
- [ ] Add `assumptions` field to `DiagnosisTask`
- [ ] Delete `IncrementalDiagnosisTask` class
- [ ] Delete `NonIncrementalDiagnosisTask` class
- [ ] Remove `IncrementalTaskType` alias
- [ ] Update `IncrementalKBPreparator` type hints
- [ ] Update preparation strategy instantiation and type hints
- [ ] Update `__init__.py` exports
- [ ] Update `pysat_diagnosis_model.py` imports and docstring
- [ ] Run tests: `PYTHONPATH=. pytest tests/test_diagnosis.py -v`

## Success Criteria

- `PYTHONPATH=. pytest tests/test_diagnosis.py -v` passes
- `PYTHONPATH=. pytest tests/ -v` passes
- No `IncrementalDiagnosisTask` or `NonIncrementalDiagnosisTask` references in code
- `grep -r "IncrementalDiagnosisTask\|NonIncrementalDiagnosisTask" acqmss/ explanation/ tests/ apps/` returns nothing

## Risk Assessment

- **Low**: Removing `ABC` -- `DiagnosisTask` has no abstract methods, so `ABC` is decorative only
- **Low**: `hasattr(self._task, 'assumptions')` check in `pysat_diagnosis_model.py` line 137 -- will still work since `assumptions` is now always present on `DiagnosisTask`
- **Medium**: `_prepare_configuration` is duplicated between `IncrementalDiagnosisTaskPreparation` and `NonIncrementalDiagnosisTaskPreparation` -- this is a DRY issue but out of scope for this refactor

## Security Considerations

None -- pure refactoring.

## Next Steps

- Phase 4: Update tests
- Future refactoring opportunity: merge duplicated `_prepare_configuration` and `_assign_sets` methods between incremental and non-incremental preparation strategies (they're now identical)
