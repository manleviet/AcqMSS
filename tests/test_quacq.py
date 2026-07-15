"""
Tests for QuAcq constraint acquisition algorithm.

Uses REAL-FM-7 feature model with generated bias.
Tests core components: QueryProvider, QuAcq, QuAcqTask, QuAcqModel.
"""

import pytest
from pathlib import Path

from conacq.oracle import FMOracle, Oracle, CachedOracle
from conacq.bias import BiasIO
from conacq.algorithms.quacq import (
    QuAcqResult,
    QuAcq,
    DiscriminatingGenerator,
)
from conacq.algorithms.quacq.task_preparation import QuAcqTask, QuAcqTaskInput
from conacq.algorithms.quacq.quacq_model import QuAcqModel
from conacq.algorithms.quacq.quacq_model_builder import QuAcqModelBuilder
from conacq.example_generators import QueryProvider
from explanation.checker.backend import (
    build_checker, SolverBackend, NonIncrementalPySATChecker,
)
from profiling import (
    get_global_profiler,
    use_global_profiler,
    ProfilerPreset
)


# Test data paths
DATA_DIR = Path(__file__).parent.parent / "data"
FM_PATH = DATA_DIR / "fms" / "REAL-FM-7.uvl"
BIAS_PATH = DATA_DIR / "bias" / "REAL-FM-7-bias.json"


def _learn_params_from_task(task):
    """Extract flat learn() params from a prepared QuAcqTask."""
    return dict(
        set_c=task.set_c,
        set_b=task.set_b,
        negation_map=task.negation_map,
    )


@pytest.fixture
def oracle():
    """Load REAL-FM-7 feature model oracle."""
    if not FM_PATH.exists():
        pytest.skip(f"Feature model not found: {FM_PATH}")
    return FMOracle(str(FM_PATH))


@pytest.fixture
def bias():
    """Load REAL-FM-7 bias."""
    if not BIAS_PATH.exists():
        pytest.skip(f"Bias file not found: {BIAS_PATH}")
    return BiasIO.load_from_json(str(BIAS_PATH))


@pytest.fixture
def interactive_model(oracle):
    """Create QuAcqModel via builder (a pure KB — preparation is per-run)."""
    if not BIAS_PATH.exists():
        pytest.skip(f"Bias file not found: {BIAS_PATH}")
    return (QuAcqModelBuilder
            .from_bias(str(BIAS_PATH))
            .with_oracle_data(oracle.oracle_data)
            .build())


@pytest.fixture
def prepared_model(interactive_model):
    """Alias for interactive_model (the pure KB model)."""
    return interactive_model


@pytest.fixture
def prepared(oracle, interactive_model):
    """The PreparedTask (task + describe + assignment_map) for the model."""
    return interactive_model.prepare_task(QuAcqTaskInput(oracle.oracle_data))


@pytest.fixture
def checker(prepared):
    """Create checker from the prepared QuAcqTask."""
    return build_checker(
        prepared.task,
        SolverBackend.from_flags(use_incremental=True))


def _minimal_checker():
    """Create a minimal checker for tests without a model."""
    return NonIncrementalPySATChecker([], [])


class TestQuAcqResult:
    """Tests for QuAcqResult data structure."""

    def test_result_creation(self):
        """Test result can be created with 4 fields."""
        result = QuAcqResult(
            kb_assumption_ids=[10, 12],
            n_queries=10,
            convergence_reason='empty_bias',
            query_history=[({'f1': True}, True, 'main')]
        )

        assert result.n_queries == 10
        assert result.convergence_reason == 'empty_bias'
        assert len(result.kb_assumption_ids) == 2
        assert len(result.query_history) == 1

    def test_result_defaults(self):
        """Test result defaults are sensible."""
        result = QuAcqResult()
        assert result.kb_assumption_ids == []
        assert result.n_queries == 0
        assert result.convergence_reason == ""
        assert result.query_history == []

    def test_result_repr(self):
        """Test repr derives n_kb from len(kb_assumption_ids)."""
        result = QuAcqResult(kb_assumption_ids=[10, 12, 14], n_queries=5,
                             convergence_reason='empty_bias')
        assert 'n_kb=3' in repr(result)
        assert 'n_queries=5' in repr(result)


