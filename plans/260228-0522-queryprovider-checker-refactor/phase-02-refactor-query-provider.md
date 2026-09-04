---
title: "Phase 2: Refactor QueryProvider"
status: complete
priority: P1
effort: 30m
created: 2026-02-28
completed: 2026-02-28
---

# Phase 2: Refactor QueryProvider

## Context Links

- [Phase 1: get_model()](phase-01-checker-get-model.md)
- [Brainstorm](../reports/brainstorm-260228-0522-queryprovider-checker-refactor.md)
- Source: `conacq/example_generators/query_provider.py`

## Overview

- **Priority**: P1 (core refactoring)
- **Status**: complete
- Replace `_satisfies_formula` with `checker.is_consistent()`
- Replace `_try_generate_for_constraint` with `checker.is_consistent()` + `checker.get_model()`
- Update signatures to use assumption IDs instead of raw clauses

## Key Insights

- `checker.is_consistent(set_c)` enables set_c, disables rest of assumption universe
- For pool filtering: `set_c = learned_kb + set_b + config_assumptions` (Part 4 IDs)
- For SAT gen: `set_c = learned_kb + set_b + [negation_map[c_id]]`
- `model.config_to_assumptions(config)` converts feature config to Part 4 assumption IDs
- Condition 2 (`violates_clauses`) stays as boolean eval (faster than SAT)

## Requirements

- Add `model: QuAcqModel` and `checker: ConsistencyChecker` to `__init__`
- Both optional for backward compat (discriminating_generator still uses raw solvers)
- Remove `pysat.solvers` import when dead code deleted

## Architecture

```
QueryProvider.__init__(solver_name, pool, seed, checker, model, profiler)
                                               ^^^^^^  ^^^^^  NEW

generate_from_pool(remaining_bias, learned_kb, set_b, constraint_clauses, feature_ids)
                                   ^^^^^^^^^^  ^^^^^  replaces kb_clauses+bg_clauses

generate_from_sat(remaining_bias, learned_kb, set_b, negation_map, id_to_feature)
                                  ^^^^^^^^^^  ^^^^^  ^^^^^^^^^^^^  new params

generate(remaining_bias, learned_kb, set_b, negation_map, constraint_clauses, feature_ids, id_to_feature)
```

## Related Code Files

- **Modify**: `conacq/example_generators/query_provider.py`

## Implementation Steps

### 1. Update __init__ — add checker + model

**Before:**
```python
def __init__(self, solver_name: str = 'glucose4',
             pool: Optional[List[Dict[str, bool]]] = None,
             seed: Optional[int] = None,
             profiler_instance: Optional[AbstractProfiler] = None) -> None:
    self.solver_name = solver_name
```

**After:**
```python
def __init__(self, solver_name: str = 'glucose4',
             pool: Optional[List[Dict[str, bool]]] = None,
             seed: Optional[int] = None,
             checker=None,
             model=None,
             profiler_instance: Optional[AbstractProfiler] = None) -> None:
    self.solver_name = solver_name
    self.checker = checker  # ConsistencyChecker (optional)
    self.model = model      # QuAcqModel (optional, for config_to_assumptions)
```

Type hints use forward refs or TYPE_CHECKING to avoid circular imports.

### 2. Refactor generate_from_pool — new signature + checker

**Before:**
```python
def generate_from_pool(self, remaining_bias, kb_clauses, bg_clauses,
                       constraint_clauses, feature_ids):
    formula = kb_clauses + bg_clauses
    ...
    assumptions = config_to_assumptions(e, feature_ids)
    if not self._satisfies_formula(formula, assumptions):
        continue
```

