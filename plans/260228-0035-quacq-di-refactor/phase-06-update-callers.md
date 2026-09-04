# Phase 6: Update Callers

## Context Links
- [Plan overview](plan.md)
- [Callers research](research/researcher-02-callers-tests.md)
- Depends on: Phase 5 (new QuAcq API)
<!-- Updated: Validation Session 1 - Renumbered from Phase 4 -->

## Overview
- **Priority:** High (makes code compile again)
- **Status:** complete
- **Description:** Update `QuAcqRunner` and `test_quacq.py` to use new QuAcq DI constructor and single `learn()` with flat params.

## Key Insights
- Runner constructs `QuAcq(solver_name, profiler)` per run → switch to factories with DI
- Runner has `self.model.task` with all fields → extract flat data from task
- Tests construct `QuAcq()` zero-arg → update to `QuAcq(oracle)` or factories
- Per-run QuAcq construction confirmed (validation decision)

## Requirements

### Functional
- `QuAcqRunner.run()` extracts flat data from task, passes to `learn()`
- Runner constructs DI objects (QueryGenerator, DiscriminatingGenerator) and injects
- Tests updated to new constructor and learn() signature
- Helper function reduces param extraction duplication in tests

### Non-Functional
- No behavioral changes — same results for same inputs
- Test assertions unchanged

## Architecture

### QuAcqRunner — After
```python
# Oracle mode
task = self.model.task
query_gen = QueryGenerator(self.solver_name, profiler)
discrim_gen = DiscriminatingGenerator(
    background_clauses=task.background_clauses,
    constraint_clauses=task.constraint_clauses,
    negated_clauses=task.negated_clauses,
    id_to_feature=task.id_to_feature)
quacq = QuAcq.for_oracle(oracle, query_gen, discrim_gen, profiler=profiler)
result = quacq.learn(
    set_c=task.set_c, set_b=task.set_b, set_kb=task.set_kb,
    negation_map=task.negation_map, assumptions=task.assumptions,
    background_clauses=task.background_clauses,
    feature_ids=task.feature_ids, id_to_feature=task.id_to_feature,
    constraint_clauses=task.constraint_clauses,
    negated_clauses=task.negated_clauses,
    mode='oracle', max_queries=..., description_provider=...)
```

### Test helper
```python
def _learn_params_from_task(task):
    """Extract flat learn() params from QuAcqTask."""
    return dict(
        set_c=task.set_c, set_b=task.set_b, set_kb=task.set_kb,
        negation_map=task.negation_map, assumptions=task.assumptions,
        background_clauses=task.background_clauses,
        feature_ids=task.feature_ids, id_to_feature=task.id_to_feature,
        constraint_clauses=task.constraint_clauses,
        negated_clauses=task.negated_clauses,
    )
```

## Related Code Files
- **Modify:** `conacq/runners/quacq_runner.py`
- **Modify:** `tests/test_quacq.py`

## Implementation Steps

### QuAcqRunner

1. **Add imports**: QueryGenerator, DiscriminatingGenerator, ExampleProvider.

2. **Refactor `run()` method**: Extract flat data dict from task after `model.prepare()`.

3. **Refactor `_run_oracle_mode`**: Create QueryGenerator + DiscriminatingGenerator + `QuAcq.for_oracle()`, call `learn(**task_data, mode='oracle', ...)`.

4. **Refactor `_run_example_mode`**: Create ExampleProvider + optional QueryGenerator + DiscriminatingGenerator (if example_first), construct QuAcq appropriately, call `learn(**task_data, mode=mode, ...)`.

5. **Keep shuffle logic**: Shuffle `task.set_c` before extracting task_data.

### Tests

6. **Add `_learn_params_from_task` helper** at module level.

7. **Update test_quacq_creation**: `QuAcq(oracle)`.

8. **Update test_quacq_learn_with_limit**: `QuAcq.for_oracle(oracle, query_gen, discrim_gen)` + `learn(**params, mode='oracle', ...)`.

9. **Update test_quacq_empty_bias**: `QuAcq(oracle)` + minimal flat params.

10. **Update TestQuAcqWithAssumptionIDs**: Same pattern with helper.

11. **Update TestIntegration**: Same pattern.

12. **Update TestQueryGenerator tests**: `generate()` now takes raw params.

## Todo List
- [ ] Refactor QuAcqRunner._run_oracle_mode with DI
- [ ] Refactor QuAcqRunner._run_example_mode with DI
- [ ] Add _learn_params_from_task test helper
- [ ] Update all QuAcq construction in tests
- [ ] Update all learn() calls in tests
- [ ] Update QueryGenerator test calls
- [ ] Verify all assertions unchanged

## Success Criteria
- `PYTHONPATH=. pytest tests/test_quacq.py -v` passes all existing tests
- No `quacq.learn(task, ...)` or `learn_from_examples()` calls remain
- QuAcqRunner uses factory methods

## Risk Assessment
- **Medium risk**: Many call sites (11+ test methods, 2 runner methods). Mechanical transformation.
- **Shuffle timing**: Must shuffle before extracting task_data.

## Next Steps
- Phase 7 runs full test suite + adds new tests
