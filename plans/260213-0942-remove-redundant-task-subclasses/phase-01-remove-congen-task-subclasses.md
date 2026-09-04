# Phase 1: Remove CONGEN Task Subclasses

## Context Links

- [plan.md](plan.md) -- overview
- [acqmss/algorithms/task.py](/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task.py) -- defines `IncrementalCONGENTask`, `NonIncrementalCONGENTask`
- [acqmss/algorithms/task_preparation.py](/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task_preparation.py) -- instantiates them
- [acqmss/algorithms/__init__.py](/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/__init__.py) -- exports them

## Overview

- **Priority**: P2
- **Status**: complete
- **Description**: Remove `IncrementalCONGENTask` and `NonIncrementalCONGENTask`. These classes add no unique logic. `IncrementalCONGENTask` body is `pass`. `NonIncrementalCONGENTask` has dead fields (`clauses_to_name`, `name_to_clauses`) only written but never read.

## Key Insights

1. `CONGENTask` inherits from `TestCaseTask` which will later gain `assumptions` (Phase 2). For now, `CONGENTask` must NOT directly inherit from `IncrementalTestCaseTask` or `NonIncrementalTestCaseTask` -- it already inherits from `TestCaseTask` which is correct.
2. `IncrementalCONGENTask(CONGENTask, IncrementalTestCaseTask)` uses MRO to get `assumptions` from `IncrementalTestCaseTask`. After Phase 2 moves `assumptions` to `TestCaseTask`, `CONGENTask` inherits it transitively.
3. **Ordering dependency**: This phase should be done AFTER Phase 2, since `CONGENTask` needs `assumptions` from `TestCaseTask`. Alternatively, temporarily add `assumptions` to `CONGENTask` and remove it in Phase 2.

**Recommended approach**: Do Phase 2 first (add `assumptions` to `TestCaseTask`), then Phase 1 becomes trivial deletion.

**Alternative approach (if doing Phase 1 first)**: Temporarily add `assumptions: List = field(default_factory=list)` to `CONGENTask` directly, then clean up in Phase 2.

## Requirements

### Functional
- Both `IncrementalCONGENTaskPreparation` and `NonIncrementalCONGENTaskPreparation` produce `CONGENTask` instead of subclasses
- Dead fields `clauses_to_name` and `name_to_clauses` are removed
- All existing tests pass unchanged

### Non-functional
- No behavioral change at runtime
- No new dependencies

## Architecture

After change:
```
TestCaseTask (base, with assumptions)
  └── CONGENTask (CONGEN-specific fields)
```

Before change:
```
TestCaseTask (base)
  ├── IncrementalTestCaseTask (assumptions)
  │     └── IncrementalCONGENTask (pass)     <-- REMOVE
  └── NonIncrementalTestCaseTask (assumptions)
        └── NonIncrementalCONGENTask (dead fields) <-- REMOVE
```

## Related Code Files

### Files to Modify

| File | Change |
|------|--------|
| `acqmss/algorithms/task.py` | Delete `IncrementalCONGENTask` and `NonIncrementalCONGENTask` classes; remove imports of `IncrementalTestCaseTask`, `NonIncrementalTestCaseTask` |
| `acqmss/algorithms/task_preparation.py` | Change `IncrementalCONGENTaskPreparation.prepare()` to instantiate `CONGENTask()` instead of `IncrementalCONGENTask()`; same for non-incremental; remove `clauses_to_name`/`name_to_clauses` writes (lines 319-321); update import |
| `acqmss/algorithms/__init__.py` | Remove `IncrementalCONGENTask`, `NonIncrementalCONGENTask` from imports and `__all__` |

## Implementation Steps

1. **If Phase 2 not yet done**: Add `assumptions: List = field(default_factory=list)` to `CONGENTask` in `acqmss/algorithms/task.py`
2. Delete `IncrementalCONGENTask` class (lines 49-56 in task.py)
3. Delete `NonIncrementalCONGENTask` class (lines 59-71 in task.py)
4. Remove imports of `IncrementalTestCaseTask`, `NonIncrementalTestCaseTask` from task.py
5. In `acqmss/algorithms/task_preparation.py`:
   - Change `from .task import IncrementalCONGENTask, NonIncrementalCONGENTask` to `from .task import CONGENTask`
   - In `IncrementalCONGENTaskPreparation.prepare()`: `result = IncrementalCONGENTask()` -> `result = CONGENTask()`
   - In `NonIncrementalCONGENTaskPreparation.prepare()`: `result = NonIncrementalCONGENTask()` -> `result = CONGENTask()`
   - Update type hints in `_prepare_bias_constraints` and `_prepare_examples` from specific types to `CONGENTask`
   - Remove lines 319-321 (`clauses_to_name` and `name_to_clauses` writes) from `NonIncrementalCONGENTaskPreparation._prepare_bias_constraints()`
6. In `acqmss/algorithms/__init__.py`:
   - Remove `IncrementalCONGENTask, NonIncrementalCONGENTask` from import line 24
   - Remove from `__all__` (lines 58-59)

## Todo List

- [ ] Add `assumptions` field to `CONGENTask` (if Phase 2 not done first)
- [ ] Delete `IncrementalCONGENTask` class
- [ ] Delete `NonIncrementalCONGENTask` class
- [ ] Update `task_preparation.py` to use `CONGENTask` directly
- [ ] Remove dead field writes (`clauses_to_name`, `name_to_clauses`)
- [ ] Update `__init__.py` exports
- [ ] Run tests: `PYTHONPATH=. pytest tests/test_congen.py -v`

## Success Criteria

- `PYTHONPATH=. pytest tests/test_congen.py -v` passes
- `PYTHONPATH=. pytest tests/ -v` passes (full suite)
- No `IncrementalCONGENTask` or `NonIncrementalCONGENTask` references remain in codebase
- `grep -r "IncrementalCONGENTask\|NonIncrementalCONGENTask" acqmss/ explanation/ tests/ apps/` returns nothing

## Risk Assessment

- **Low**: MRO change -- `CONGENTask` inherits from `TestCaseTask` directly, no diamond problem
- **Low**: Dead field removal -- confirmed `clauses_to_name` and `name_to_clauses` are only written, never read
- **Medium**: If Phase 2 not done first, `assumptions` must be temporarily added to `CONGENTask`

## Security Considerations

None -- pure refactoring, no behavioral change.

## Next Steps

- Phase 2: Remove `IncrementalTestCaseTask` and `NonIncrementalTestCaseTask`
- Or if doing in recommended order: Do Phase 2 first, then this phase