class TestFMOracle:
    """Tests for FMOracle."""

    def test_oracle_creation(self, oracle):
        """Test oracle can be created."""
        assert oracle.get_fm_data().feature_count > 0

    def test_oracle_invalid_config(self, oracle):
        """Test oracle rejects invalid configuration."""
        # Create an invalid config (all features false including root)
        features = oracle.get_variables()
        invalid_config = {f: False for f in features}
        assert oracle.ask(invalid_config) is False


class TestCachedOracle:
    """Tests for CachedOracle."""

    def test_cached_oracle_caches_results(self, oracle):
        """Test cached oracle caches results."""
        cached = CachedOracle(oracle)

        # First query — use a real feature name from the FM
        features = list(oracle.get_variables())
        config = {features[0]: True}
        result1 = cached.ask(config)
        stats1 = cached.get_cache_stats()

        assert stats1['misses'] == 1
        assert stats1['hits'] == 0

        # Same query should hit cache
        result2 = cached.ask(config)
        stats2 = cached.get_cache_stats()

        assert stats2['hits'] == 1
        assert result1 == result2


class TestQueryProvider:
    """Tests for QueryProvider."""

    def test_provider_creation(self):
        """Test provider can be created."""
        provider = QueryProvider()
        assert provider.pool_exhausted is True
        assert provider.pool_remaining == 0

    def test_provider_with_pool(self):
        """Test provider with pool."""
        pool = [{'a': True, 'b': False}]
        provider = QueryProvider(pool=pool, seed=42)
        assert provider.pool_exhausted is False
        assert provider.pool_remaining == 1

    def test_generate_from_sat(self, prepared_model, prepared, checker):
        """Test SAT-based query generation."""
        task = prepared.task
        provider = QueryProvider(checker=checker, model=prepared_model,
                                 assignment_map=prepared.assignment_map)
        remaining_bias = set(task.set_c)
        query, tested_c_id = provider.generate_from_sat(
            remaining_bias=remaining_bias,
            learned_kb=[],
            set_b=task.set_b,
            negation_map=task.negation_map)

        if task.set_c:
            if query is not None:
                assert isinstance(query, dict)
                assert tested_c_id is not None
                assert tested_c_id in remaining_bias


class TestQuAcq:
    """Tests for QuAcq algorithm."""

    def test_quacq_creation(self, oracle):
        """Test QuAcq can be created."""
        checker = _minimal_checker()
        quacq = QuAcq(checker, oracle)
        assert quacq.oracle is oracle

    def test_quacq_learn_with_limit(self, prepared_model, prepared, oracle, bias, checker):
        """Test QuAcq learning with query limit."""
        task = prepared.task
        task_data = _learn_params_from_task(task)

        query_provider = QueryProvider(checker=checker, model=prepared_model,
                                       assignment_map=prepared.assignment_map)
        discrim_gen = DiscriminatingGenerator(
            checker=checker, model=prepared_model,
            profiler=get_global_profiler(), root_assumption=task.set_b[0], task=task)

        quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen,
                                   model=prepared_model,
                                   task=task, assignment_map=prepared.assignment_map)
        result = quacq.learn(
            **task_data, mode='oracle',
            max_queries=5)

        assert result is not None
        assert result.n_queries <= 5
        assert isinstance(result.kb_assumption_ids, list)
        assert result.convergence_reason in ['empty_bias', 'max_queries', 'no_query']

        print(f"\nQuAcq Result (max_queries=5):")
        print(f"  Queries: {result.n_queries}")
        print(f"  KB size: {len(result.kb_assumption_ids)}")
        print(f"  Convergence: {result.convergence_reason}")

    def test_quacq_empty_bias(self, oracle):
        """Test QuAcq with empty bias converges immediately."""
        checker = _minimal_checker()
        query_provider = QueryProvider()
        discrim_gen = DiscriminatingGenerator(
            checker=checker, model=None,
            profiler=get_global_profiler(), root_assumption=0)

        quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)
        result = quacq.learn(
            set_c=[], set_b=[], negation_map={},
            mode='oracle', max_queries=100)

        assert result.n_queries == 0
        assert result.convergence_reason == 'empty_bias'


