# Phase 5: Delete ExampleProvider and Update Tests

## Context Links

- Phase 4: `phase-04-update-runner-consumers.md`
- Source: `tests/test_quacq.py` (826 LOC)
- Delete: `conacq/example_generators/example_provider.py`
- Delete: `conacq/example_generators/query_generator.py`

## Overview

- **Date**: 2026-02-28
- **Priority**: P2
- **Status**: completed
- **Description**: Delete old files (example_provider.py, query_generator.py), update all test imports and test logic to use QueryProvider

## Key Insights

- `tests/test_quacq.py` imports QueryGenerator in 3 places (line 26, line 651, line 692)
- TestQueryGenerator class (lines 176-204) tests QueryGenerator directly -> rename to TestQueryProvider, use QueryProvider
- TestQuAcqFactories (lines 632-656) tests for_oracle/for_examples with old params
- TestQuAcqModeValidation (lines 659-696) validates mode errors with old field names
- No other test files import QueryGenerator or ExampleProvider (verified via codebase search)

## Requirements

### Functional
- Delete `conacq/example_generators/example_provider.py`
- Delete `conacq/example_generators/query_generator.py`
- Update all QueryGenerator references in tests -> QueryProvider
- Update factory tests to use new QueryProvider-based API
- Update mode validation tests for new error messages
- All tests must pass

### Non-Functional
- No reduction in test coverage -- same scenarios tested with new API

## Related Code Files

### Files to delete
- `conacq/example_generators/example_provider.py`
- `conacq/example_generators/query_generator.py`

### Files to modify
- `tests/test_quacq.py`

## Implementation Steps

### Step 1: Delete old files

```bash
rm conacq/example_generators/example_provider.py
rm conacq/example_generators/query_generator.py
```

### Step 2: Update test imports (lines 26-27)

Replace:
```python
from conacq.example_generators import QueryGenerator
```
With:
```python
from conacq.example_generators import QueryProvider
```

### Step 3: Rename and update TestQueryGenerator class (lines 176-204)

Rename class to `TestQueryProvider`. Update tests:

```python
class TestQueryProvider:
    """Tests for QueryProvider."""

    def test_provider_creation(self):
        """Test provider can be created."""
        provider = QueryProvider()
        assert provider.solver_name == 'glucose4'
        assert provider.pool_exhausted is True  # no pool
        assert provider.pool_remaining == 0

    def test_provider_with_pool(self):
        """Test provider with pool."""
        pool = [{'a': True, 'b': False}]
        provider = QueryProvider(pool=pool, seed=42)
        assert provider.pool_exhausted is False
        assert provider.pool_remaining == 1

    def test_generate_from_sat(self, prepared_model):
        """Test SAT-based query generation."""
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

        if task.set_c:
            if query is not None:
                assert isinstance(query, dict)
                assert tested_c_id is not None
                assert tested_c_id in remaining_bias
```

### Step 4: Update TestQuAcq tests (lines 207-260)

All QuAcq tests using `QueryGenerator()` need to use `QueryProvider()` instead.

Replace pattern `query_gen = QueryGenerator()` with `query_provider = QueryProvider()` and update QuAcq construction.

Example for test_quacq_learn_with_limit (line 216):
```python
    def test_quacq_learn_with_limit(self, prepared_model, oracle, bias, checker):
        task = prepared_model.task
        task_data = _learn_params_from_task(task)

        query_provider = QueryProvider()
        discrim_gen = DiscriminatingGenerator(
            background_clauses=task.background_clauses,
            constraint_clauses=task.constraint_clauses,
            negated_clauses=task.negated_clauses,
            id_to_feature=task.id_to_feature)

        quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)
        result = quacq.learn(**task_data, mode='oracle', max_queries=5)
        ...
```

Apply same pattern to:
- test_quacq_empty_bias (line 243)
- test_full_learning_small_limit (line 266)
- test_quacq_learn_with_quacq_task (line 453)
- test_quacq_empty_bias_quacq_task (line 482)
- test_result_resolved_via_model (line 501)

### Step 5: Update TestQueryGeneratorWithQuAcqTask (lines 603-626)

Rename to `TestQueryProviderWithQuAcqTask`:

```python
class TestQueryProviderWithQuAcqTask:
    """Tests for QueryProvider with raw params from QuAcqTask."""

    def test_generate_from_sat_with_quacq_task(self, prepared_model):
        """Test SAT query generation with raw params from QuAcqTask."""
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

        if query is not None:
            assert isinstance(query, dict)
            assert isinstance(tested_c_id, int)
            assert tested_c_id in remaining_bias
```

### Step 6: Update TestQuAcqFactories (lines 632-656)

