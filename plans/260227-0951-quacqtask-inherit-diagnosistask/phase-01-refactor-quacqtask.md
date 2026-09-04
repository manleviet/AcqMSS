# Phase 1: Refactor QuAcqTask Class

## Context
- Parent plan: [plan.md](plan.md)
- DiagnosisTask: `explanation/models/task_preparation.py:86-107`
- QuAcqTask: `conacq/algorithms/interactive/quacq_task.py:11-197`

## Overview
- **Priority**: High (blocks Phase 2 and 3)
- **Description**: Make QuAcqTask inherit DiagnosisTask, remove duplicate fields
- **Status**: completed

## Key Insights
- DiagnosisTask fields all have defaults → child dataclass works fine
- `prepare_kb()` writes to `set_kb` and `assumptions` by name → inherited fields work
- Constructor order: parent fields first, then child fields

## Related Code Files
- **Modify**: `conacq/algorithms/interactive/quacq_task.py`
- **Modify**: `conacq/algorithms/interactive/interactive_task_preparation.py`
- **Read-only**: `explanation/models/task_preparation.py` (DiagnosisTask definition)

## Implementation Steps

### 1. Update QuAcqTask class definition

```python
# OLD
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple

@dataclass
class QuAcqTask:

# NEW
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from explanation.models.task_preparation import DiagnosisTask

@dataclass
class QuAcqTask(DiagnosisTask):
```

### 2. Remove duplicate field declarations from QuAcqTask

Remove these fields (now inherited from DiagnosisTask):
- `set_kb: List[List[int]]` (lines 39-41)
- `assumptions: List[int]` (lines 43-45)
- `negation_map: Dict[int, int]` (lines 47-49)

### 3. Rename `background` field to `set_b`

Remove field declaration:
- `background: List[int]` (lines 51-53) → inherited as `set_b` from DiagnosisTask

### 4. Update `interactive_task_preparation.py`

Change `result.background = ...` → `result.set_b = ...` (line 57)

### 5. Update `clone()` method

```python
def clone(self) -> 'QuAcqTask':
    return QuAcqTask(
        bias=set(self.bias),
        learned_kb=self.learned_kb.copy(),
        set_b=self.set_b.copy(),              # was: background=self.background.copy()
        set_kb=[c.copy() for c in self.set_kb],
        assumptions=self.assumptions.copy(),
        negation_map=dict(self.negation_map),
        background_clauses=[c.copy() for c in self.background_clauses],
        feature_ids=dict(self.feature_ids),
        id_to_feature=dict(self.id_to_feature),
        constraint_clauses={k: [c.copy() for c in v]
                            for k, v in self.constraint_clauses.items()},
        negated_clauses={k: [c.copy() for c in v]
                         for k, v in self.negated_clauses.items()},
        n_queries=self.n_queries,
        query_history=[(c.copy(), a, s) for c, a, s in self.query_history]
    )
```

### 6. Update docstring

Update Attributes docstring: remove `set_kb`, `assumptions`, `negation_map` entries (inherited). Change `background` → `set_b`.

## Todo List
- [x] Add DiagnosisTask import and inheritance
- [x] Remove duplicate fields (set_kb, assumptions, negation_map)
- [x] Remove background field (use inherited set_b)
- [x] Update clone() to use set_b
- [x] Update interactive_task_preparation.py (result.background → result.set_b)
- [x] Update docstring

## Success Criteria
- QuAcqTask inherits DiagnosisTask
- No duplicate field declarations
- `QuAcqTask()` with no args still works (all defaults)
- `prepare_kb()` writes to inherited `set_kb`/`assumptions`

## Risk Assessment
- **Dataclass field order**: Parent fields come first in constructor. All have defaults → no positional arg issues.
- **Type looseness**: DiagnosisTask uses untyped `Dict`/`List`. Acceptable trade-off for hierarchy alignment.
