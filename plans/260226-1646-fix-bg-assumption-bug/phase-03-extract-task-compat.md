# Phase 3: Extract Shared Duck-Typing Helpers (DRY)

## Context
- Parent: [plan.md](plan.md)
- Independent of Phases 1-2 (can run in parallel)
- Review: Issues #5, #6

## Overview
- **Priority**: Medium
- **Status**: complete
- **Description**: Extract duplicated `_get_clause_map` and `_get_negated_clauses` helpers into shared module `_task_compat.py`. Add `_get_bg_clauses` helper.

## Key Insights

Duplicated across 4 files (3 identical `_get_clause_map`, 2 identical `_get_negated_clauses`):
- `quacq.py`: `_get_clause_map` (lines 41-45)
- `findscope.py`: `_get_clause_map` (lines 20-24)
- `findc.py`: `_get_clause_map` (lines 23-27), `_get_negated_clauses` (lines 30-36)
- `query_generator.py`: `_get_negated_clauses` (lines 19-29), `_get_clause_map_for_priority` (lines 32-37)

## Related Code Files

- **Create**: `conacq/algorithms/interactive/_task_compat.py`
- **Modify**: `conacq/algorithms/interactive/quacq.py` — remove local, import shared
- **Modify**: `conacq/algorithms/interactive/findscope.py` — remove local, import shared
- **Modify**: `conacq/algorithms/interactive/findc.py` — remove local, import shared
- **Modify**: `conacq/example_generators/query_generator.py` — remove local, import shared

## Implementation Steps

### 1. Create `_task_compat.py`

```python
"""
Shared duck-typing helpers for QuAcqTask / InteractiveTask compatibility.

Both task types provide similar clause mappings but with different attribute names:
- QuAcqTask: constraint_clauses (int keys), negated_clauses (int keys)
- InteractiveTask: constraint_map (str keys), negated_constraint_map (str keys)
"""


def get_clause_map(task):
    """Get constraint -> clauses mapping from either task type."""
    if hasattr(task, 'constraint_clauses'):
        return task.constraint_clauses
    return task.constraint_map


def get_negated_clauses(task, c_id):
    """Get negated clauses for a constraint from either task type."""
    if hasattr(task, 'negated_clauses') and isinstance(c_id, int):
        return task.negated_clauses.get(c_id, [])
    if hasattr(task, 'negated_constraint_map'):
        return task.negated_constraint_map.get(c_id, [])
    return []


def get_bg_clauses(task) -> list:
    """Get raw BG clauses from either task type.

    QuAcqTask: uses background_clauses (raw CNF, no assumption guards)
    InteractiveTask: wraps background feature IDs as unit clauses
    """
    if hasattr(task, 'background_clauses') and task.background_clauses:
        return list(task.background_clauses)
    if task.background:
        if isinstance(task.background[0], int):
            return [[lit] for lit in task.background]
        return list(task.background)
    return []
```

### 2. Update imports in each file

**quacq.py**: Remove local `_get_clause_map` (lines 41-45). Add:
```python
from ._task_compat import get_clause_map as _get_clause_map, get_bg_clauses
```

**findscope.py**: Remove local `_get_clause_map` (lines 20-24). Add:
```python
from conacq.algorithms.interactive._task_compat import get_clause_map as _get_clause_map
```

**findc.py**: Remove local `_get_clause_map` + `_get_negated_clauses` (lines 23-36). Add:
```python
from conacq.algorithms.interactive._task_compat import get_clause_map as _get_clause_map, get_negated_clauses as _get_negated_clauses
```

**query_generator.py**: Remove local `_get_negated_clauses` (lines 19-29). Add:
```python
from conacq.algorithms.interactive._task_compat import get_negated_clauses as _get_negated_clauses
```

Note: `_get_clause_map_for_priority` in query_generator.py is slightly different (handles both QuAcqTask and InteractiveTask for a single c_id). Keep it local or add to compat module.

### 3. Update `_find_conflict` and `generate()` to use `get_bg_clauses`

After Phase 2 fix, simplify BG handling in `_find_conflict`:
```python
bg_clauses = task.get_kb_clauses()
bg_clauses.extend(get_bg_clauses(task))
```

And in `QueryGenerator.generate()`:
```python
bg_clauses=get_bg_clauses(task),
```

## Todo

- [x] Create `_task_compat.py` with shared helpers
- [x] Update quacq.py imports
- [x] Update findscope.py imports
- [x] Update findc.py imports
- [x] Update query_generator.py imports
- [x] Simplify BG handling using `get_bg_clauses`

## Success Criteria

- Zero duplicated duck-typing helpers across files
- All existing tests pass unchanged
- `get_bg_clauses` returns correct clauses for both task types
