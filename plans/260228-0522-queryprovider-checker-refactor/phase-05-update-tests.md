---
title: "Phase 5: Update Tests"
status: complete
priority: P1
effort: 25m
created: 2026-02-28
completed: 2026-02-28
---

# Phase 5: Update Tests

## Context Links

- [Phase 2: QueryProvider refactor](phase-02-refactor-query-provider.md)
- Source: `tests/test_quacq.py`

## Overview

- **Priority**: P1
- **Status**: complete
- Update TestQueryProvider and TestQueryProviderWithQuAcqTask to use new signatures
- Ensure tests pass checker + model to QueryProvider

## Key Insights

- `TestQueryProvider.test_provider_creation` — no change (no checker/model needed for creation)
- `TestQueryProvider.test_generate_from_sat` — needs checker + model, new signature
- `TestQueryProviderPoolFiltering.test_pool_filtering_skips_invalid` — needs checker + model
- `TestQueryProviderWithQuAcqTask.test_generate_from_sat_with_quacq_task` — needs checker + model
- Tests that only test creation/pool state don't need changes

## Requirements

- All existing tests pass
- Tests exercise checker-backed QueryProvider path
- No mocks — use real checkers (NonIncrementalPySATChecker or CheckerFactory)

## Related Code Files

- **Modify**: `tests/test_quacq.py`

## Implementation Steps

### 1. TestQueryProvider.test_generate_from_sat (lines 191-211)

**Before:**
```python
def test_generate_from_sat(self, prepared_model):
    task = prepared_model.task
    provider = QueryProvider()
    remaining_bias = set(task.set_c)
    kb_clauses = get_kb_clauses([], task.constraint_clauses)
    query, tested_c_id = provider.generate_from_sat(
        remaining_bias=remaining_bias,
        learned_kb=[],
        kb_clauses=kb_clauses,
        negated_clauses=task.negated_clauses,
        bg_clauses=task.background_clauses,
        feature_ids=task.feature_ids,
        id_to_feature=task.id_to_feature)
```

**After:**
```python
def test_generate_from_sat(self, prepared_model, checker):
    task = prepared_model.task
    provider = QueryProvider(checker=checker, model=prepared_model)
    remaining_bias = set(task.set_c)
    query, tested_c_id = provider.generate_from_sat(
        remaining_bias=remaining_bias,
        learned_kb=[],
        set_b=task.set_b,
        negation_map=task.negation_map,
        id_to_feature=task.id_to_feature)
```

### 2. TestQueryProviderPoolFiltering.test_pool_filtering_skips_invalid (lines 705-715)

This test uses minimal data (no model/checker). Two options:

**Option A (preferred)**: Create minimal checker + model for test.
This is complex. Better approach: skip this test or adjust to use a prepared_model fixture.

**Option B**: Keep test with old API if we add a backward-compat path.

**Recommended**: Refactor to use prepared_model fixture with a real pool:

```python
def test_pool_filtering_skips_invalid(self, prepared_model, checker):
    """Pool examples not satisfying KB+BG are skipped."""
    task = prepared_model.task
    features = list(task.feature_ids.keys())
    # All-false config almost certainly invalid (root must be true)
    invalid_config = {f: False for f in features}
    provider = QueryProvider(pool=[invalid_config], seed=42,
                             checker=checker, model=prepared_model)
    query, c_id = provider.generate_from_pool(
        remaining_bias=set(task.set_c),
        learned_kb=[],
        set_b=task.set_b,
        constraint_clauses=task.constraint_clauses,
        feature_ids=task.feature_ids)
    assert query is None  # filtered out
    assert provider.pool_exhausted is True
```

### 3. TestQueryProviderWithQuAcqTask.test_generate_from_sat_with_quacq_task (lines 612-631)

**Before:**
```python
def test_generate_from_sat_with_quacq_task(self, prepared_model):
    task = prepared_model.task
    provider = QueryProvider()
    remaining_bias = set(task.set_c)
    kb_clauses = get_kb_clauses([], task.constraint_clauses)
    query, tested_c_id = provider.generate_from_sat(
        remaining_bias=remaining_bias,
        learned_kb=[],
        kb_clauses=kb_clauses,
        negated_clauses=task.negated_clauses,
        bg_clauses=task.background_clauses,
        feature_ids=task.feature_ids,
        id_to_feature=task.id_to_feature)
```

**After:**
```python
def test_generate_from_sat_with_quacq_task(self, prepared_model, checker):
    task = prepared_model.task
    provider = QueryProvider(checker=checker, model=prepared_model)
    remaining_bias = set(task.set_c)
    query, tested_c_id = provider.generate_from_sat(
        remaining_bias=remaining_bias,
        learned_kb=[],
        set_b=task.set_b,
        negation_map=task.negation_map,
        id_to_feature=task.id_to_feature)
```

### 4. Verify tests that don't need changes

These should remain unchanged:
- `test_provider_creation` — no checker needed for construction
- `test_provider_with_pool` — just tests pool state
- `test_pool_exhausted_when_empty` — just tests pool state

### 5. Remove unused imports

If `get_kb_clauses` no longer used in tests (check all uses), remove from imports. It's still used in `TestQuAcqTask.test_get_kb_clauses` and `TestSatUtils.test_get_kb_clauses`, so keep the import.

### 6. Run full test suite

```bash
PYTHONPATH=. pytest tests/test_quacq.py -v
PYTHONPATH=. pytest tests/ -v
```

## Todo List

- [ ] Update test_generate_from_sat to use checker + new signature
- [ ] Update test_pool_filtering_skips_invalid to use checker + model
- [ ] Update test_generate_from_sat_with_quacq_task to use checker + new signature
- [ ] Verify unchanged tests still pass
- [ ] Run full suite: `PYTHONPATH=. pytest tests/ -v`

## Success Criteria

- All tests pass in both incremental and non-incremental modes
- No ad-hoc solver creation in test code for QueryProvider tests
- Tests exercise real checker path (not mocked)

## Risk Assessment

- **Medium**: Pool filtering test needs real model/checker, may need fixture dependency
- **Low**: SAT generation tests are straightforward signature updates

## Security Considerations

N/A.

## Next Steps

All phases complete. Run final validation: `PYTHONPATH=. pytest tests/ -v`.
