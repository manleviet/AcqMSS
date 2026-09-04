# Phase 7: Deprecate Old Classes

## Context Links
- [Parent Plan](plan.md) | [Phase 6](phase-06-update-tests.md)
- Source: `conacq/algorithms/interactive/task.py` (InteractiveTask, 195 LOC)
- Source: `conacq/algorithms/interactive/learner.py` (InteractiveLearner, 379 LOC)
- Source: `conacq/algorithms/interactive/__init__.py` (74 LOC)

## Overview
- **Priority**: P3
- **Status**: completed
- **Depends on**: Phase 6 (all tests pass)
- **Description**: Add deprecation warnings to InteractiveTask and InteractiveLearner. Document migration path. Do NOT delete — removal in separate future commit.

## Key Insights
1. InteractiveTask and InteractiveLearner still work (old path). Deprecation, not deletion.
2. Python `warnings.warn()` with `DeprecationWarning` category is standard.
3. `__init__.py` exports should keep old classes but add new ones.
4. InteractiveLearner.evaluate() can remain as-is — it uses kb_constraints (str) which is still populated.

## Requirements

### Functional
- InteractiveTask.__init__() emits DeprecationWarning
- InteractiveLearner.__init__() emits DeprecationWarning
- Both warnings include migration guidance
- New classes exported from __init__.py

### Non-functional
- No behavioral changes to deprecated classes
- Tests for deprecated path still pass (warnings don't break tests)

## Related Code Files

### Files to Modify
| File | Changes |
|------|---------|
| `conacq/algorithms/interactive/task.py` | Add deprecation warning in __post_init__ |
| `conacq/algorithms/interactive/learner.py` | Add deprecation warning in __init__ |
| `conacq/algorithms/interactive/__init__.py` | Add new exports, keep old |

## Implementation Steps

### Step 1: Add deprecation to InteractiveTask (task.py)

```python
import warnings

@dataclass
class InteractiveTask:
    """
    [DEPRECATED] Use QuAcqTask instead.
    ...existing docstring...
    """
    # ... fields unchanged ...

    def __post_init__(self):
        warnings.warn(
            "InteractiveTask is deprecated. Use QuAcqTask with InteractiveModel.prepare() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        if not isinstance(self.bias, set):
            self.bias = set(self.bias)
```

### Step 2: Add deprecation to InteractiveLearner (learner.py)

```python
import warnings

class InteractiveLearner:
    """
    [DEPRECATED] Use InteractiveModel + QuAcq directly instead.
    ...existing docstring...
    """

    def __init__(self, task, oracle=None, solver_name='glucose4',
                 profiler=None, fm_path=None, bias_path=None):
        warnings.warn(
            "InteractiveLearner is deprecated. "
            "Use InteractiveModel.from_bias(path).prepare(oracle) + QuAcq.learn() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # ... rest of __init__ unchanged ...
```

### Step 3: Update __init__.py exports

```python
"""Interactive (QuAcq-style) constraint acquisition module."""

# New API (preferred)
from .quacq_task import QuAcqTask
from .interactive_model import InteractiveModel
from .interactive_task_preparation import InteractiveTaskPreparation

# Existing API
from .task import InteractiveTask          # deprecated
from .result import InteractiveResult
from conacq.oracle import (
    Oracle, FeatureModelOracle, UserPromptOracle, CachedOracle,
)
from .quacq import QuAcq
from .findscope import find_scope
from .findc import find_c
from .learner import InteractiveLearner    # deprecated
from .learner import run_interactive_learning  # deprecated

__all__ = [
    # New API
    'QuAcqTask',
    'InteractiveModel',
    'InteractiveTaskPreparation',
    # Core
    'QuAcq',
    'InteractiveResult',
    'find_scope',
    'find_c',
    # Oracle
    'Oracle',
    'FeatureModelOracle',
    'UserPromptOracle',
    'CachedOracle',
    # Deprecated (still exported for backward compat)
    'InteractiveTask',
    'InteractiveLearner',
    'run_interactive_learning',
]
```

### Step 4: Suppress deprecation warnings in old tests

In `tests/test_interactive.py`, for tests that use the deprecated path:
```python
import warnings

class TestInteractiveTask:
    def test_task_creation(self, interactive_task):
        # interactive_task fixture already created — warning already fired
        # No suppression needed in test body

# OR in the fixture:
@pytest.fixture
def interactive_task(oracle, bias):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        # ... create InteractiveTask ...
```

### Step 5: Document migration path

Add comment block at top of task.py and learner.py:

```python
# MIGRATION GUIDE:
# Old: InteractiveLearner.from_files(fm, bias) -> learner.learn()
# New: InteractiveModel.from_bias(bias).prepare(oracle) -> QuAcq().learn(task, oracle, provider)
#
# Old: InteractiveTask(bias=[str], constraint_map={str: clauses})
# New: QuAcqTask created by InteractiveModel.prepare() — bias is Set[int]
```

## Todo List
- [ ] Add DeprecationWarning to InteractiveTask.__post_init__()
- [ ] Add DeprecationWarning to InteractiveLearner.__init__()
- [ ] Add deprecation note to class docstrings
- [ ] Update __init__.py with new exports (QuAcqTask, InteractiveModel, InteractiveTaskPreparation)
- [ ] Suppress deprecation warnings in old test fixtures
- [ ] Add migration guide comments
- [ ] Run full test suite to verify no regressions

## Success Criteria
- DeprecationWarning emitted when InteractiveTask or InteractiveLearner instantiated
- All tests pass (warnings suppressed in deprecated-path tests)
- New classes properly exported from __init__.py
- `from conacq.algorithms.interactive import QuAcqTask, InteractiveModel` works

## Risk Assessment
1. **Warning noise in tests**: pytest may show warnings by default. Suppress in fixtures or configure pytest.ini to filter. Low risk.
2. **Third-party consumers**: If any external code uses InteractiveTask/InteractiveLearner, they get a clear deprecation message with migration instructions. This is expected behavior.

## Security Considerations
- No changes to external input handling

## Next Steps
- Future commit: Remove InteractiveTask, InteractiveLearner, run_interactive_learning after all consumers migrated
- Future commit: Remove old test fixtures and deprecated-path tests
