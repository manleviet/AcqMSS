from conacq.algorithms.quacq.quacq_model import _model_to_config

# Brainstorm: Replace _satisfies_formula in QueryProvider with ConsistencyChecker

## Problem Statement

`QueryProvider._satisfies_formula()` creates a **fresh PySAT solver per call** to check if a config satisfies KB+BG. Similarly, `_try_generate_for_constraint()` creates ad-hoc solvers for SAT query generation. This duplicates solver management already handled by `ConsistencyChecker`.

**Goal:** Replace ad-hoc solver usage in QueryProvider with `ConsistencyChecker`, passed from `QuacqRunner`.

## Current State

### _satisfies_formula (lines 100-109, query_provider.py)
```python
def _satisfies_formula(self, clauses, assumptions):
    solver = Solver(name=self.solver_name, bootstrap_with=clauses)
    try:
        return solver.solve(assumptions=assumptions)
    finally:
        solver.delete()
```
- Called from `generate_from_pool()` Condition 1: `formula = kb_clauses + bg_clauses`
- Feature-level assumptions (config assignment as literals)

### _try_generate_for_constraint (lines 174-188)
```python
all_clauses = kb_clauses + bg_clauses + neg_c_clauses
solver = Solver(name=self.solver_name, bootstrap_with=all_clauses)
# solve → get_model → config
```

### ConsistencyChecker.is_consistent(set_c)
- Takes **constraint assumption IDs** (not feature literals)
- `_compute_delta`: enables `set_c`, disables `self.assumptions \ set_c`
- Solver already has full KB loaded (bias + BG + assignment clauses)

## Key Finding: Assumption Universe

Assignment assumptions (Part 4) and negation assumptions ARE already in `task.assumptions` and `task.set_kb`:
```python
# task_preparation.py:104-105
result.set_kb.extend(bg_data.assignment_clauses)
result.assumptions.extend(bg_data.assignment_assumptions)
```

This means `checker.is_consistent()` can handle both:
- Config checking: via Part 4 assignment assumptions from `model.config_to_assumptions(config)`
- Negated constraint: via `negation_map[c_id]`

## Agreed Solution

### 1. QueryProvider.__init__ changes
- Add `model: QuAcqModel` (optional) — for `config_to_assumptions()`
- Add `checker: ConsistencyChecker` (optional) — replaces ad-hoc solvers
- Keep `solver_name` for fallback (discriminating generator still uses raw solvers)

### 2. generate_from_pool: Replace _satisfies_formula
**Before:**
```python
formula = kb_clauses + bg_clauses
assumptions = config_to_assumptions(e, feature_ids)  # feature literals
if not self._satisfies_formula(formula, assumptions): continue
```

**After:**
```python
config_assumptions = self.model.config_to_assumptions(e)  # Part 4 assumption IDs
set_c = learned_kb + set_b + config_assumptions
if not self.checker.is_consistent(set_c): continue
```

**Signature change:** `generate_from_pool(remaining_bias, learned_kb, set_b, constraint_clauses, feature_ids)`
- Replaces `kb_clauses` + `bg_clauses` with `learned_kb` (List[int]) + `set_b` (List[int])
- `feature_ids` still needed for Condition 2 (`violates_clauses` boolean eval — keep as-is, not SAT)

### 3. generate_from_sat: Replace _try_generate_for_constraint
**Before:** Creates solver with `kb_clauses + bg_clauses + neg_c_clauses`, extracts model

**After:**

```python
set_c = learned_kb + set_b + [negation_map[c_id]]
if self.checker.is_consistent(set_c):
    model = self.checker.get_model()  # NEW method
    config = _model_to_config(model, id_to_feature)
    return config, c_id
```

**Signature change:** `generate_from_sat(remaining_bias, learned_kb, set_b, negation_map, id_to_feature)`
- Replaces raw clause params with assumption IDs
- Adds `negation_map` param

### 4. ConsistencyChecker: Add get_model()
New abstract method: `get_model() -> Optional[List[int]]`

| Implementation | Approach |
|---|---|
| `IncrementalPySATChecker` | `self.solver.get_model()` — solver persists, model available after solve |
| `NonIncrementalPySATChecker` | Cache model before `solver.delete()` in `is_consistent()` |
| `SAT4JChecker` | Parse model from subprocess output, cache it |

### 5. QuacqRunner: Pass checker + model
```python
# Oracle mode
query_provider = QueryProvider(self.solver_name, checker=self.checker,
                               model=self.model, profiler_instance=profiler)

# Example mode
query_provider = QueryProvider(self.solver_name, pool=mixed_examples,
                               seed=shuffle_seed, checker=self.checker,
                               model=self.model, profiler_instance=profiler)
```

### 6. QuAcq.learn(): Update call sites
```python
# generate_from_pool
query, tested_c_id = self.query_provider.generate_from_pool(
    remaining_bias=remaining_bias, learned_kb=learned_kb,
    set_b=set_b, constraint_clauses=constraint_clauses,
    feature_ids=feature_ids)

# generate_from_sat
query, tested_c_id = self.query_provider.generate_from_sat(
    remaining_bias=remaining_bias, learned_kb=learned_kb,
    set_b=set_b, negation_map=negation_map,
    id_to_feature=id_to_feature)
```

### 7. generate(): Update unified method
Signature combines both pools: `generate(remaining_bias, learned_kb, set_b, negation_map, constraint_clauses, feature_ids, id_to_feature)`

### 8. Delete dead code
- Remove `_satisfies_formula()` method
- Remove `_try_generate_for_constraint()` method
- `solver_name` stays (may be used elsewhere or as fallback)

## Benefits
- **DRY**: No ad-hoc solver creation; reuses checker infrastructure
- **Performance**: Incremental checker reuses solver across calls (no bootstrap overhead)
- **Consistency**: All SAT ops go through checker — single point for profiling, counting
- **Architecture**: QueryProvider depends on checker abstraction, not raw PySAT

## Risks
- **Semantic correctness**: `is_consistent(set_c)` enables set_c and disables everything else. Must ensure `learned_kb + set_b + config_assumptions` correctly activates all needed constraints.
- **Condition 2 still uses raw boolean eval**: `violates_clauses()` stays as-is (faster than SAT for simple clause violation checking).
- **get_model() lifecycle**: NonIncremental checker must cache model before solver deletion. Model is only valid until next `is_consistent()` call.

## Files to Modify
| File | Change |
|---|---|
| `explanation/operations/algorithms/checker.py` | Add abstract `get_model()`, implement in all 3 checkers |
| `conacq/example_generators/query_provider.py` | Add model/checker to init, replace _satisfies_formula and _try_generate, update signatures |
| `conacq/algorithms/quacq/quacq.py` | Update call sites in `learn()` |
| `conacq/runners/quacq_runner.py` | Pass checker + model to QueryProvider |
| `tests/test_quacq.py` | Update TestQueryProvider tests |

## Unresolved Questions
1. Should `discriminating_generator.py` (same pattern: ad-hoc solver + get_model) also be refactored? — Out of scope for now.
2. Should `solver_name` be removed from QueryProvider if checker replaces all solver usage? — Keep for now, remove later if truly unused.
