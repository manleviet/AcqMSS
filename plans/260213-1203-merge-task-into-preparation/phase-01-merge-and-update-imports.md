---
parent: plan.md
status: complete
priority: P3
---

# Phase 01: Merge and Update Imports

## Overview

Move `CONGENTask` dataclass from `task.py` into `task_preparation.py`, update all imports, delete `task.py`.

## Key Insights

- `CONGENTask` is a pure dataclass (42 lines, no business logic beyond a getter)
- `task_preparation.py` already imports it — removing internal dependency
- 4 files import `CONGENTask` directly; all use relative imports within the package

## Related Code Files

**Modify:**
- `acqmss/algorithms/task_preparation.py` — add `CONGENTask`, remove `from .task import CONGENTask`
- `acqmss/algorithms/__init__.py` — `from .task import CONGENTask` → `from .task_preparation import CONGENTask`
- `acqmss/algorithms/congen.py` — `from .task import CONGENTask` → `from .task_preparation import CONGENTask`
- `acqmss/algorithms/model.py` — `from .task import CONGENTask` → `from .task_preparation import CONGENTask`

**Delete:**
- `acqmss/algorithms/task.py`

## Implementation Steps

1. In `task_preparation.py`:
   - Add `from typing import Any` to existing typing imports
   - Add `CONGENTask` dataclass BEFORE `CONGENTaskPreparation` class
   - Remove `from .task import CONGENTask` import line
2. Update `__init__.py`: change import source from `.task` to `.task_preparation`
3. Update `congen.py`: change `from .task import CONGENTask` → `from .task_preparation import CONGENTask`
4. Update `model.py`: change `from .task import CONGENTask` → `from .task_preparation import CONGENTask`
5. Delete `task.py`
6. Run `PYTHONPATH=. python -c "from acqmss.algorithms import CONGENTask; print('OK')"` to verify imports
7. Run `PYTHONPATH=. pytest tests/test_congen.py -x` to verify tests pass

## Todo List

- [x] Move CONGENTask into task_preparation.py
- [x] Update __init__.py import
- [x] Update congen.py import
- [x] Update model.py import
- [x] Delete task.py
- [x] Verify imports resolve
- [x] Run tests

## Success Criteria

- `from acqmss.algorithms import CONGENTask` works
- All existing tests pass
- `task.py` no longer exists

## Risk Assessment

- **Low risk**: Pure mechanical refactor, no logic changes
- Mitigation: verify imports + run tests after each step
