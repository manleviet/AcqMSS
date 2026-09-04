---
title: "Phase 4: QuacqRunner Passes Checker + Model to QueryProvider"
status: complete
priority: P1
effort: 15m
created: 2026-02-28
completed: 2026-02-28
---

# Phase 4: QuacqRunner Passes Checker + Model to QueryProvider

## Context Links

- [Phase 2: QueryProvider refactor](phase-02-refactor-query-provider.md)
- Source: `conacq/runners/quacq_runner.py`

## Overview

- **Priority**: P1
- **Status**: complete
- Pass `checker` and `model` to QueryProvider at construction in runner

## Key Insights

- Runner already creates checker via `CheckerFactory.create_from_model()`
- Runner already has `self.model` (QuAcqModel)
- QueryProvider constructed in 2 places: `_run_oracle_mode()` and `_run_example_mode()`
- Both need `checker=checker, model=self.model` added

## Requirements

- Both oracle and example mode QueryProvider instances receive checker + model
- Checker must be created BEFORE QueryProvider (already the case in runner flow)

## Related Code Files

- **Modify**: `conacq/runners/quacq_runner.py` (lines 239, 259)

## Implementation Steps

### 1. Update _run_oracle_mode (line 239)

**Before:**
```python
query_provider = QueryProvider(self.solver_name, profiler_instance=profiler)
```

**After:**
```python
query_provider = QueryProvider(self.solver_name,
                               checker=checker,
                               model=self.model,
                               profiler_instance=profiler)
```

### 2. Update _run_example_mode (lines 258-263)

**Before:**
```python
mixed_examples = list(positive_examples) + list(negative_examples)
query_provider = QueryProvider(
    self.solver_name,
    pool=mixed_examples,
    seed=shuffle_seed,
    profiler_instance=profiler)
```

**After:**
```python
mixed_examples = list(positive_examples) + list(negative_examples)
query_provider = QueryProvider(
    self.solver_name,
    pool=mixed_examples,
    seed=shuffle_seed,
    checker=checker,
    model=self.model,
    profiler_instance=profiler)
```

### 3. Verify checker is available

In `run()`, checker is created at line 175 and passed to `_run_oracle_mode` / `_run_example_mode` as first arg. Both methods receive it. No additional wiring needed.

## Todo List

- [ ] Add `checker=checker, model=self.model` to oracle mode QueryProvider
- [ ] Add `checker=checker, model=self.model` to example mode QueryProvider
- [ ] Run: `PYTHONPATH=. pytest tests/test_quacq.py -v`

## Success Criteria

- QueryProvider receives checker and model in both modes
- No change to runner's public API

## Risk Assessment

- **Very low**: Mechanical addition of 2 params to 2 constructor calls

## Security Considerations

N/A.

## Next Steps

Phase 5: Update tests.
