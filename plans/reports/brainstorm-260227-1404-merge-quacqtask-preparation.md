# Brainstorm: Merge QuAcqTask + QuAcqTaskPreparation

## Problem
`QuAcqTaskPreparation` (96 lines) only creates `QuAcqTask` — co-locating them reduces file fragmentation and keeps creation logic next to the data structure.

## Evaluated Approaches

### Option A: Simple merge (SELECTED)
- Move `QuAcqTaskPreparation` class into `quacq_task.py`
- Keep `quacq_task_preparation.py` as thin re-export stub for backward compat
- **Pros:** Simplest, lowest risk, co-locates creation logic
- **Cons:** ~274 lines (37% over 200-line threshold) — acceptable since two clear sections

### Option B: Merge + extract utils
- Merge but extract utility methods (`violates_clauses`, `_get_constraint_vars`) to `quacq_task_utils.py`
- **Pros:** Keeps main file at ~200 lines
- **Cons:** Creates new file, splits simple utility methods unnecessarily

### Option C: classmethod `QuAcqTask.from_model()`
- Turn `prepare()` into classmethod on `QuAcqTask`
- **Pros:** Cleanest API, eliminates preparation class
- **Cons:** Breaks `ConGenTaskPreparation` pattern, `PreparationOutput` returns both task + provider

## Implementation Plan

### Step 1: Move `QuAcqTaskPreparation` into `quacq_task.py`
- Add imports: `DescriptionProvider`, `PreparationOutput`, `prepare_kb`, `_ASSUMPTION_PAIR_STRIDE`, `negate_cnf_tseitin`, `TYPE_CHECKING` for `QuAcqModel`, `FeatureModelOracle`
- Place class after `QuAcqTask` definition

### Step 2: Update `quacq_task_preparation.py` to re-export stub
```python
"""Backward-compat re-export."""
from .quacq_task import QuAcqTaskPreparation, QuAcqTask

InteractiveTaskPreparation = QuAcqTaskPreparation
```

### Step 3: Update `__init__.py`
- Change import: `from .quacq_task import QuAcqTask, QuAcqTaskPreparation`
- Keep re-export from `quacq_task_preparation` for `InteractiveTaskPreparation` alias

### Step 4: Verify no import breakage
- `quacq_model.py` imports `QuAcqTask` from `.quacq_task` — unchanged
- `quacq.py` imports `QuAcqTask` from `.quacq_task` — unchanged
- `tests/test_quacq.py` imports `QuAcqTask` from `.quacq_task` — unchanged
- `quacq_task_preparation.py` becomes stub — all existing imports still work

### Consumers (no changes needed)
| File | Import | Status |
|------|--------|--------|
| `quacq.py` | `from .quacq_task import QuAcqTask` | unchanged |
| `quacq_model.py` | `from .quacq_task import QuAcqTask` | unchanged |
| `__init__.py` | `from .quacq_task import QuAcqTask` | add `QuAcqTaskPreparation` |
| `tests/test_quacq.py` | `from ...quacq_task import QuAcqTask` | unchanged |

## Risk
- **Low**: All existing import paths remain valid via re-export stub
- The only real change is where `QuAcqTaskPreparation` class definition lives

## Success Criteria
- All tests pass (`PYTHONPATH=. pytest tests/ -v`)
- No import errors
- `quacq_task.py` contains both `QuAcqTask` and `QuAcqTaskPreparation`
- `quacq_task_preparation.py` is thin re-export stub
