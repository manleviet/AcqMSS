# Phase 03: Update Tests and Docs

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-remove-from-algorithm.md), [Phase 02](phase-02-update-runner.md)

## Overview
- **Priority:** High (validation)
- **Status:** completed
- **Description:** Remove `description_provider=` from test learn() calls, update assertions, fix __init__.py docstring

## Key Insights
- 4 test call sites pass `description_provider=` to `learn()` (lines 235, 303, 558, 606)
- Tests asserting `result.kb_constraints` after direct `learn()` calls will now get `[]` — update to verify via `model.resolve_kb()` instead
- `test_description_provider` (line 509) and `test_resolve_kb` (line 518) remain unchanged — they test model, not algorithm
- `__init__.py` docstring example includes `description_provider=model.description_provider` — remove it

## Related Code Files

### Modify
- `tests/test_quacq.py` — 4 learn() call sites
- `conacq/algorithms/quacq/__init__.py` — docstring example (line 42)

## Implementation Steps

### 1. Update test_quacq_learn_with_limit (line 233-235)
- Remove `description_provider=prepared_model.description_provider`
- Assertion `isinstance(result.kb_constraints, list)` (line 240) still valid (empty list)

### 2. Update test in profiler section (line 301-303)
- Remove `description_provider=model.description_provider`

### 3. Update test_quacq_result_has_assumption_ids (line 556-558)
- Remove `description_provider=prepared_model.description_provider`
- Lines 564-566 assert `kb_constraints` are strings — change to verify via model:
  ```python
  if result.kb_assumption_ids:
      names, _ = prepared_model.resolve_kb(result.kb_assumption_ids)
      for name in names:
          assert isinstance(name, str)
  ```

### 4. Update test_result_has_dual_representation (line 604-606)
- Remove `description_provider=prepared_model.description_provider`
- Line 609 asserts `len(kb_constraints) == len(kb_assumption_ids)` — update to verify via model:
  ```python
  if result.kb_assumption_ids:
      names, _ = prepared_model.resolve_kb(result.kb_assumption_ids)
      assert len(names) == len(result.kb_assumption_ids)
  ```

### 5. Update __init__.py docstring (line 42)
- Remove `mode='oracle', description_provider=model.description_provider)` → `mode='oracle')`

## Todo List
- [ ] Remove `description_provider=` from 4 test learn() calls
- [ ] Update assertions that check `result.kb_constraints` after direct learn() — verify via model.resolve_kb() instead
- [ ] Update `__init__.py` docstring example
- [ ] Run full test suite: `PYTHONPATH=. pytest tests/ -v`

## Success Criteria
- All tests pass
- No `description_provider` in any `learn()` call across codebase
- `__init__.py` example doesn't mention `description_provider`

## Risk Assessment
- **Low:** Mechanical changes, same assertions via different path
- Tests for `model.description_provider` and `model.resolve_kb()` remain untouched