class TestIntegration:
    """Integration tests for full learning pipeline."""

    @pytest.mark.slow
    def test_full_learning_small_limit(self):
        """Test full learning with small query limit."""
        if not FM_PATH.exists() or not BIAS_PATH.exists():
            pytest.skip("Test data files not found")

        profiler = use_global_profiler(ProfilerPreset.BENCHMARK)
        profiler.start()

        try:
            oracle = FMOracle(str(FM_PATH))
            model = (QuAcqModelBuilder
                     .from_bias(str(BIAS_PATH))
                     .with_oracle_data(oracle.oracle_data)
                     .build())

            prepared = model.prepare_task(QuAcqTaskInput(oracle.oracle_data))
            task = prepared.task
            task_data = _learn_params_from_task(task)

            checker = build_checker(
                task, SolverBackend.from_flags(use_incremental=True))
            query_provider = QueryProvider(checker=checker, model=model,
                                           assignment_map=prepared.assignment_map)
            discrim_gen = DiscriminatingGenerator(
                checker=checker, model=model,
                profiler=get_global_profiler(), root_assumption=task.set_b[0], task=task)

            quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen, model=model,
                                     task=task, assignment_map=prepared.assignment_map)
            result = quacq.learn(
                **task_data, mode='oracle',
                max_queries=50)

            assert result is not None
            assert result.n_queries <= 50
            assert result.convergence_reason in [
                'empty_bias', 'max_queries', 'no_query']

        finally:
            profiler.stop()


class TestFMData:
    """Tests for FMData dataclass."""

    def test_fm_data_populated(self, oracle):
        """Verify FMData contains correct FM metadata."""
        fm_data = oracle.get_fm_data()

        assert isinstance(fm_data.features, set)
        assert len(fm_data.features) > 0
        assert isinstance(fm_data.feature_ids, dict)
        assert len(fm_data.feature_ids) == len(fm_data.features)
        assert fm_data.root_feature in fm_data.features
        assert fm_data.num_constraints > 0
        assert fm_data.next_available_id > max(fm_data.feature_ids.values())
        assert fm_data.feature_count == len(fm_data.features)

    def test_fm_data_frozen(self, oracle):
        """Verify FMData is immutable."""
        fm_data = oracle.get_fm_data()
        with pytest.raises(AttributeError):
            fm_data.root_feature = "changed"


class TestOracleABC:
    """Tests for Oracle ABC contract."""

    def test_oracle_abc_minimal(self):
        """Verify Oracle ABC has only is_valid as abstract method."""
        import inspect
        from conacq.oracle.base import Oracle

        abstract_methods = {
            name for name, method in inspect.getmembers(Oracle)
            if getattr(method, '__isabstractmethod__', False)
        }
        assert abstract_methods == {'is_valid'}


# =========================================================================
# Assumption-ID-based tests (QuAcqTask, QuAcqModel)
# =========================================================================

