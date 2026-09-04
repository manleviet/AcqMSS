# Phase 1: Make QuAcqTask Immutable

## Context Links

- [Plan overview](plan.md)
- [QuAcqTask source](../../conacq/algorithms/quacq/task_preparation.py)
- [DiagnosisTask base](../../explanation/models/task_preparation.py)
- [ConGenTask pattern reference](../../conacq/algorithms/task_preparation.py)

## Overview

- **Date**: 2026-02-27
- **Priority**: P2
- **Status**: pending
- **Description**: Remove mutable fields and mutation methods from QuAcqTask. Store initial bias IDs in inherited `set_c` field (matching ConGenTask pattern). Keep immutable data fields (feature_ids, constraint_clauses, etc).

## Key Insights

1. `task.bias` (Set[int]) is semantically identical to `set_c` (List[int]) from DiagnosisTask — both hold bias constraint assumption IDs
2. ConGenTask uses `set_c` for bias and never mutates it. QuAcqTask should do the same.
3. `learned_kb`, `n_queries`, `query_history` are algorithm OUTPUT, not task INPUT
4. Immutable data fields (`background_clauses`, `feature_ids`, `id_to_feature`, `constraint_clauses`, `negated_clauses`) stay on the task — they're read-only input data
5. Helper methods that read from immutable fields stay: `config_to_assumptions()`, `partial_config_to_assumptions()`, `model_to_config()`, `get_constraints_with_scope()`, `violates_clauses()`, `get_kb_clauses()` (but signature changes)

## Requirements

### Functional
- Remove fields: `bias`, `learned_kb`, `n_queries`, `query_history`
- Remove methods: `add_to_kb()`, `remove_from_bias()`, `record_query()`, `clone()`
- In `QuAcqTaskPreparation.prepare()`: assign bias IDs to `result.set_c` instead of `result.bias`
- Keep `get_kb_clauses()` but change it to accept `learned_kb` as parameter

### Non-Functional
- All existing tests should fail predictably (they test removed fields/methods)
- No runtime behavior change until Phase 2 wires up the algorithm

## Architecture

### Before (mutable task)
```
QuAcqTask(DiagnosisTask):
  # Inherited (immutable): set_kb, assumptions, set_b, set_c, negation_map
  # Mutable (REMOVE):
  bias: Set[int]           → use set_c (inherited)
  learned_kb: List[int]    → move to algorithm local
  n_queries: int           → move to algorithm local
  query_history: List      → move to algorithm local
  # Mutation methods (REMOVE):
  add_to_kb()              → algorithm does learned_kb.append()
  remove_from_bias()       → algorithm does remaining_bias -= set(...)
  record_query()           → algorithm does query_history.append()
  clone()                  → no longer needed (task is immutable)
```

### After (immutable task)
```
QuAcqTask(DiagnosisTask):
  # Inherited: set_kb, assumptions, set_b, set_c (=bias IDs), negation_map
  # Immutable data:
  background_clauses: List[List[int]]
  feature_ids: Dict[str, int]
  id_to_feature: Dict[int, str]
  constraint_clauses: Dict[int, List[List[int]]]
  negated_clauses: Dict[int, List[List[int]]]
  # Read-only helpers (stay):
  config_to_assumptions(), partial_config_to_assumptions()
  model_to_config(), get_constraints_with_scope()
  violates_clauses() (static)
  get_kb_clauses(learned_kb)  ← NEW signature
```

## Related Code Files

### Modify
- `conacq/algorithms/quacq/task_preparation.py` (lines 29-193, 195-263)

### Reference (read-only in this phase)
- `explanation/models/task_preparation.py` — DiagnosisTask base class

## Implementation Steps

### Step 1: Remove mutable fields from QuAcqTask (lines 50-75)

In `conacq/algorithms/quacq/task_preparation.py`:

**Delete** these field declarations (lines 50-75):
```python
bias: Set[int] = field(default_factory=set)          # line 51
learned_kb: List[int] = field(default_factory=list)   # line 54
n_queries: int = 0                                     # line 72
query_history: List[Tuple[...]] = field(...)          # line 75
```

### Step 2: Remove mutation methods (lines 84-97)

**Delete** these methods from QuAcqTask:
- `add_to_kb()` (lines 84-87)
- `remove_from_bias()` (lines 89-91)
- `record_query()` (lines 93-97)

### Step 3: Remove clone() method (lines 172-192)

**Delete** the entire `clone()` method. Task is now immutable — no need to clone.

### Step 4: Update get_kb_clauses() to accept parameter (lines 77-82)

Change from:
```python
def get_kb_clauses(self) -> List[List[int]]:
    clauses = []
    for aid in self.learned_kb:
        clauses.extend(self.constraint_clauses.get(aid, []))
    return clauses
```

To:
```python
def get_kb_clauses(self, learned_kb: List[int]) -> List[List[int]]:
    """Get raw CNF clauses for given learned KB assumption IDs."""
    clauses = []
    for aid in learned_kb:
        clauses.extend(self.constraint_clauses.get(aid, []))
    return clauses
```

### Step 5: Update QuAcqTaskPreparation.prepare() (line 245-246)

Change bias assignment from `result.bias` to `result.set_c`:

**Before** (line 245-246):
```python
result.bias = set(
    result.assumptions[bias_start_pos::_ASSUMPTION_PAIR_STRIDE])
```

**After**:
```python
result.set_c = list(
    result.assumptions[bias_start_pos::_ASSUMPTION_PAIR_STRIDE])
```

Note: `set_c` is `List[int]` (from DiagnosisTask), not `Set[int]`. This matches ConGenTask pattern.

### Step 6: Update constraint_clauses loop (line 249)

Change `result.bias` to iterate `result.set_c`:

**Before** (line 249):
```python
for aid in result.bias:
```

**After**:
```python
for aid in result.set_c:
```

### Step 7: Update docstring (lines 30-48)

Update the class docstring to reflect immutable fields. Remove references to `bias`, `learned_kb`, `n_queries`, `query_history`. Add note that `set_c` holds bias constraint assumption IDs.

### Step 8: Remove unused imports

Remove `Tuple` from imports (line 12) if no longer used after removing `query_history` type annotation.

## Todo List

- [ ] Delete `bias`, `learned_kb`, `n_queries`, `query_history` field declarations
- [ ] Delete `add_to_kb()`, `remove_from_bias()`, `record_query()` methods
- [ ] Delete `clone()` method
- [ ] Change `get_kb_clauses()` to accept `learned_kb` parameter
- [ ] Change `QuAcqTaskPreparation.prepare()` to assign `set_c` instead of `bias`
- [ ] Update iteration from `result.bias` to `result.set_c` in preparation
- [ ] Update class docstring
- [ ] Clean up unused imports

## Success Criteria

- QuAcqTask has no mutable fields (only immutable data + inherited DiagnosisTask fields)
- `set_c` populated with bias assumption IDs after preparation
- `constraint_clauses` and `negated_clauses` still populated correctly
- Module compiles without syntax errors

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tests fail after field removal | Expected | Phase 3 updates tests |
| QueryGenerator accesses task.bias | High | Phase 2 changes to task.set_c |
| FindScope/FindC access task.bias | High | Phase 2 threads remaining_bias |
| Runner accesses task.bias | Medium | Phase 3 updates runner |

## Next Steps

Phase 2 wires up the algorithm to use local mutable state instead of task mutation.