**After:**
```python
def generate_from_pool(self, remaining_bias: set,
                       learned_kb: List[int],
                       set_b: List[int],
                       constraint_clauses: Dict[int, List[List[int]]],
                       feature_ids: Dict[str, int]) -> Tuple[...]:
    while self._pool_index < len(self._pool):
        e = self._pool[self._pool_index]
        self._pool_index += 1

        # Condition 1: config satisfies C_L + BG (via checker)
        config_assumptions = self.model.config_to_assumptions(e)
        set_c = learned_kb + set_b + config_assumptions
        if not self.checker.is_consistent(set_c):
            continue

        # Condition 2: violates >=1 constraint in remaining_bias (boolean eval)
        assumptions_list = config_to_assumptions(e, feature_ids)
        assignment = {abs(lit): lit > 0 for lit in assumptions_list}
        for c_id in remaining_bias:
            clauses = constraint_clauses.get(c_id)
            if clauses and violates_clauses(clauses, assignment):
                return e, c_id

    return None, None
```

### 3. Refactor generate_from_sat — new signature + checker + get_model

**Before:**
```python
def generate_from_sat(self, remaining_bias, learned_kb, kb_clauses,
                      negated_clauses, bg_clauses, feature_ids,
                      id_to_feature, n_bg=0):
    for c_id in remaining_bias:
        neg_c_clauses = negated_clauses.get(c_id)
        ...
        query_result = self._try_generate_for_constraint(
            kb_clauses=kb_clauses, bg_clauses=bg_clauses,
            neg_c_clauses=neg_c_clauses, ...)
```

**After:**

```python
def generate_from_sat(self, remaining_bias: set,
                      learned_kb: List[int],
                      set_b: List[int],
                      negation_map: Dict[int, int],
                      id_to_feature: Dict[int, str]) -> Tuple[...]:
    for c_id in remaining_bias:
        neg_aid = negation_map.get(c_id)
        if neg_aid is None:
            logging.warning('No negation for constraint %s, skipping', c_id)
            continue

        set_c = learned_kb + set_b + [neg_aid]
        if self.checker.is_consistent(set_c):
            model_lits = self.checker.get_model()
            config = self.model_to_config(model_lits, id_to_feature)
            return config, c_id

    return None, None
```

### 4. Refactor generate() — combine both

**After:**
```python
def generate(self, remaining_bias: set,
             learned_kb: List[int],
             set_b: List[int],
             negation_map: Dict[int, int],
             constraint_clauses: Dict[int, List[List[int]]],
             feature_ids: Dict[str, int],
             id_to_feature: Dict[int, str]) -> Tuple[...]:
    if not self.pool_exhausted:
        result = self.generate_from_pool(
            remaining_bias, learned_kb, set_b,
            constraint_clauses, feature_ids)
        if result[0] is not None:
            return result

    return self.generate_from_sat(
        remaining_bias, learned_kb, set_b,
        negation_map, id_to_feature)
```

### 5. Delete dead methods

- Delete `_satisfies_formula()`
- Delete `_try_generate_for_constraint()`
- Remove `from pysat.solvers import Solver` (no longer needed)

### 6. Keep _model_to_config unchanged

Already correct — converts SAT model literals to feature config dict.

## Todo List

- [ ] Add checker + model to __init__
- [ ] Refactor generate_from_pool signature + body
- [ ] Refactor generate_from_sat signature + body
- [ ] Refactor generate() signature + body
- [ ] Delete _satisfies_formula
- [ ] Delete _try_generate_for_constraint
- [ ] Remove pysat.solvers import
- [ ] Run: `PYTHONPATH=. pytest tests/test_quacq.py -v`

## Success Criteria

- No ad-hoc Solver() creation in QueryProvider
- All SAT checks go through checker.is_consistent()
- Condition 2 still uses boolean eval (not SAT)
- `_model_to_config` reused as-is

## Risk Assessment

- **Semantic correctness**: `is_consistent(learned_kb + set_b + config_assumptions)` must activate correct constraints. The checker enables set_c and disables complement in assumption universe. learned_kb + set_b + config_assumptions are all assumption IDs in the universe.
- **get_model() lifecycle**: Must call immediately after `is_consistent()` returns True, before any other checker call.

## Security Considerations

N/A.

## Next Steps

Phase 3: Update QuAcq.learn() call sites to pass new params.
