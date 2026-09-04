# Phase 2: Merge CONGEN Strategies

## Context

- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-merge-explanation-strategies.md)

## Overview

- **Date**: 2026-02-13
- **Priority**: P1
- **Description**: Merge IncrementalCONGENTaskPreparation + NonIncrementalCONGENTaskPreparation → CONGENTaskPreparation
- **Implementation status**: complete
- **Review status**: complete

## Key Insights

1. Both CONGEN preparation classes are 100% identical except `mode_name` and debug log message
2. Both produce `CONGENTask` with identical data
3. They inherit `TestCaseTaskPreparationStrategy` — after Phase 1 this ABC still exists
4. `_prepare_bias_constraints()` and `_prepare_examples()` are copy-pasted between the two classes

## Requirements

- Merge into single `CONGENTaskPreparation` class
- Parameterize `mode_name` via constructor
- Maintain same interface (`TestCaseTaskPreparationStrategy` subclass)

## Architecture

### Before
```
TestCaseTaskPreparationStrategy(ABC)
├── IncrementalCONGENTaskPreparation    (190 lines)
└── NonIncrementalCONGENTaskPreparation (143 lines, copy-paste)
```

### After
```
TestCaseTaskPreparationStrategy(ABC)
└── CONGENTaskPreparation               (~190 lines, single impl)
```

## Related Code Files

| File | Action |
|------|--------|
| `acqmss/algorithms/task_preparation.py` | Merge 2 classes → 1 |

## Implementation Steps

### Step 1: Merge

1. Rename `IncrementalCONGENTaskPreparation` → `CONGENTaskPreparation`
2. Add `__init__(self, mode_name: str = "congen")`
3. Change `mode_name` property to return `self._mode_name`
4. Update debug log to use `self._mode_name`
5. Delete `NonIncrementalCONGENTaskPreparation` entirely

### Step 2: Update imports in same file

- Remove any imports only needed by deleted class (none expected)

### Step 3: Verify

- `PYTHONPATH=. python -c "from acqmss.algorithms.task_preparation import CONGENTaskPreparation"`

## Todo List

- [x] Rename IncrementalCONGENTaskPreparation → CONGENTaskPreparation
- [x] Add mode_name constructor parameter
- [x] Update debug log messages
- [x] Delete NonIncrementalCONGENTaskPreparation
- [x] Verify import works

## Success Criteria

- `acqmss/algorithms/task_preparation.py` reduced from ~357 to ~200 lines
- 2 classes → 1
- Import and compile passes

## Risk Assessment

- **Low**: Straightforward rename+delete, same pattern as Phase 1

## Security Considerations

None.

## Next Steps

→ Phase 3: Update all references, tests, exports, docs
