# Phase 1: Refactor CONGENModel to Self-Preparing Class

## Context Links

- [DiagnosisModel reference](../../explanation/models/pysat_diagnosis_model.py) -- pattern to follow
- [Current CONGENModel](../../conacq/algorithms/congen_model.py) -- file to refactor
- [CONGENTaskPreparation](../../conacq/algorithms/task_preparation.py) -- called from prepare()
- [Code standards](../../docs/code-standards.md)

## Overview

- **Priority**: P2
- **Status**: pending
- **Description**: Convert CONGENModel from @dataclass to regular class with `prepare()` method, `task` property, and `description_provider` property -- mirroring DiagnosisModel's pattern.

## Key Insights

1. DiagnosisModel stores `_task`, `_description_provider` as `Optional` fields, exposes via properties with RuntimeError guard
2. DiagnosisModel.prepare() delegates to strategy (TaskPreparationFactory) and stores result internally
3. CONGENModel currently holds data only; preparation is entirely external
4. CONGENModel's `from_bias_and_examples()` classmethod is a good factory -- keep it
5. `_examples_to_testsuite()` staticmethod is internal utility -- keep it

## Requirements

### Functional
- CONGENModel must have `prepare(mode_name: str = "congen") -> CONGENTask` method
- `task` property must raise RuntimeError if `prepare()` not called
- `description_provider` property must raise RuntimeError if `prepare()` not called
- `from_bias_and_examples()` classmethod must remain as factory constructor
- All existing fields must remain accessible (constraint_map, variables, task_input, etc.)

### Non-Functional
- Follow DiagnosisModel pattern exactly for consistency
- Type hints on all public methods
- Google-style docstrings

## Architecture

```
Before:
  caller -> CONGENTaskPreparation(mode).prepare(model) -> PreparationOutput
  caller -> output.task, output.description_provider

After:
  caller -> model.prepare(mode) -> CONGENTask
  caller -> model.task, model.description_provider
  (internally: model delegates to CONGENTaskPreparation)
```

## Related Code Files

- **Modify**: `acqmss/algorithms/model.py`
- **Read-only reference**: `explanation/models/pysat_diagnosis_model.py`
- **Read-only reference**: `explanation/models/task_preparation.py` (PreparationOutput, DescriptionProvider)

## Implementation Steps

### Step 1: Remove @dataclass decorator, add `__init__`

Replace the dataclass with a regular class. Move all fields into `__init__`:

```python
class CONGENModel:
    """Model for ConGen algorithm.

    Uses composition to delegate task preparation to ConGenTaskPreparation.
    Call prepare() before accessing task or description_provider.
    """

    def __init__(self) -> None:
        self.constraint_map: Dict[str, List[List[int]]] = {}
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        self.variables: Dict[str, int] = {}
        self.task_input: TaskInput = TaskInput()
        self.next_tseitin_var: int = 1
        self.background_knowledge: List[int] = []  # Phase 2 -- for now keep root_feature_id

        # Populated after prepare()
        self._task: Optional[CONGENTask] = None
        self._description_provider: Optional[DescriptionProvider] = None
```

### Step 2: Add `task` and `description_provider` properties

Follow DiagnosisModel lines 84-97 exactly:

```python
@property
def task(self) -> CONGENTask:
    """Get prepared task. Call prepare() first."""
    if self._task is None:
        raise RuntimeError("Call prepare() first")
    return self._task

@property
def description_provider(self) -> DescriptionProvider:
    """Get description provider. Call prepare() first."""
    if self._description_provider is None:
        raise RuntimeError("Call prepare() first")
    return self._description_provider
```

### Step 3: Add `prepare()` method

Delegates to CONGENTaskPreparation, stores result:

```python
def prepare(self, mode_name: str = "congen_root") -> CONGENTask:
    """Prepare ConGen task using ConGenTaskPreparation strategy.

    Args:
        mode_name: Mode name for logging (e.g., "incremental-congen_root")

    Returns:
        ConGenTask ready for GenerateNE and ConGen.
    """
    preparation = CONGENTaskPreparation(mode_name)
    output = preparation.prepare(self)

    self._task = output.task
    self._description_provider = output.description_provider
    return self._task
```

### Step 4: Update `from_bias_and_examples()` classmethod

Must instantiate new-style class:

```python
@classmethod
def from_bias_and_examples(
        cls,
        bias_constraints: Dict[str, List[List[int]]],
        positive_examples: List[Dict[str, bool]],
        negative_examples: List[Dict[str, bool]],
        feature_ids: Dict[str, int],
        root_feature_id: Optional[int] = None  # Phase 2 changes this
) -> 'ConGenModel':
    # Find max variable ID
    max_var = max(feature_ids.values()) if feature_ids else 0
    for clauses in bias_constraints.values():
        for clause in clauses:
            for lit in clause:
                max_var = max(max_var, abs(lit))

    positive_tc = cls._examples_to_testsuite(positive_examples)
    negative_tc = cls._examples_to_testsuite(negative_examples)

    model = cls()
    model.constraint_map = bias_constraints
    model.negated_constraint_map = {}
    model.variables = feature_ids
    model.task_input = TaskInput(
        positive_test_cases=positive_tc,
        negative_test_cases=negative_tc
    )
    model.next_tseitin_var = max_var + 1
    model.root_feature_id = root_feature_id  # Phase 2 changes
    return model
```

### Step 5: Keep `_examples_to_testsuite()` staticmethod unchanged

No changes needed.

### Step 6: Update imports

Add import for CONGENTask and DescriptionProvider:

```python
from typing import Dict, List, Optional
from explanation.models.testsuite import Assignment, TestCase, TestSuite
from explanation.models.task_preparation import TaskInput, DescriptionProvider
from .task import CONGENTask
from .task_preparation import CONGENTaskPreparation
```

Note: Circular import risk -- CONGENTaskPreparation imports CONGENModel. Use TYPE_CHECKING guard:

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .task_preparation import CONGENTaskPreparation
```

Then in `prepare()`, do the import locally:

```python
def prepare(self, mode_name: str = "congen_root") -> CONGENTask:
    from .task_preparation import CONGENTaskPreparation
    preparation = CONGENTaskPreparation(mode_name)
    ...
```

## Todo List

- [ ] Remove @dataclass, convert to regular class with `__init__`
- [ ] Add `_task` and `_description_provider` Optional fields
- [ ] Add `task` property with RuntimeError guard
- [ ] Add `description_provider` property with RuntimeError guard
- [ ] Add `prepare(mode_name)` method delegating to CONGENTaskPreparation
- [ ] Update `from_bias_and_examples()` to use attribute assignment
- [ ] Handle circular import (local import in prepare())
- [ ] Keep `_examples_to_testsuite()` staticmethod
- [ ] Run type check: `mypy acqmss/algorithms/model.py`
- [ ] Verify no regressions: `PYTHONPATH=. pytest tests/test_congen.py -v`

## Success Criteria

- `CONGENModel` has `prepare()`, `task`, `description_provider` matching DiagnosisModel pattern
- `from_bias_and_examples()` still works as factory
- Existing tests pass (callers updated in Phase 3)
- No circular import errors
- Type hints on all public methods

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Circular import model<->task_preparation | High | Medium | Local import in prepare() |
| Callers break before Phase 3 | Certain | Low | Phases 1+3 applied together |
| Missing field in __init__ | Low | Medium | Compare against dataclass fields |

## Security Considerations

- No security impact -- pure structural refactor, no I/O changes

## Next Steps

- Phase 2: Replace `root_feature_id` with `background_knowledge`
- Phase 3: Update all callers to use `model.prepare()`
