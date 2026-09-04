from conacq.algorithms.quacq import quacq_model

# Phase 6: Update Tests

## Context Links
- [Parent Plan](plan.md) | Depends on: Phase 1-5
- Source: `tests/test_interactive.py` (601 LOC)
- Source: `tests/test_evaluation.py` (474 LOC)

## Overview
- **Priority**: P1
- **Status**: completed
- **Depends on**: Phase 1-5 (all implementation complete)
- **Description**: Update all interactive tests to use QuAcqTask/InteractiveModel, verify identical KB results via DescriptionProvider, and add new unit tests for new classes.

## Key Insights
1. `test_interactive.py` has 7 test classes: TestInteractiveTask, TestInteractiveResult, TestFeatureModelOracle, TestCachedOracle, TestQueryGenerator, TestQuAcq, TestInteractiveLearner, TestIntegration, TestEvaluation, TestFMData, TestOracleABC.
2. Tests that use InteractiveTask directly (TestInteractiveTask, interactive_task fixture) must be duplicated/updated for QuAcqTask.
3. Tests that use InteractiveLearner (TestInteractiveLearner, TestIntegration, TestEvaluation) must be updated to use InteractiveModel + QuAcq OR kept as deprecated path tests.
4. TestFeatureModelOracle, TestCachedOracle, TestFMData, TestOracleABC — unchanged (oracle tests).
5. TestQueryGenerator — must test with QuAcqTask.
6. TestQuAcq — must test with QuAcqTask.
7. `test_evaluation.py` has CV tests — should work unchanged since runner resolves to strings.

## Requirements

### Functional
- New tests for QuAcqTask, InteractiveModel, InteractiveTaskPreparation
- Updated tests for QuAcq, QueryGenerator, FindScope, FindC with QuAcqTask
- Integration test: full pipeline InteractiveModel -> QuAcq -> InteractiveResult -> evaluate
- Verify identical KB results (by constraint name) between old and new paths

### Non-functional
- Follow existing test patterns (@parameterized.expand, ENABLED_TESTS, fixtures)
- Keep old InteractiveTask tests (they test the deprecated path, still valid)

## Related Code Files

### Files to Modify
| File | Changes |
|------|---------|
| `tests/test_interactive.py` | Add QuAcqTask tests, update QuAcq/QueryGenerator tests, add InteractiveModel tests |

### Files to Read
| File | Why |
|------|-----|
| `tests/test_congen.py` | ConGenModel test patterns to mirror |
| `tests/test_evaluation.py` | CV test patterns, check if updates needed |

## Implementation Steps

### Step 1: Add new fixtures

```python
@pytest.fixture
def interactive_model(bias):
    """Create InteractiveModel from bias."""
    model = InteractiveModel()
    model.constraint_map = bias.to_constraint_map()
    model.variables = bias.feature_ids
    return model

@pytest.fixture
def prepared_model(interactive_model, oracle):
    """Create prepared InteractiveModel with QuAcqTask."""
    interactive_model.prepare(oracle)
    return interactive_model

@pytest.fixture
def quacq_task(prepared_model):
    """Get QuAcqTask from prepared model."""
    return prepared_model.task
```

### Step 2: Add TestQuAcqTask class