class TestQuAcqTask:
    """Tests for QuAcqTask data structure (assumption-ID based)."""

    def test_task_creation(self, prepared_model, prepared):
        """Test QuAcqTask is created with correct structure."""
        task = prepared.task
        assert isinstance(task, QuAcqTask)
        assert len(task.set_c) > 0
        assert len(prepared_model.name_to_id) > 0

        # All bias IDs should be ints
        for aid in task.set_c:
            assert isinstance(aid, int)

    def test_bias_has_clause_mappings(self, prepared):
        """Test each bias constraint has clause and negated clause mappings."""
        task = prepared.task
        for aid in task.set_c:
            assert aid in task.constraint_clauses, f"Missing clauses for {aid}"
            assert len(task.constraint_clauses[aid]) > 0

    def test_background_populated(self, prepared):
        """Test background has BG assumption IDs from oracle."""
        task = prepared.task
        assert len(task.set_b) > 0
        # BG assumptions should be in the full assumptions list
        for bg_id in task.set_b:
            assert bg_id in task.assumptions

    def test_assumptions_and_negation_map(self, prepared):
        """Test assumption ID layout is consistent."""
        task = prepared.task
        # Each bias constraint should have a negation mapping
        for aid in task.set_c:
            assert aid in task.negation_map, f"Missing negation for {aid}"
            neg_id = task.negation_map[aid]
            assert neg_id in task.assumptions


class TestQuAcqModel:
    """Tests for QuAcqModel (assumption-ID based model)."""

    def test_builder(self, interactive_model, prepared):
        """Test model creation via builder yields a pure KB that prepares a task."""
        assert len(interactive_model.constraint_map) > 0
        assert len(interactive_model.name_to_id) > 0
        assert prepared.task is not None

    def test_prepare_task(self, prepared):
        """Test prepare_task creates a QuAcqTask."""
        assert prepared.task is not None
        assert isinstance(prepared.task, QuAcqTask)

    def test_prepared_describe(self, prepared):
        """Test the PreparedTask's DescriptionProvider resolves IDs to names."""
        provider = prepared.describe
        aid = prepared.task.set_c[0]
        name = provider.get_description(aid)
        assert isinstance(name, str)
        assert len(name) > 0

    def test_resolve_kb(self, prepared_model, prepared):
        """Test resolve_kb maps assumption IDs to names and clauses (stateless:
        the describe provider is passed in)."""
        aid = prepared.task.set_c[0]
        names, clauses = prepared_model.resolve_kb(prepared.describe, [aid])
        assert len(names) == 1
        assert isinstance(names[0], str)
        assert len(clauses) > 0

    def test_resolve_kb_empty(self, prepared_model, prepared):
        """Test resolve_kb with empty list."""
        names, clauses = prepared_model.resolve_kb(prepared.describe, [])
        assert names == []
        assert clauses == []

    def test_prepare_task_is_pure(self, prepared_model, oracle):
        """prepare_task stores nothing on the model; two calls are independent."""
        p1 = prepared_model.prepare_task(QuAcqTaskInput(oracle.oracle_data))
        p2 = prepared_model.prepare_task(QuAcqTaskInput(oracle.oracle_data))
        assert p1.task.set_c == p2.task.set_c
        assert p1.task is not p2.task


