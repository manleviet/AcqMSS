# Phase 1: Refactor DiscriminatingGenerator

## Context Links
- [Plan overview](plan.md)
- [QuAcq Internals research](research/researcher-01-quacq-internals.md)
- Source: `conacq/algorithms/quacq/discriminating_generator.py` (66 LOC)
- Consumer: `findc.py` (`_narrow_with_generator` calls `generator.generate(c_i, c_j, learned_kb, scope)`)
<!-- Updated: Validation Session 1 - discrim_gen required in for_oracle(), no auto-create -->

## Overview
- **Priority:** High (blocks Phase 3)
- **Status:** complete
- **Description:** Remove `QuAcqTask` dependency from `DiscriminatingGenerator`. Accept raw data params instead.

## Key Insights
- `__init__` currently stores full `self._task` — only uses 5 fields/methods
- Fields accessed: `background_clauses`, `constraint_clauses`, `negated_clauses`, `model_to_config()`, `_get_constraint_vars()`
- `model_to_config()` and `_get_constraint_vars()` are pure computation on `id_to_feature` and `constraint_clauses` — can be inlined or passed as data
- `generate()` signature (`c_i, c_j, learned_kb, scope`) stays unchanged externally
- FindC passes generator as opaque object — only calls `.generate()`

## Requirements

### Functional
- `__init__` accepts raw data: `background_clauses`, `constraint_clauses`, `negated_clauses`, `id_to_feature`, `solver_name`
- No import of `QuAcqTask` in this file
- `generate()` signature unchanged: `(c_i, c_j, learned_kb, scope) -> Optional[Dict[str, bool]]`
- Inline `model_to_config` and `_get_constraint_vars` logic using stored raw data

### Non-Functional
- File stays under 80 LOC
- Type hints on all public methods

## Architecture

### Before
```
DiscriminatingGenerator.__init__(task: QuAcqTask, solver_name)
    self._task = task  # stores full task
```

### After
```
DiscriminatingGenerator.__init__(
    background_clauses: List[List[int]],
    constraint_clauses: Dict[int, List[List[int]]],
    negated_clauses: Dict[int, List[List[int]]],
    id_to_feature: Dict[int, str],
    solver_name: str = 'glucose4'
)
```

## Related Code Files
- **Modify:** `conacq/algorithms/quacq/discriminating_generator.py`
- **No change:** `conacq/algorithms/quacq/findc.py` (calls `.generate()` with same args)

## Implementation Steps

1. **Replace `__init__` params**: Remove `task: QuAcqTask`. Add `background_clauses`, `constraint_clauses`, `negated_clauses`, `id_to_feature`, `solver_name`. Store each as `self._<field>`.

2. **Remove `QuAcqTask` import**: Delete `from .task_preparation import QuAcqTask`.

3. **Update `generate()` body**: Replace `self._task.background_clauses` -> `self._background_clauses`. Replace `self._task.constraint_clauses.get(c_i, [])` -> `self._constraint_clauses.get(c_i, [])`. Replace `self._task.negated_clauses.get(c_j, [])` -> `self._negated_clauses.get(c_j, [])`. Replace `self._task.model_to_config(model)` -> `self._model_to_config(model)`.

4. **Inline `_model_to_config`**: Add private method:
   ```python
   def _model_to_config(self, model: List[int]) -> Dict[str, bool]:
       config = {}
       for lit in model:
           var = abs(lit)
           if var in self._id_to_feature:
               config[self._id_to_feature[var]] = lit > 0
       return config
   ```

5. **Inline `_get_constraint_vars` in `_get_learned_clauses_in_scope`**: Replace `self._task._get_constraint_vars(c_id)` with inline logic:
   ```python
   def _get_constraint_vars(self, assumption_id: int) -> set:
       clauses = self._constraint_clauses.get(assumption_id, [])
       c_vars = set()
       for clause in clauses:
           for lit in clause:
               var = abs(lit)
               if var in self._id_to_feature:
                   c_vars.add(self._id_to_feature[var])
       return c_vars
   ```

6. **Update docstrings**: Reflect new param types in class and method docstrings.

7. **Verify LOC**: Target ~80 LOC (was 66, adding ~15 for inlined helpers).

## Todo List
- [ ] Replace `__init__` signature with raw data params
- [ ] Remove `QuAcqTask` import
- [ ] Update `generate()` to use `self._*` fields
- [ ] Add `_model_to_config()` private method
- [ ] Add `_get_constraint_vars()` private method
- [ ] Update docstrings
- [ ] Run `PYTHONPATH=. pytest tests/test_quacq.py -v` (expect failures until Phase 3 wires new constructor)

## Success Criteria
- No `QuAcqTask` import in `discriminating_generator.py`
- `generate()` returns same results given same data
- File under 100 LOC
- Type hints on all public methods

## Risk Assessment
- **Low risk**: `generate()` external signature unchanged; FindC doesn't need changes
- **Callers break temporarily**: `QuAcq.learn()` creates `DiscriminatingGenerator(task, ...)` — fixed in Phase 3

## Next Steps
- Phase 3 will update `DiscriminatingGenerator(...)` construction in `QuAcq.learn()` to pass raw data extracted from flat params
