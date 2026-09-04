# Phase 2: Refactor QueryGenerator

## Context Links
- [Plan overview](plan.md)
- [QuAcq Internals research](research/researcher-01-quacq-internals.md)
- Source: `conacq/example_generators/query_generator.py` (187 LOC)
- Consumers: `QuAcq.learn()`, `QuAcq.learn_from_examples()`, `QuAcqRunner._run_example_mode()`

## Overview
- **Priority:** High (blocks Phase 3)
- **Status:** complete
- **Description:** Refactor `generate()` and `generate_with_priority()` to accept raw data params instead of `task` object.

## Key Insights
- `generate()` accesses from task: `set_b` (len only for logging), `get_kb_clauses(kb)`, `negated_clauses`, `feature_ids`, `id_to_feature`, BG clauses via `get_bg_clauses(task)`
- `_try_generate_for_constraint` already accepts raw data — no change needed
- Module-level `_get_negated_clauses(task, c_id)` and `_get_clause_map_for_priority(task, c_id)` are duck-typing shims for both `QuAcqTask` and `InteractiveTask` — these get replaced by direct dict access
- `get_bg_clauses` import from `_task_compat` can be removed
- `_model_to_config` already inlined in this file — stays as-is

## Requirements

### Functional
- `generate()` signature: accept `negated_clauses`, `feature_ids`, `id_to_feature`, `bg_clauses`, `kb_clauses` directly instead of `task`
- `generate_with_priority()` same approach
- Remove `_get_negated_clauses()` and `_get_clause_map_for_priority()` module-level shims
- Remove `get_bg_clauses` import from `_task_compat`

### Non-Functional
- File stays under 200 LOC
- Type hints on all public methods
- `_try_generate_for_constraint` unchanged (already clean)

## Architecture

### Before
```python
def generate(self, task, remaining_bias, learned_kb):
    kb_clauses = task.get_kb_clauses(kb)
    for c_id in bias:
        neg_c = _get_negated_clauses(task, c_id)
        self._try_generate_for_constraint(
            kb_clauses, get_bg_clauses(task), neg_c,
            task.feature_ids, task.id_to_feature)
```

### After
```python
def generate(self,
             remaining_bias: set,
             learned_kb: list,
             kb_clauses: List[List[int]],
             negated_clauses: Dict[int, List[List[int]]],
             bg_clauses: List[List[int]],
             feature_ids: Dict[str, int],
             id_to_feature: Dict[int, str],
             n_bg: int = 0,   # for logging (was len(task.set_b))
             ) -> Tuple[Optional[Dict[str, bool]], Any]:
    for c_id in remaining_bias:
        neg_c = negated_clauses.get(c_id)
        self._try_generate_for_constraint(
            kb_clauses, bg_clauses, neg_c,
            feature_ids, id_to_feature)
```

## Related Code Files
- **Modify:** `conacq/example_generators/query_generator.py`
- **Phase 3 updates callers:** `conacq/algorithms/quacq/quacq.py` (wires new signature)

## Implementation Steps

1. **Remove module-level shims**: Delete `_get_negated_clauses()` and `_get_clause_map_for_priority()` functions. Delete `from conacq.algorithms.quacq._task_compat import get_bg_clauses` import.

2. **Refactor `generate()` signature**:
   ```python
   def generate(self,
                remaining_bias: set,
                learned_kb: list,
                kb_clauses: List[List[int]],
                negated_clauses: Dict[int, List[List[int]]],
                bg_clauses: List[List[int]],
                feature_ids: Dict[str, int],
                id_to_feature: Dict[int, str],
                n_bg: int = 0,
                ) -> Tuple[Optional[Dict[str, bool]], Any]:
   ```

3. **Update `generate()` body**:
   - Replace `task.get_kb_clauses(kb)` -> use `kb_clauses` param directly
   - Replace `_get_negated_clauses(task, c_id)` -> `negated_clauses.get(c_id)`
   - Replace `get_bg_clauses(task)` -> `bg_clauses` param
   - Replace `task.feature_ids` -> `feature_ids` param
   - Replace `task.id_to_feature` -> `id_to_feature` param
   - Replace `len(task.set_b)` in logging -> `n_bg` param

4. **Refactor `generate_with_priority()` signature**: Same raw data params plus `priority_fn`. For priority function, pass `constraint_clauses` dict as additional param (replaces `_get_clause_map_for_priority`):
   ```python
   def generate_with_priority(self,
                              remaining_bias: set,
                              learned_kb: list,
                              kb_clauses: List[List[int]],
                              negated_clauses: Dict[int, List[List[int]]],
                              constraint_clauses: Dict[int, List[List[int]]],
                              bg_clauses: List[List[int]],
                              feature_ids: Dict[str, int],
                              id_to_feature: Dict[int, str],
                              priority_fn=None,
                              n_bg: int = 0,
                              ) -> Tuple[Optional[Dict[str, bool]], Any]:
   ```

5. **Update `generate_with_priority()` body**: Replace `_get_clause_map_for_priority(task, c_id)` -> `constraint_clauses.get(c_id, [])`. Delegate to `generate()` when `priority_fn is None` (passing through all raw params).

6. **Update docstrings**: Reflect new params. Remove references to "task".

7. **Keep `_try_generate_for_constraint` and `_model_to_config` unchanged** — already accept raw data.

8. **Keep `clause_count_priority` and `literal_count_priority` unchanged** — standalone functions.

## Todo List
- [ ] Delete `_get_negated_clauses()` module-level function
- [ ] Delete `_get_clause_map_for_priority()` module-level function
- [ ] Remove `_task_compat` import
- [ ] Refactor `generate()` to accept raw data params
- [ ] Refactor `generate_with_priority()` to accept raw data params
- [ ] Update all docstrings
- [ ] Verify file under 200 LOC
- [ ] Run `PYTHONPATH=. pytest tests/test_quacq.py -v` (expect failures until Phase 3)

## Success Criteria
- No `task` parameter anywhere in `QueryGenerator`
- No `_task_compat` import
- No module-level duck-typing shims
- `_try_generate_for_constraint` unchanged
- Type hints on all public methods

## Risk Assessment
- **Medium risk**: `generate()` is called from 3 places (QuAcq.learn, QuAcq.learn_from_examples, QuAcqRunner via learn_from_examples). All updated in Phase 3-4.
- **`generate_with_priority` risk**: Currently not called in production code (no priority_fn usage found). Low risk to refactor.
- **InteractiveTask compatibility**: Removing duck-typing shims means this generator no longer supports `InteractiveTask`. Acceptable — `InteractiveTask` was removed in earlier refactors.

## Next Steps
- Phase 3 wires new `generate()` signature from `QuAcq.learn()` by extracting raw data from flat params
