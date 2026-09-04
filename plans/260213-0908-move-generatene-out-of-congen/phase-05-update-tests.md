# Phase 5: Update Tests

## Context Links

- Tests: `tests/test_congen.py`
- All phases 1-4 must be complete before this phase

## Overview

- **Priority**: P1
- **Status**: completed
- **Description**: Update `test_congen.py` to match new flow. The `create_checker_and_task()` helper must run GenerateNE and merge results into task before creating the final checker. Also update `TestGenerateNE` to verify new `NEResult` fields.

## Key Insights

- `create_checker_and_task()` helper is used by all 3 `TestCONGEN` tests
- Fix the helper once, all CONGEN tests work
- `TestGenerateNE.test_generate_ne_empty` needs minor update (verify new fields)
- `TestACQMSS` and `TestReduce` tests don't use GenerateNE, unchanged

## Requirements

### Functional
- `create_checker_and_task()` returns checker + task with `set_ne` populated
- `TestGenerateNE` verifies `new_clauses` and `new_assumptions` in result

### Non-functional
- Test assertions unchanged (same KB results expected)
- Tests still run in both incremental and non-incremental modes

## Related Code Files

- **Modify**: `tests/test_congen.py`

## Implementation Steps

### Step 1: Update `create_checker_and_task()` helper

Current code (lines 67-115):
```python
def create_checker_and_task(oracle, bias, examples, is_incremental=True):
    # ... model creation ...
    if is_incremental:
        preparation = IncrementalCONGENTaskPreparation()
        output = preparation.prepare(model)
        task = output.task
        checker = IncrementalPySATChecker(
            task.set_kb, task.assumptions, 'glucose4', profiler
        )
    else:
        preparation = NonIncrementalCONGENTaskPreparation()
        output = preparation.prepare(model)
        task = output.task
        checker = NonIncrementalPySATChecker(
            task.set_kb, task.assumptions, 'glucose4', profiler)
    return checker, task, profiler, root_id
```

**New code:**

```python
def create_checker_and_task(oracle, bias, examples, is_incremental=True):
    # ... model creation (unchanged) ...

    profiler = get_global_profiler()

    if is_incremental:
        preparation = IncrementalCONGENTaskPreparation()
    else:
        preparation = NonIncrementalCONGENTaskPreparation()

    output = preparation.prepare(model)
    task = output.task

    # Run GenerateNE with temp checker (read-only QXP calls)
    temp_checker = NonIncrementalPySATChecker(
        task.set_kb, task.assumptions, 'glucose4', profiler
    )
    generate_ne = GenerateNE(temp_checker, profiler)
    ne_result = generate_ne.generate(
        set_tv=task.e_neg_literals,
        set_bg=task.set_b,
        start_assumption_id=task.next_assumption_id
    )
    merge_ne_into_task(task, ne_result)

    # Create final checker with complete data (including NE)
    if is_incremental:
        checker = IncrementalPySATChecker(
            task.set_kb, task.assumptions, 'glucose4', profiler
        )
    else:
        checker = NonIncrementalPySATChecker(
            task.set_kb, task.assumptions, 'glucose4', profiler
        )

    return checker, task, profiler, root_id
```

### Step 2: Update imports at top of `test_congen.py`

Add `merge_ne_into_task` import:

```python
from conacq.algorithms import (
    ConGen, AcqMSS, Reduce, GenerateNE,
    ConGenModel,
    IncrementalCONGENTaskPreparation,
    NonIncrementalCONGENTaskPreparation
)
from conacq.algorithms.generate_ne import merge_ne_into_task
```

### Step 3: Update `TestGenerateNE.test_generate_ne_empty`

Current test (lines 280-290) verifies empty output. Update to also check new fields:

```python
def test_generate_ne_empty(self):
    """Test GenerateNE with empty input returns empty."""
    checker = IncrementalPySATChecker([[1]], [1], 'glucose4')

    try:
        generate_ne = GenerateNE(checker)
        result = generate_ne.generate([], [])

        assert result.assumption_ids == []
        assert result.new_clauses == []
        assert result.set_neg_tv == []
    finally:
        checker.cleanup()
```

Note: `generate_from_examples` still works but now returns assumption_ids from the updated `generate()`. No change needed to its behavior.

### Step 4: Verify all TestCONGEN tests pass

The three CONGEN tests (`test_congen_incremental_with_rs_examples`, `test_congen_non_incremental_with_rs_examples`, `test_congen_incremental_with_ff_examples`) use `create_checker_and_task()` helper. After updating the helper, they should pass without changes to their test bodies.

Run:
```bash
PYTHONPATH=. pytest tests/test_congen.py -v
```

### Step 5: Verify TestACQMSS and TestReduce are unchanged

These tests create their own simple checkers directly and don't use GenerateNE. They should pass without any changes. Confirm:

```bash
PYTHONPATH=. pytest tests/test_congen.py::TestACQMSS -v
PYTHONPATH=. pytest tests/test_congen.py::TestReduce -v
```

## Todo List

- [ ] Update `create_checker_and_task()` with GenerateNE + merge step
- [ ] Add `merge_ne_into_task` import
- [ ] Update `TestGenerateNE.test_generate_ne_empty` to check new fields
- [ ] Run all tests: `PYTHONPATH=. pytest tests/test_congen.py -v`
- [ ] Verify all pass with identical results

## Success Criteria

- All tests in `test_congen.py` pass
- CONGEN tests produce same KB results as before refactoring
- GenerateNE test verifies `new_clauses` and `new_assumptions` fields
- No test references `checker.add_clause` or `checker.add_assumption`

## Risk Assessment

- **Low risk**: Only helper function changes; test assertions unchanged
- **Mitigation**: Compare KB output before/after refactoring for the same input data

## Security Considerations

None -- test code only.

## Next Steps

Run full test suite to confirm no regressions:
```bash
PYTHONPATH=. pytest tests/ -v
```

Update documentation (`docs/codebase-summary.md`, `docs/system-architecture.md`, `docs/code-standards.md`) to reflect new architecture where GenerateNE runs before CONGEN and checker is immutable after construction.