```python
class TestQuAcqTask:
    """Tests for QuAcqTask data structure."""

    def test_task_creation(self, quacq_task):
        """Test QuAcqTask created with correct structure."""
        assert len(quacq_task.bias) > 0
        assert all(isinstance(aid, int) for aid in quacq_task.bias)
        assert len(quacq_task.learned_kb) == 0
        assert len(quacq_task.feature_ids) > 0
        assert len(quacq_task.constraint_clauses) == len(quacq_task.bias)
        assert len(quacq_task.set_kb) > 0
        assert len(quacq_task.assumptions) > 0

    def test_add_to_kb(self, quacq_task):
        """Test adding assumption ID to KB."""
        aid = next(iter(quacq_task.bias))
        quacq_task.add_to_kb(aid)
        assert aid in quacq_task.learned_kb
        assert len(quacq_task.learned_kb) == 1

    def test_remove_from_bias(self, quacq_task):
        """Test removing assumption IDs from bias."""
        initial_size = len(quacq_task.bias)
        bias_iter = iter(quacq_task.bias)
        to_remove = [next(bias_iter), next(bias_iter)]
        quacq_task.remove_from_bias(to_remove)
        assert len(quacq_task.bias) == initial_size - 2

    def test_constraint_clauses_populated(self, quacq_task):
        """Test constraint_clauses maps each bias ID to raw clauses."""
        for aid in quacq_task.bias:
            assert aid in quacq_task.constraint_clauses
            clauses = quacq_task.constraint_clauses[aid]
            assert isinstance(clauses, list)
            assert len(clauses) > 0

    def test_negated_clauses_populated(self, quacq_task):
        """Test negated_clauses maps each bias ID to negated raw clauses."""
        for aid in quacq_task.bias:
            assert aid in quacq_task.negated_clauses
            neg_clauses = quacq_task.negated_clauses[aid]
            assert isinstance(neg_clauses, list)
            assert len(neg_clauses) > 0

    def test_negation_map_populated(self, quacq_task):
        """Test negation_map maps each bias ID to its negated assumption."""
        for aid in quacq_task.bias:
            assert aid in quacq_task.negation_map
            neg_aid = quacq_task.negation_map[aid]
            assert isinstance(neg_aid, int)
            assert neg_aid != aid

    def test_background_populated(self, quacq_task):
        """Test background has BG assumption IDs from oracle."""
        assert len(quacq_task.background) > 0
        assert all(isinstance(b, int) for b in quacq_task.background)

    def test_get_constraints_with_scope(self, quacq_task):
        """Test scope matching returns int assumption IDs."""
        # Get scope of first constraint
        aid = next(iter(quacq_task.bias))
        scope = quacq_task._get_constraint_vars(aid)
        if scope:
            candidates = quacq_model.get_constraints_with_scope(scope)
            assert all(isinstance(c, int) for c in candidates)
            assert aid in candidates

    def test_get_kb_clauses(self, quacq_task):
        """Test getting KB clauses from learned constraints."""
        aid = next(iter(quacq_task.bias))
        quacq_task.add_to_kb(aid)
        clauses = quacq_task.get_kb_clauses()
        assert isinstance(clauses, list)
        assert len(clauses) > 0

    def test_clone(self, quacq_task):
        """Test deep copy."""
        cloned = quacq_task.clone()
        assert cloned.bias == quacq_task.bias
        assert cloned is not quacq_task
```

### Step 3: Add TestInteractiveModel class

```python
class TestInteractiveModel:
    """Tests for InteractiveModel."""

    def test_from_bias(self):
        """Test model creation from bias file."""
        if not BIAS_PATH.exists():
            pytest.skip("Bias not found")
        model = InteractiveModel.from_bias(str(BIAS_PATH))
        assert len(model.constraint_map) > 0
        assert len(model.variables) > 0

    def test_prepare(self, interactive_model, oracle):
        """Test prepare creates QuAcqTask."""
        task = interactive_model.prepare(oracle)
        assert isinstance(task, QuAcqTask)
        assert len(task.bias) > 0
        assert len(task.set_kb) > 0

    def test_description_provider(self, prepared_model):
        """Test DescriptionProvider maps IDs to names."""
        provider = prepared_model.description_provider
        task = prepared_model.task
        for aid in task.bias:
            name = provider.get_description(aid)
            assert isinstance(name, str)
            assert len(name) > 0

    def test_resolve_kb(self, prepared_model):
        """Test resolving assumption IDs to names and clauses."""
        task = prepared_model.task
        aids = list(task.bias)[:3]
        names, clauses = prepared_model.resolve_kb(aids)
        assert len(names) == 3
        assert all(isinstance(n, str) for n in names)
        assert len(clauses) > 0

    def test_prepare_reusable(self, interactive_model, oracle):
        """Test prepare can be called multiple times."""
        task1 = interactive_model.prepare(oracle)
        task2 = interactive_model.prepare(oracle)
        assert task1.bias == task2.bias
        assert len(task1.set_kb) == len(task2.set_kb)
```

### Step 4: Update TestQueryGenerator

