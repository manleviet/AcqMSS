# Phase 1: Merge Explanation Strategies + Integrate KBPreparator

## Context

- Parent: [plan.md](plan.md)
- Docs: [codebase-summary](../../docs/codebase-summary.md), [system-architecture](../../docs/system-architecture.md)

## Overview

- **Date**: 2026-02-13
- **Priority**: P1
- **Description**: Merge 4 strategy classes into 2, integrate IncrementalKBPreparator as base class
- **Implementation status**: complete
- **Review status**: complete

## Key Insights

1. `IncrementalDiagnosisTaskPreparation` and `NonIncrementalDiagnosisTaskPreparation` are 100% identical except `mode_name`
2. `NonIncrementalDiagnosisTaskPreparation._prepare_configuration()` duplicates `IncrementalKBPreparator.prepare_configuration()`
3. `IncrementalTestCaseTaskPreparation` and `NonIncrementalTestCaseTaskPreparation` are 100% identical except `mode_name`
4. Both merged classes will use `IncrementalKBPreparator.prepare_kb()` — better to make it a base class
5. Strategy ABC interfaces (`DiagnosisTaskPreparationStrategy`, `TestCaseTaskPreparationStrategy`) can remain as-is or be simplified

## Requirements

- Merge each pair into single class parameterized by `mode_name`
- Eliminate `IncrementalKBPreparator` as standalone utility → integrate into base class
- Maintain backward compatibility: `TaskPreparationFactory` still works
- All tests pass without changes to test logic

## Architecture

### Before (current)
```
DiagnosisTaskPreparationStrategy(ABC)
├── IncrementalDiagnosisTaskPreparation
└── NonIncrementalDiagnosisTaskPreparation  (copy-paste of above)

TestCaseTaskPreparationStrategy(ABC)
├── IncrementalTestCaseTaskPreparation
└── NonIncrementalTestCaseTaskPreparation   (copy-paste of above)

IncrementalKBPreparator                     (standalone utility)
```

### After (target)
```
DiagnosisTaskPreparationStrategy(ABC)       # keep as interface
└── DiagnosisTaskPreparation                # single impl, mode_name via __init__

TestCaseTaskPreparationStrategy(ABC)        # keep as interface
└── TestCaseTaskPreparation                 # single impl, mode_name via __init__

IncrementalKBPreparator                     # REMOVED (methods moved to preparation classes)
```

**Note on base class extraction**: After merging, check if `DiagnosisTaskPreparation` and `TestCaseTaskPreparation` share enough logic to warrant a base. They both use `prepare_kb()` and `prepare_configuration()` — if these are the only shared methods, keep them as static utility methods on one of the classes or as module-level functions. Only extract a base class if there's substantial shared logic (3+ methods).

## Related Code Files

| File | Action |
|------|--------|
| `explanation/models/task_preparation.py` | Merge 4 classes → 2, remove IncrementalKBPreparator |

## Implementation Steps

### Step 1: Merge DiagnosisTaskPreparation

1. Rename `IncrementalDiagnosisTaskPreparation` → `DiagnosisTaskPreparation`
2. Add `__init__(self, mode_name: str = "incremental")` to store mode_name
3. Change `mode_name` property to return `self._mode_name`
4. In `prepare()`: replace `IncrementalKBPreparator.prepare_kb()` call with direct method (move prepare_kb as instance method or keep as static)
5. Replace `IncrementalKBPreparator.prepare_configuration()` calls with direct method
6. Delete `NonIncrementalDiagnosisTaskPreparation` entirely

### Step 2: Merge TestCaseTaskPreparation

1. Rename `IncrementalTestCaseTaskPreparation` → `TestCaseTaskPreparation`
2. Add `__init__(self, mode_name: str = "incremental-testcase")`
3. Change `mode_name` property to return `self._mode_name`
4. Replace `IncrementalKBPreparator.prepare_kb()` call with direct method
5. Delete `NonIncrementalTestCaseTaskPreparation` entirely

### Step 3: Handle shared KB preparation logic

After merging, both `DiagnosisTaskPreparation` and `TestCaseTaskPreparation` need `prepare_kb()`.

**Decision tree:**
- If only `prepare_kb()` is shared → keep as module-level function or static method on one class
- If `prepare_kb()` + `prepare_configuration()` shared → consider a mixin or base
- If 3+ methods shared → extract proper base class

Current analysis: `prepare_kb()` used by both; `prepare_configuration()` only by Diagnosis. So keep `prepare_kb()` as module-level function. Delete `IncrementalKBPreparator` class.

### Step 4: Update TaskPreparationFactory

```python
class TaskPreparationFactory:
    _diagnosis: DiagnosisTaskPreparation = None
    _testcase: TestCaseTaskPreparation = None

    @classmethod
    def create_diagnosis(cls, is_incremental: bool) -> DiagnosisTaskPreparationStrategy:
        mode = "incremental" if is_incremental else "non-incremental"
        # Can cache single instance since mode_name is only used for logging
        if cls._diagnosis is None:
            cls._diagnosis = DiagnosisTaskPreparation(mode)
        return cls._diagnosis

    @classmethod
    def create_testcase(cls, is_incremental: bool = True) -> TestCaseTaskPreparationStrategy:
        mode = "incremental-testcase" if is_incremental else "non-incremental-testcase"
        if cls._testcase is None:
            cls._testcase = TestCaseTaskPreparation(mode)
        return cls._testcase
```

**Wait** — caching won't work if mode_name changes between calls. Two options:
- (A) Cache per mode: `_diagnosis_inc` and `_diagnosis_noninc` — but then we have 2 instances of same class
- (B) Don't cache, just create new instance each time (cheap)
- (C) Since mode_name is only for logging and both produce identical output, cache one instance with generic name

**Recommendation: Option C** — use single cached instance with mode_name="diagnosis" / "testcase". The incremental/non-incremental distinction is meaningless at the preparation level.

### Step 5: Update module docstring

Update the docstring at top of file to reflect new structure.

## Todo List

- [x] Rename IncrementalDiagnosisTaskPreparation → DiagnosisTaskPreparation
- [x] Add mode_name constructor parameter
- [x] Move prepare_kb() to module-level function
- [x] Move prepare_configuration() into DiagnosisTaskPreparation as instance method
- [x] Delete NonIncrementalDiagnosisTaskPreparation
- [x] Delete IncrementalKBPreparator class
- [x] Rename IncrementalTestCaseTaskPreparation → TestCaseTaskPreparation
- [x] Add mode_name constructor parameter
- [x] Delete NonIncrementalTestCaseTaskPreparation
- [x] Update TaskPreparationFactory
- [x] Update module docstring
- [x] Verify file compiles: `python -c "import explanation.models.task_preparation"`

## Success Criteria

- `explanation/models/task_preparation.py` reduced from ~895 to ~500 lines
- 4 strategy classes → 2
- IncrementalKBPreparator eliminated
- `PYTHONPATH=. python -c "import explanation.models.task_preparation"` passes
- All existing tests pass unchanged

## Risk Assessment

- **Low**: Renaming classes that are NOT exported from `__init__.py` — only used internally via Factory
- **Low**: prepare_kb logic is identical in all usages

## Security Considerations

None — pure refactoring, no behavioral changes.

## Next Steps

→ Phase 2: Merge CONGEN strategies (depends on this phase for pattern)