class TestQuAcqWithAssumptionIDs:
    """Tests for QuAcq algorithm with QuAcqTask (assumption IDs)."""

    def test_quacq_learn_with_quacq_task(self, prepared_model, prepared, oracle, checker):
        """Test QuAcq learning with QuAcqTask and DescriptionProvider."""
        task = prepared.task
        task_data = _learn_params_from_task(task)

        query_provider = QueryProvider(checker=checker, model=prepared_model,
                                       assignment_map=prepared.assignment_map)
        discrim_gen = DiscriminatingGenerator(
            checker=checker, model=prepared_model,
            profiler=get_global_profiler(), root_assumption=task.set_b[0], task=task)

        quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen,
                                   model=prepared_model,
                                   task=task, assignment_map=prepared.assignment_map)
        result = quacq.learn(
            **task_data, mode='oracle',
            max_queries=5)

        assert result is not None
        assert result.n_queries <= 5
        assert isinstance(result.kb_assumption_ids, list)
        if result.kb_assumption_ids:
            names, _ = prepared_model.resolve_kb(prepared.describe, result.kb_assumption_ids)
            for name in names:
                assert isinstance(name, str)
        for aid in result.kb_assumption_ids:
            assert isinstance(aid, int)
        assert result.convergence_reason in [
            'empty_bias', 'max_queries', 'no_query']

    def test_quacq_empty_bias_quacq_task(self, oracle):
        """Test QuAcq with empty QuAcqTask converges immediately."""
        checker = _minimal_checker()
        query_provider = QueryProvider()
        discrim_gen = DiscriminatingGenerator(
            checker=checker, model=None,
            profiler=get_global_profiler(), root_assumption=0)

        quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)
        result = quacq.learn(
            set_c=[], set_b=[], negation_map={},
            mode='oracle', max_queries=100)

        assert result.n_queries == 0
        assert result.convergence_reason == 'empty_bias'
        assert result.kb_assumption_ids == []

    def test_result_resolved_via_model(self, prepared_model, prepared, oracle, checker):
        """Test result assumption IDs can be resolved via model."""
        task = prepared.task
        task_data = _learn_params_from_task(task)

        query_provider = QueryProvider(checker=checker, model=prepared_model,
                                       assignment_map=prepared.assignment_map)
        discrim_gen = DiscriminatingGenerator(
            checker=checker, model=prepared_model,
            profiler=get_global_profiler(), root_assumption=task.set_b[0], task=task)

        quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen,
                                   model=prepared_model,
                                   task=task, assignment_map=prepared.assignment_map)
        result = quacq.learn(
            **task_data, mode='oracle',
            max_queries=10)

        # Runner resolves names via model, not algorithm result
        if result.kb_assumption_ids:
            names, _ = prepared_model.resolve_kb(prepared.describe, result.kb_assumption_ids)
            assert len(names) == len(result.kb_assumption_ids)


class TestQuAcqResultAssumptionIDs:
    """Tests for QuAcqResult with assumption IDs."""

    def test_result_with_assumption_ids(self):
        """Test result creation with assumption IDs."""
        result = QuAcqResult(
            kb_assumption_ids=[10, 12],
            n_queries=5,
            convergence_reason='empty_bias'
        )
        assert result.kb_assumption_ids == [10, 12]
        assert result.n_queries == 5

    def test_n_kb_derived_from_len(self):
        """Test n_kb is derived from len(kb_assumption_ids)."""
        result = QuAcqResult(kb_assumption_ids=[10, 12, 14])
        assert len(result.kb_assumption_ids) == 3





class TestQueryProviderWithQuAcqTask:
    """Tests for QueryProvider with raw params from QuAcqTask."""

    def test_generate_from_sat_with_quacq_task(self, prepared_model, prepared, checker):
        """Test SAT query generation with raw params from QuAcqTask."""
        task = prepared.task
        provider = QueryProvider(checker=checker, model=prepared_model,
                                 assignment_map=prepared.assignment_map)
        remaining_bias = set(task.set_c)

        query, tested_c_id = provider.generate_from_sat(
            remaining_bias=remaining_bias,
            learned_kb=[],
            set_b=task.set_b,
            negation_map=task.negation_map)

        if query is not None:
            assert isinstance(query, dict)
            assert isinstance(tested_c_id, int)
            assert tested_c_id in remaining_bias


# =========================================================================
# DI / Factory / Mode validation tests
# =========================================================================

class TestQuAcqFactories:
    """Tests for QuAcq factory class methods."""

    def test_for_oracle_factory(self, oracle):
        """Test for_oracle factory injects all deps."""
        checker = _minimal_checker()
        query_provider = QueryProvider()
        discrim_gen = DiscriminatingGenerator(
            checker=checker, model=None,
            profiler=get_global_profiler(), root_assumption=0)
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


class TestQuAcqModeValidation:
    """Tests for mode validation in learn()."""

    def _minimal_learn_params(self):
        return dict(
            set_c=[], set_b=[], negation_map={})

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