```python
class TestQuAcqFactories:
    """Tests for QuAcq factory class methods."""

    def test_for_oracle_factory(self, oracle):
        """Test for_oracle factory injects all deps."""
        checker = _minimal_checker()
        query_provider = QueryProvider()
        discrim_gen = DiscriminatingGenerator(
            background_clauses=[], constraint_clauses={},
            negated_clauses={}, id_to_feature={})
        quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)
        assert quacq.oracle is oracle
        assert quacq.query_provider is query_provider
        assert quacq.discriminating_generator is discrim_gen

    def test_for_examples_factory(self, oracle):
        """Test for_examples factory injects query_provider."""
        provider = QueryProvider(pool=[{'a': True}], seed=42)
        quacq = QuAcq.for_examples(_minimal_checker(), oracle, provider)
        assert quacq.oracle is oracle
        assert quacq.query_provider is provider
```

### Step 7: Update TestQuAcqModeValidation (lines 659-696)

Update error message assertions:

```python
class TestQuAcqModeValidation:
    """Tests for mode validation in learn()."""

    def _minimal_learn_params(self):
        return dict(
            set_c=[], set_b=[], negation_map={},
            background_clauses=[],
            feature_ids={'root': 1}, id_to_feature={1: 'root'},
            constraint_clauses={}, negated_clauses={},
            pos_assignment_to_assumption=None,
            neg_assignment_to_assumption=None,
            root_assumption=None)

    def test_no_query_provider_raises(self, oracle):
        """Any mode without query_provider raises."""
        quacq = QuAcq(_minimal_checker(), oracle)
        with pytest.raises(ValueError, match="query_provider"):
            quacq.learn(**self._minimal_learn_params(), mode='oracle')

    def test_oracle_mode_requires_discrim_gen(self, oracle):
        """Oracle mode without discriminating_generator raises."""
        quacq = QuAcq(_minimal_checker(), oracle, query_provider=QueryProvider())
        with pytest.raises(ValueError, match="discriminating_generator"):
            quacq.learn(**self._minimal_learn_params(), mode='oracle')

    def test_example_only_works_without_discrim_gen(self, oracle):
        """example_only mode works without discriminating_generator."""
        quacq = QuAcq(_minimal_checker(), oracle, query_provider=QueryProvider())
        result = quacq.learn(**self._minimal_learn_params(), mode='example_only')
        assert result.convergence_reason == 'empty_bias'

    def test_example_first_requires_discrim_gen(self, oracle):
        """example_first mode without discriminating_generator raises."""
        quacq = QuAcq(_minimal_checker(), oracle, query_provider=QueryProvider())
        with pytest.raises(ValueError, match="discriminating_generator"):
            quacq.learn(**self._minimal_learn_params(), mode='example_first')
```

### Step 8: Add new QueryProvider-specific tests

Add test class for pool filtering:

```python
class TestQueryProviderPoolFiltering:
    """Tests for QueryProvider pool filtering logic."""

    def test_pool_exhausted_when_empty(self):
        """Provider with no pool is immediately exhausted."""
        provider = QueryProvider()
        assert provider.pool_exhausted is True

    def test_pool_filtering_skips_invalid(self):
        """Pool examples not satisfying KB+BG are skipped."""
        # Pool has 1 example, KB has clause that rejects it
        provider = QueryProvider(pool=[{'a': True}])
        query, c_id = provider.generate_from_pool(
            remaining_bias={1},
            kb_clauses=[[-1]],  # clause: NOT a (rejects a=True)
            bg_clauses=[],
            constraint_clauses={1: [[1]]},  # constraint: a
            feature_ids={'a': 1})
        assert query is None  # filtered out
        assert provider.pool_exhausted is True
```

## Todo List

- [ ] Delete example_provider.py and query_generator.py
- [ ] Update test imports (QueryGenerator -> QueryProvider)
- [ ] Rename TestQueryGenerator -> TestQueryProvider, update tests
- [ ] Update all QuAcq test constructors (QueryGenerator -> QueryProvider)
- [ ] Update TestQuAcqFactories
- [ ] Update TestQuAcqModeValidation
- [ ] Add TestQueryProviderPoolFiltering
- [ ] Run full test suite, verify all pass

## Success Criteria

- No references to QueryGenerator or ExampleProvider in codebase
- All existing test scenarios preserved with new API
- New pool filtering tests added
- `PYTHONPATH=. pytest tests/test_quacq.py -v` passes

## Risk Assessment

- **Missing references**: Grep for `QueryGenerator` and `ExampleProvider` across entire codebase before declaring done
- **Test behavior change**: Pool-based tests may behave differently due to filtering -- verify assertions match new behavior

## Security Considerations

- No new external interfaces

## Next Steps

- Phase 6: Update documentation
