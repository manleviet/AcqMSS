# Phase 2: Remove TestCase Task Subclasses

## Context Links

- [plan.md](plan.md) -- overview
- [explanation/models/task_preparation.py](/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/task_preparation.py) -- defines `IncrementalTestCaseTask`, `NonIncrementalTestCaseTask` and preparation strategies
- [acqmss/algorithms/task.py](/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task.py) -- imports for MRO

## Overview

- **Priority**: P2
- **Status**: complete
- **Description**: Remove `IncrementalTestCaseTask` and `NonIncrementalTestCaseTask`. Both add only `assumptions: List = field(default_factory=list)` to `TestCaseTask`. Move `assumptions` up to `TestCaseTask`.

## Key Insights

1. Both subclasses are structurally identical -- each adds only `assumptions: List`
2. `TestCaseTask` already inherits from `DiagnosisTask` which will also gain `assumptions` in Phase 3
3. The `IncrementalTaskType` type alias (line 163-166) references all four subclasses and will need updating
4. `IncrementalKBPreparator.prepare_kb()` uses `IncrementalTaskType` for its `result` parameter type hint
5. Preparation strategies (`IncrementalTestCaseTaskPreparation`, `NonIncrementalTestCaseTaskPreparation`) instantiate these classes -- they must switch to `TestCaseTask()`

## Requirements

### Functional
- `assumptions` field available on `TestCaseTask` directly
- All preparation strategies produce `TestCaseTask` instances
- `IncrementalTaskType` simplified or removed

### Non-functional
- No behavioral change

## Architecture

Before:
```
DiagnosisTask
  └── TestCaseTask
        ├── IncrementalTestCaseTask (assumptions)    <-- REMOVE
        └── NonIncrementalTestCaseTask (assumptions)  <-- REMOVE
```

After:
```
DiagnosisTask
  └── TestCaseTask (assumptions moved here)
```

## Related Code Files

### Files to Modify

| File | Change |
|------|--------|
| `explanation/models/task_preparation.py` | (1) Add `assumptions: List = field(default_factory=list)` to `TestCaseTask`; (2) Delete `IncrementalTestCaseTask` and `NonIncrementalTestCaseTask` classes; (3) Update `IncrementalTaskType` alias; (4) Update type hints in preparation strategies; (5) Change instantiation in `IncrementalTestCaseTaskPreparation.prepare()` and `NonIncrementalTestCaseTaskPreparation.prepare()` to use `TestCaseTask()` |
| `explanation/models/__init__.py` | Remove `IncrementalTestCaseTask`, `NonIncrementalTestCaseTask` from imports and `__all__` |

### Downstream Impact

| File | Impact |
|------|--------|
| `acqmss/algorithms/task.py` | If Phase 1 not done yet: `IncrementalCONGENTask` and `NonIncrementalCONGENTask` inherit from these -- their imports will break. **Must update** to inherit from `TestCaseTask` or `CONGENTask` only. |
| `explanation/models/pysat_diagnosis_model.py` | Imports `IncrementalTestCaseTask` (line 13) -- must remove |

## Implementation Steps

1. In `explanation/models/task_preparation.py`:
   a. Add `assumptions: List = field(default_factory=list)` to `TestCaseTask` class (after `neg_tc_map`)
   b. Delete `IncrementalTestCaseTask` class (lines 143-150)
   c. Delete `NonIncrementalTestCaseTask` class (lines 153-159)
   d. Simplify `IncrementalTaskType` -- either remove it or redefine as `Union[DiagnosisTask, TestCaseTask]` (or simply use `DiagnosisTask` since `TestCaseTask` is a subclass). Since `IncrementalKBPreparator.prepare_kb()` just needs `.set_kb`, `.assumptions`, `.neg_c_map`, it can use `DiagnosisTask` once `assumptions` is on `DiagnosisTask` (Phase 3). **For now**: change to `Union[DiagnosisTask, TestCaseTask]` or keep temporarily.
   e. Update `IncrementalTestCaseTaskPreparation.prepare()` (line 609): `result = IncrementalTestCaseTask()` -> `result = TestCaseTask()`
   f. Update `NonIncrementalTestCaseTaskPreparation.prepare()` (line 754): `result = NonIncrementalTestCaseTask()` -> `result = TestCaseTask()`
   g. Update type hints in `_prepare_testsuite_with_negation` and `_assign_sets` methods to use `TestCaseTask`
   h. Update `IncrementalKBPreparator.prepare_configuration()` type hint (line 351): `IncrementalDiagnosisTask` -> `DiagnosisTask` (deferred to Phase 3 if needed)

2. In `explanation/models/__init__.py`:
   - Remove `IncrementalTestCaseTask` and `NonIncrementalTestCaseTask` from import and `__all__`

3. In `explanation/models/pysat_diagnosis_model.py`:
   - Remove `IncrementalTestCaseTask` from import (line 13)

4. If Phase 1 NOT yet done: In `acqmss/algorithms/task.py`:
   - Remove imports of `IncrementalTestCaseTask`, `NonIncrementalTestCaseTask`
   - Change `IncrementalCONGENTask(CONGENTask, IncrementalTestCaseTask)` to `IncrementalCONGENTask(CONGENTask)`
   - Change `NonIncrementalCONGENTask(CONGENTask, NonIncrementalTestCaseTask)` to `NonIncrementalCONGENTask(CONGENTask)`
   - `CONGENTask(TestCaseTask)` already inherits from `TestCaseTask` which now has `assumptions`

## Todo List

- [ ] Add `assumptions: List = field(default_factory=list)` to `TestCaseTask`
- [ ] Delete `IncrementalTestCaseTask` class
- [ ] Delete `NonIncrementalTestCaseTask` class
- [ ] Update `IncrementalTaskType` alias
- [ ] Update preparation strategies to instantiate `TestCaseTask()`
- [ ] Update type hints throughout task_preparation.py
- [ ] Update `__init__.py` exports
- [ ] Update `pysat_diagnosis_model.py` imports
- [ ] If Phase 1 not done: update `acqmss/algorithms/task.py` inheritance
- [ ] Run tests: `PYTHONPATH=. pytest tests/test_diagnosis.py -v`

## Success Criteria

- `PYTHONPATH=. pytest tests/test_diagnosis.py -v` passes
- `PYTHONPATH=. pytest tests/ -v` passes
- No `IncrementalTestCaseTask` or `NonIncrementalTestCaseTask` references in code (excluding plans/)
- `grep -r "IncrementalTestCaseTask\|NonIncrementalTestCaseTask" acqmss/ explanation/ tests/ apps/` returns nothing

## Risk Assessment

- **Medium**: `IncrementalTaskType` is used by `IncrementalKBPreparator.prepare_kb()` -- type hint update needed but no runtime impact
- **Medium**: If Phase 1 not done, CONGEN task MRO changes -- but `CONGENTask` inherits `TestCaseTask` directly so `assumptions` is still accessible
- **Low**: `prepare_configuration` type hint references `IncrementalDiagnosisTask` -- can defer to Phase 3

## Security Considerations

None -- pure refactoring.

## Next Steps

- Phase 3: Remove `IncrementalDiagnosisTask` and `NonIncrementalDiagnosisTask`
