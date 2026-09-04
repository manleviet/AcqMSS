# Phase 3: Update Construction Sites and Tests

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 2](phase-02-rewrite-generator.md)

## Overview
- **Priority**: High (required for compilation)
- **Status**: Complete
- **Description**: Update all DiscriminatingGenerator construction sites to use new DI constructor

## Related Code Files
- **Modify**: `conacq/runners/quacq_runner.py` (2 construction sites)
- **Modify**: `conacq/algorithms/quacq/__init__.py` (example code)
- **Modify**: `tests/test_quacq.py` (test construction)

## Implementation Steps

### 3.1 Update quacq_runner.py — oracle mode (~line 236)

**Current:**
```python
discrim_gen = DiscriminatingGenerator(
    background_clauses=task.background_clauses,
    constraint_clauses=task.constraint_clauses,
    negated_clauses=task.negated_clauses,
    id_to_feature=task.id_to_feature,
    solver_name=self.solver_name)
```

**New:**
```python
discrim_gen = DiscriminatingGenerator(
    checker=checker,
    model=self.model,
    root_assumption=task.set_b[0])
```

### 3.2 Update quacq_runner.py — example_first mode (~line 265)

**Current:**
```python
discrim_gen = DiscriminatingGenerator(
    background_clauses=task.background_clauses,
    constraint_clauses=task.constraint_clauses,
    negated_clauses=task.negated_clauses,
    id_to_feature=task.id_to_feature,
    solver_name=self.solver_name)
```

**New:**
```python
discrim_gen = DiscriminatingGenerator(
    checker=checker,
    model=self.model,
    root_assumption=task.set_b[0])
```

Note: `checker` is already available in both methods — created before discrim_gen.

### 3.3 Update quacq/__init__.py (~line 29)

**Current:**
```python
discrim_gen = DiscriminatingGenerator(
    background_clauses=task.background_clauses,
    constraint_clauses=task.constraint_clauses,
    negated_clauses=task.negated_clauses,
    id_to_feature=task.id_to_feature)
```

**New:**
```python
discrim_gen = DiscriminatingGenerator(
    checker=checker,
    model=model,
    root_assumption=task.set_b[0])
```

Note: `checker` created at line 34 — may need to move creation before discrim_gen.

### 3.4 Update tests/test_quacq.py

Find DiscriminatingGenerator construction in test setup. Update to pass checker, model, root_assumption instead of raw data dicts. The test already creates checker via `CheckerFactory.create_from_model(model)`.

## Todo
- [x] Update quacq_runner.py oracle mode construction
- [x] Update quacq_runner.py example_first mode construction
- [x] Update __init__.py example code
- [x] Update test_quacq.py construction
- [x] Run `PYTHONPATH=. pytest tests/test_quacq.py -v` — all tests pass
- [x] Verify no unused imports remain (background_clauses, negated_clauses etc.)

## Success Criteria
- All 3 construction sites use new `(checker, model, root_assumption)` signature
- `PYTHONPATH=. pytest tests/test_quacq.py -v` passes
- No references to old constructor args (background_clauses, constraint_clauses, negated_clauses, id_to_feature, solver_name) in DiscriminatingGenerator usage
