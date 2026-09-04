# Phase 1: Package Rename (interactive/ -> quacq/)

## Context Links
- [Brainstorm](../reports/brainstorm-260227-1132-rename-interactive-to-quacq.md)
- [Plan overview](plan.md)

## Overview
- **Priority**: High (highest blast radius, must go first)
- **Status**: pending
- **Effort**: 40m

Rename folder `conacq/algorithms/interactive/` -> `conacq/algorithms/quacq/`, rename 2 files inside, rename 2 classes, update all imports.

## Key Insights
- 8 files inside the folder; only 2 need file rename (`interactive_model.py`, `interactive_task_preparation.py`)
- 2 class renames: `InteractiveModel` -> `QuAcqModel`, `InteractiveTaskPreparation` -> `QuAcqTaskPreparation`
- Internal imports within the package use relative paths (`.quacq`, `.findscope`, etc.) -- folder rename changes the package path but relative imports within the folder stay the same
- External imports use `conacq.algorithms.interactive` -- all need update to `conacq.algorithms.quacq`

## Requirements

### Functional
- All existing tests pass after rename
- No import errors at any level

### Non-functional
- Git history preserved via `git mv`
- No stale `__pycache__` bytecode

## Related Code Files

### Rename (git mv)
| From | To |
|------|-----|
| `conacq/algorithms/interactive/` | `conacq/algorithms/quacq/` |
| `conacq/algorithms/quacq/interactive_model.py` | `conacq/algorithms/quacq/quacq_model.py` |
| `conacq/algorithms/quacq/interactive_task_preparation.py` | `conacq/algorithms/quacq/quacq_task_preparation.py` |

### Class Renames
| From | To | File |
|------|-----|------|
| `InteractiveModel` | `QuAcqModel` | `quacq_model.py` |
| `InteractiveTaskPreparation` | `QuAcqTaskPreparation` | `quacq_task_preparation.py` |

### Import Updates (external consumers)

| File | Change |
|------|--------|
| `conacq/algorithms/__init__.py` | `from .interactive import ...` -> `from .quacq import ...` |
| `conacq/algorithms/acqmss/__init__.py` | `from ..interactive import ...` -> `from ..quacq import ...` |
| `conacq/runners/interactive_runner.py` | `from conacq.algorithms.interactive.interactive_model` -> `from conacq.algorithms.quacq.quacq_model` |
| `conacq/runners/interactive_runner.py` | `from conacq.algorithms.interactive.quacq` -> `from conacq.algorithms.quacq.quacq` |
| `conacq/eval/cross_validation.py` | (lazy import of InteractiveRunner -- no direct package ref, but verify) |
| `conacq/eval/progressive_evaluation.py` | No direct package ref (imports from runners) |
| `conacq/example_generators/query_generator.py` | `from conacq.algorithms.interactive._task_compat` -> `from conacq.algorithms.quacq._task_compat` |
| `tests/test_interactive.py` | 6 occurrences of `conacq.algorithms.interactive` -> `conacq.algorithms.quacq` |

### Internal Import Updates (within renamed folder)

| File | Change |
|------|--------|
| `quacq/findscope.py` | `from conacq.algorithms.interactive._task_compat` -> `from conacq.algorithms.quacq._task_compat` |
| `quacq/findc.py` | `from conacq.algorithms.interactive._task_compat` -> `from conacq.algorithms.quacq._task_compat` |
| `quacq/quacq_model.py` | `from .interactive_task_preparation` -> `from .quacq_task_preparation` |
| `quacq/__init__.py` | `from .interactive_model` -> `from .quacq_model`; `from .interactive_task_preparation` -> `from .quacq_task_preparation`; update `__all__`; update docstring example |
| `quacq/quacq_task_preparation.py` | `from .interactive_model` -> `from .quacq_model` (TYPE_CHECKING import) |

## Implementation Steps

1. `git mv conacq/algorithms/interactive conacq/algorithms/quacq`
2. `git mv conacq/algorithms/quacq/interactive_model.py conacq/algorithms/quacq/quacq_model.py`
3. `git mv conacq/algorithms/quacq/interactive_task_preparation.py conacq/algorithms/quacq/quacq_task_preparation.py`
4. Delete old `__pycache__`: `rm -rf conacq/algorithms/interactive/__pycache__ conacq/algorithms/quacq/__pycache__`
5. Rename class `InteractiveModel` -> `QuAcqModel` in `quacq_model.py`
6. Rename class `InteractiveTaskPreparation` -> `QuAcqTaskPreparation` in `quacq_task_preparation.py`
7. Update `quacq/__init__.py`:
   - Change import paths for renamed files/classes
   - Update `__all__` entries: `'InteractiveModel'` -> `'QuAcqModel'`, `'InteractiveTaskPreparation'` -> `'QuAcqTaskPreparation'`
   - Add backward-compat aliases: `InteractiveModel = QuAcqModel`, `InteractiveTaskPreparation = QuAcqTaskPreparation`
   - Update module docstring example import path
8. Update internal imports in `findscope.py`, `findc.py` (absolute `conacq.algorithms.interactive` -> `conacq.algorithms.quacq`)
9. Update `quacq_model.py` import: `.interactive_task_preparation` -> `.quacq_task_preparation`
10. Update `quacq_task_preparation.py` TYPE_CHECKING import: `.interactive_model` -> `.quacq_model`
11. Update `conacq/algorithms/__init__.py`: `from .interactive import ...` -> `from .quacq import ...`
12. Update `conacq/algorithms/acqmss/__init__.py`: `from ..interactive import ...` -> `from ..quacq import ...`
13. Update `conacq/runners/interactive_runner.py`: 2 lazy imports of package path
14. Update `conacq/example_generators/query_generator.py`: 1 import of `_task_compat`
15. Update `tests/test_interactive.py`: 6 import lines
16. Run `PYTHONPATH=. pytest tests/ -v` to verify

## Todo List

- [ ] git mv folder
- [ ] git mv 2 files inside
- [ ] Delete __pycache__
- [ ] Rename InteractiveModel -> QuAcqModel (class)
- [ ] Rename InteractiveTaskPreparation -> QuAcqTaskPreparation (class)
- [ ] Update quacq/__init__.py (imports, __all__, docstring, backward compat aliases)
- [ ] Update internal imports (findscope, findc, quacq_model, quacq_task_preparation)
- [ ] Update conacq/algorithms/__init__.py
- [ ] Update conacq/algorithms/acqmss/__init__.py
- [ ] Update conacq/runners/interactive_runner.py (2 lazy imports)
- [ ] Update conacq/example_generators/query_generator.py
- [ ] Update tests/test_interactive.py (6 imports)
- [ ] Run tests -- all pass

## Success Criteria
- `from conacq.algorithms.quacq import QuAcqModel, QuAcq` works
- Backward compat: `InteractiveModel = QuAcqModel` alias exported
- All tests pass
- No `conacq.algorithms.interactive` import path remains in `.py` files (except plans/docs)

## Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| __pycache__ stale bytecode | Import errors | Delete after git mv |
| Missing import update | ImportError | Grep for `conacq.algorithms.interactive` after step 15 |
| Circular import with TYPE_CHECKING | ImportError | Already using TYPE_CHECKING guard -- just update path |

## Next Steps
- Phase 2: Runner Rename (depends on this phase completing)
