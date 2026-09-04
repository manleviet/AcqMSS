# Phase 01: Add prepare() Reuse Support

## Context

- Parent: [plan.md](plan.md)
- Docs: [code-standards.md](../../docs/code-standards.md)

## Overview

- **Priority**: P3
- \*\*Status\*\*: Completed
- **Description**: Add optional `task_input` parameter to `DiagnosisModel.prepare()` and `ConGenModel.prepare()` to enable model reuse without rebuilding.

## Key Insights

- FM data (`constraint_map`, `variables`, `negated_constraint_map`, `next_tseitin_var`) is never mutated by `prepare()` — safe to call multiple times
- `prepare()` creates fresh `DiagnosisTask`/`TestCaseTask` each call, overwrites `_task` and `_description_provider`
- `ConGenModel.task_input` is already public; adding parameter is for API consistency only

## Related Code Files

### Modify

1. **`explanation/models/pysat_diagnosis_model.py`** — `DiagnosisModel.prepare()`
2. **`acqmss/algorithms/congen_model.py`** — `ConGenModel.prepare()`

## Implementation Steps

### Step 1: DiagnosisModel.prepare()

File: `explanation/models/pysat_diagnosis_model.py`

Change signature and add input assignment:

```python
# Before:
def prepare(self) -> DiagnosisTask:
    task_input = self._task_input or TaskInput()


# After:
def prepare(self, task_input: Optional[TaskInput] = None) -> DiagnosisTask:
    """... existing docstring ...

    Args:
        task_input: Optional TaskInput to use. If provided, updates the model's
            task input before preparing. If None, uses existing task input.

    Note:
        After calling prepare() with new input, any existing checker instances
        must be recreated as they hold references to the previous KB/assumptions.
    """
    if task_input is not None:
        self._task_input = task_input
    task_input = self._task_input or TaskInput()
```

### Step 2: ConGenModel.prepare()

File: `acqmss/algorithms/congen_model.py`

Add `task_input` parameter:

```python
# Before:
def prepare(self, mode_name: str = "congen_root") -> ConGenTask:


# After:
def prepare(self, mode_name: str = "congen_root", task_input: Optional[TaskInput] = None) -> ConGenTask:
    """... existing docstring ...

    Args:
        mode_name: Mode name for logging.
        task_input: Optional TaskInput. If provided, updates model's task_input
            before preparing. If None, uses existing task_input.

    Note:
        After calling prepare() with new input, any existing checker instances
        must be recreated as they hold references to the previous KB/assumptions.
    """
    if task_input is not None:
        self._task_input = task_input
```

Add import if not present: `from typing import Optional`

### Step 3: Run tests

```bash
PYTHONPATH=. pytest tests/ -x -v
```

## Todo List

- [x] Update `DiagnosisModel.prepare()` signature and docstring
- [x] Update `ConGenModel.prepare()` signature and docstring
- [x] Run existing tests to verify backward compatibility
- [x] Run mypy/ruff to verify type correctness

## Success Criteria

- All existing tests pass without modification
- `DiagnosisModel` can be reused: `model.prepare(TaskInput(configuration=cfg2))` works
- `ConGenModel` can be reused: `model.prepare(task_input=TaskInput(...))` works
- No breaking changes to `DiagnosisModelBuilder.build()` flow

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Checker staleness after re-prepare | Medium — old checker has stale KB | Document in docstring |
| Variable name shadowing (`task_input` param vs local) | Low | Use `if` guard before reassigning |

## Next Steps

- Consider adding reuse test cases in a follow-up if needed