class TestQueryProviderPoolFiltering:
    """Tests for QueryProvider pool filtering logic."""

    def test_pool_exhausted_when_empty(self):
        """Provider with no pool is immediately exhausted."""
        provider = QueryProvider()
        assert provider.pool_exhausted is True

    def test_pool_filtering_skips_invalid(self, prepared_model, prepared, checker):
        """Pool examples not satisfying KB+BG are skipped."""
        task = prepared.task
        features = list(prepared_model.name_to_id.keys())
        # All-false config almost certainly invalid (root must be true)
        invalid_config = {f: False for f in features}
        provider = QueryProvider(pool=[invalid_config], seed=42,
                                 checker=checker, model=prepared_model,
                                 assignment_map=prepared.assignment_map)
        query, c_id = provider.generate_from_pool(
            remaining_bias=set(task.set_c),
            learned_kb=[],
            set_b=task.set_b)
        assert query is None  # filtered out
        assert provider.pool_exhausted is True


class TestSatUtils:
    """Tests for sat_utils standalone functions."""

    def test_get_constraint_vars(self):
        model = QuAcqModel()
        model.id_to_name = {1: 'a', 2: 'b', 3: 'c'}
        # Stateless: the task is passed in, not stored on the model.
        task = QuAcqTask(constraint_clauses={10: [[1, -2], [3]]})
        result = model.get_constraint_vars(task, 10)
        assert result == {'a', 'b', 'c'}

    def test_get_constraint_vars_missing(self):
        model = QuAcqModel()
        model.id_to_name = {}
        task = QuAcqTask(constraint_clauses={})
        result = model.get_constraint_vars(task, 99)
        assert result == set()

    def test_get_constraints_with_scope_exact(self):
        constraint_clauses = {10: [[1, -2]], 12: [[1]]}
        scope = {'a', 'b'}
        # Build minimal model with synthetic task (passed in, not stored)
        model = QuAcqModel()
        model.id_to_name = {1: 'a', 2: 'b'}
        task = QuAcqTask(constraint_clauses=constraint_clauses)
        result = model.get_constraints_with_scope(task, scope, {10, 12})
        assert result == [10]  # exact match

    def test_get_constraints_with_scope_subset(self):
        constraint_clauses = {10: [[1]], 12: [[2]]}
        scope = {'a', 'b'}
        # Build minimal model with synthetic task (passed in, not stored)
        model = QuAcqModel()
        model.id_to_name = {1: 'a', 2: 'b'}
        task = QuAcqTask(constraint_clauses=constraint_clauses)
        result = model.get_constraints_with_scope(task, scope, {10, 12})
        # No exact match, both are subsets
        assert set(result) == {10, 12}



# =========================================================================
# Part 4 data flow tests
# =========================================================================

class TestBGDataPart4:
    """Tests for BGData Part 4 fields."""

    def test_bgdata_part4_populated(self, oracle):
        """BGData Part 4 fields populated after oracle prepare."""
        bg_data = oracle.oracle_data.get_bg_data()
        assert len(bg_data.assignment_clauses) > 0
        assert len(bg_data.assignment_assumptions) > 0
        assert len(bg_data.pos_assignment_to_assumption) > 0
        assert len(bg_data.neg_assignment_to_assumption) > 0
        # Each feature should have pos and neg entry
        assert (len(bg_data.pos_assignment_to_assumption) ==
                len(bg_data.neg_assignment_to_assumption))

    def test_bgdata_part4_default_empty(self):
        """BGData Part 4 fields default to empty."""
        from conacq.oracle.bg_data import BGData
        bg = BGData(set_kb=[], assumptions=(1, 2),
                    negation_map={}, descriptions={},
                    next_available_id=10)
        assert bg.assignment_clauses == []
        assert bg.assignment_assumptions == []
        assert bg.pos_assignment_to_assumption == {}
        assert bg.neg_assignment_to_assumption == {}


class TestQuAcqTaskPart4:
    """Tests for QuAcqTask Part 4 fields."""


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
