# Phase 7: Test and Verify

## Context Links
- [Plan overview](plan.md)
- Depends on: Phase 6 (all callers updated)
<!-- Updated: Validation Session 1 - Add 3-mode test coverage (oracle, example_only, example_first) -->

## Overview
- **Priority:** High (gate for completion)
- **Status:** complete
- **Description:** Run full test suite, add new tests for DI features and ALL 3 learning modes, verify no regressions.

## Key Insights
- Phases 1-6 change public APIs of 5 files + 2 callers
- No `learn_from_examples` tests existed before — now covered via mode param
- Validation confirmed: test all 3 modes (oracle, example_only, example_first)
- sat_utils.py standalone functions should also be unit-tested

## Requirements

### Functional
- All existing tests pass (adapted to new API)
- New tests: factory methods, mode validation, DI injection
- New tests: all 3 learning modes end-to-end
- sat_utils.py utility functions tested

### Non-Functional
- No test skips or xfails for this refactor
- No mocks — real SAT solving

## Implementation Steps

### Step 1: Run existing tests
```bash
PYTHONPATH=. pytest tests/test_quacq.py -v
PYTHONPATH=. pytest tests/ -v
```

### Step 2: Add factory method tests
```python
def test_for_oracle_factory(self):
    quacq = QuAcq.for_oracle(oracle, query_gen, discrim_gen)
    assert quacq.oracle is oracle
    assert quacq.query_generator is query_gen
    assert quacq.discriminating_generator is discrim_gen

def test_for_examples_factory(self):
    quacq = QuAcq.for_examples(oracle, example_provider)
    assert quacq.example_provider is example_provider
    assert quacq.query_generator is None
```

### Step 3: Add mode validation tests
```python
def test_oracle_mode_requires_query_generator(self):
    quacq = QuAcq(oracle)  # no query_gen
    with pytest.raises(ValueError, match="query_generator"):
        quacq.learn(..., mode='oracle')

def test_oracle_mode_requires_discrim_gen(self):
    quacq = QuAcq(oracle, query_generator=QueryGenerator())
    with pytest.raises(ValueError, match="discriminating_generator"):
        quacq.learn(..., mode='oracle')

def test_example_mode_requires_provider(self):
    quacq = QuAcq(oracle, query_generator=QueryGenerator())
    with pytest.raises(ValueError, match="example_provider"):
        quacq.learn(..., mode='example_only')
```

### Step 4: Add 3-mode learning tests
```python
def test_learn_oracle_mode(self):
    """Oracle mode: QueryGenerator generates queries, oracle.ask() classifies."""
    quacq = QuAcq.for_oracle(oracle, query_gen, discrim_gen)
    result = quacq.learn(**task_data, mode='oracle', max_queries=5)
    assert isinstance(result, QuAcqResult)
    assert result.n_queries <= 5

def test_learn_example_only_mode(self):
    """Example-only: ExampleProvider supplies queries, oracle.is_valid() classifies."""
    provider = ExampleProvider(examples, seed=42)
    quacq = QuAcq.for_examples(oracle, provider)
    result = quacq.learn(**task_data, mode='example_only', max_queries=50)
    assert isinstance(result, QuAcqResult)

def test_learn_example_first_mode(self):
    """Example-first: pool first, SAT fallback when exhausted."""
    provider = ExampleProvider(examples[:3], seed=42)  # small pool
    quacq = QuAcq(oracle, query_generator=query_gen,
                  example_provider=provider,
                  discriminating_generator=discrim_gen)
    result = quacq.learn(**task_data, mode='example_first', max_queries=20)
    assert isinstance(result, QuAcqResult)
```

### Step 5: Add sat_utils unit tests
```python
class TestSatUtils:
    def test_config_to_assumptions(self): ...
    def test_partial_config_to_assumptions(self): ...
    def test_get_constraint_vars(self): ...
    def test_violates_clauses(self): ...
    def test_get_constraints_with_scope(self): ...
```

### Step 6: Verify _task_compat tests still pass
```bash
PYTHONPATH=. pytest tests/test_quacq.py -v -k "TaskCompat"
```

### Step 7: Final full suite
```bash
PYTHONPATH=. pytest tests/ -v
```

## Todo List
- [ ] Run existing tests — all pass
- [ ] Add factory method tests
- [ ] Add mode validation tests (3 tests)
- [ ] Add oracle mode learning test
- [ ] Add example_only mode learning test
- [ ] Add example_first mode learning test
- [ ] Add sat_utils unit tests
- [ ] Verify TaskCompat tests pass
- [ ] Final full suite — zero failures

## Success Criteria
- **Zero test failures** across full suite
- New tests cover: factories, mode validation, all 3 learning modes, sat_utils
- No xfails or skips
- sat_utils functions independently verified

## Risk Assessment
- **Low risk at this point**: All code changes done. Verification only.
- **Example mode test data**: Need valid positive/negative examples for ExampleProvider. Use existing test fixtures if available.

## Unresolved Questions
- Should `generate_with_priority` get a dedicated test? No production callers — skip for now.