```python
class TestQueryGenerator:
    def test_generate_query_quacq_task(self, quacq_task):
        """Test query generation with QuAcqTask."""
        gen = QueryGenerator()
        query, tested_aid = gen.generate(quacq_task)

        if quacq_task.bias:
            if query is not None:
                assert isinstance(query, dict)
                assert isinstance(tested_aid, int)
                assert tested_aid in quacq_task.bias
```

### Step 5: Update TestQuAcq

```python
class TestQuAcq:
    def test_quacq_learn_with_quacq_task(self, quacq_task, oracle, prepared_model):
        """Test QuAcq learning with QuAcqTask."""
        quacq = QuAcq()
        result = quacq.learn(quacq_task, oracle,
                             prepared_model.description_provider,
                             max_queries=5)

        assert result is not None
        assert result.n_queries <= 5
        assert isinstance(result.kb_assumption_ids, list)
        assert isinstance(result.kb_constraints, list)
        assert len(result.kb_assumption_ids) == len(result.kb_constraints)
        assert all(isinstance(aid, int) for aid in result.kb_assumption_ids)
        assert all(isinstance(name, str) for name in result.kb_constraints)

    def test_quacq_empty_bias(self, oracle):
        """Test QuAcq with empty QuAcqTask converges immediately."""
        task = QuAcqTask(
            bias=set(),
            feature_ids={'root': 1},
            id_to_feature={1: 'root'},
        )
        provider = DescriptionProvider()
        quacq = QuAcq()
        result = quacq.learn(task, oracle, provider, max_queries=100)
        assert result.n_queries == 0
        assert result.convergence_reason == 'empty_bias'
```

### Step 6: Add equivalence test

```python
class TestEquivalence:
    """Verify old and new paths produce equivalent KB."""

    @pytest.mark.slow
    def test_kb_names_match(self):
        """Old InteractiveLearner and new InteractiveModel produce same KB names."""
        if not FM_PATH.exists() or not BIAS_PATH.exists():
            pytest.skip("Test data not found")

        # Old path
        learner = InteractiveLearner.from_files(
            fm_path=str(FM_PATH), bias_path=str(BIAS_PATH),
            enable_profiling=False)
        old_result = learner.learn(mode='automated', max_queries=20)

        # New path
        oracle = FeatureModelOracle(str(FM_PATH))
        model = InteractiveModel.from_bias(str(BIAS_PATH))
        model.prepare(oracle)
        quacq = QuAcq()
        new_result = quacq.learn(model.task, oracle,
                                 model.description_provider, max_queries=20)

        # Same KB by name
        assert set(old_result.kb_constraints) == set(new_result.kb_constraints)
```

### Step 7: Update TestInteractiveLearner (keep for deprecated path)

Keep existing tests as-is — they test the deprecated InteractiveLearner path which still works. Add deprecation note in test docstrings.

### Step 8: Verify test_evaluation.py

Run `test_evaluation.py` without changes. CV tests use InteractiveRunner which is updated in Phase 4. If tests pass, no changes needed. If any test accesses `result.kb_constraints` expecting str, it should still work.

## Todo List
- [ ] Add fixtures: interactive_model, prepared_model, quacq_task
- [ ] Add TestQuAcqTask class with all field/method tests
- [ ] Add TestInteractiveModel class
- [ ] Update TestQueryGenerator with QuAcqTask tests
- [ ] Update TestQuAcq with QuAcqTask tests
- [ ] Add TestEquivalence class comparing old vs new paths
- [ ] Keep existing InteractiveTask/InteractiveLearner tests (deprecated path)
- [ ] Run full test suite: `PYTHONPATH=. pytest tests/ -v`
- [ ] Verify test_evaluation.py passes without changes

## Success Criteria
- All new tests pass
- All existing tests pass (deprecated path still functional)
- Equivalence test confirms identical KB names between old and new paths
- Full test suite green: `PYTHONPATH=. pytest tests/ -v`

## Risk Assessment
1. **Non-determinism**: QuAcq's query generation order may differ between old (str iteration) and new (int iteration) paths, leading to different KB results for same max_queries. Equivalence test should use large enough max_queries to converge, or compare on a small enough model (REAL-FM-7) where convergence is fast.
2. **Fixture dependencies**: prepared_model fixture depends on oracle fixture which depends on FM file. Skip if not available.

## Security Considerations
- No changes to external input handling

## Next Steps
- Phase 7: Deprecate old classes
