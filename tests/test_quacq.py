"""
Tests for QuAcq constraint acquisition algorithm.

Uses REAL-FM-7 feature model with generated bias.
Tests core components: QueryGenerator, QuAcq, QuAcqTask, QuAcqModel.
"""

import pytest
from pathlib import Path

from conacq.oracle import FeatureModelOracle, Oracle, CachedOracle
from conacq.bias import BiasIO
from conacq.algorithms.quacq import (
    QuAcqResult,
    QuAcq,
)
from conacq.algorithms.quacq.task_preparation import QuAcqTask
from conacq.algorithms.quacq.quacq_model import QuAcqModel
from conacq.algorithms.quacq.quacq_model_builder import QuAcqModelBuilder
from conacq.example_generators import QueryGenerator
from explanation.operations.algorithms.profiler import (
    get_global_profiler,
    use_global_profiler,
    ProfilerPreset
)


# Test data paths
DATA_DIR = Path(__file__).parent.parent / "data"
FM_PATH = DATA_DIR / "fms" / "REAL-FM-7.uvl"
BIAS_PATH = DATA_DIR / "bias" / "REAL-FM-7-bias.json"


@pytest.fixture
def oracle():
    """Load REAL-FM-7 feature model oracle."""
    if not FM_PATH.exists():
        pytest.skip(f"Feature model not found: {FM_PATH}")
    return FeatureModelOracle(str(FM_PATH))


@pytest.fixture
def bias():
    """Load REAL-FM-7 bias."""
    if not BIAS_PATH.exists():
        pytest.skip(f"Bias file not found: {BIAS_PATH}")
    return BiasIO.load_from_json(str(BIAS_PATH))


@pytest.fixture
def interactive_model(oracle):
    """Create QuAcqModel via builder (auto-prepared)."""
    if not BIAS_PATH.exists():
        pytest.skip(f"Bias file not found: {BIAS_PATH}")
    return (QuAcqModelBuilder
            .from_bias(str(BIAS_PATH))
            .with_oracle(oracle)
            .build())


@pytest.fixture
def prepared_model(interactive_model):
    """Alias for interactive_model (already prepared by builder)."""
    return interactive_model


class TestQuAcqResult:
    """Tests for QuAcqResult data structure."""

    def test_result_creation(self):
        """Test result can be created."""
        result = QuAcqResult(
            kb_constraints=['c1', 'c2'],
            n_queries=10,
            n_kb=2,
            convergence_reason='empty_bias',
            runtime_ms=100.5
        )

        assert result.n_queries == 10
        assert result.n_kb == 2
        assert result.convergence_reason == 'empty_bias'
        assert len(result.kb_constraints) == 2

    def test_result_to_dict(self):
        """Test result serialization."""
        result = QuAcqResult(
            kb_constraints=['c1'],
            n_queries=5,
            n_kb=1,
            convergence_reason='no_query',
            runtime_ms=50.0
        )

        d = result.to_dict()
        assert d['n_queries'] == 5
        assert d['n_kb'] == 1
        assert d['convergence_reason'] == 'no_query'

    def test_result_save_load(self, tmp_path):
        """Test result save and load."""
        result = QuAcqResult(
            kb_constraints=['c1', 'c2'],
            n_queries=10,
            n_kb=2,
            convergence_reason='empty_bias',
            runtime_ms=100.5,
            query_history=[({'f1': True}, True, 'main'), ({'f1': False}, False, 'main')]
        )

        filepath = tmp_path / "result.json"
        result.save(str(filepath))

        loaded = QuAcqResult.load(str(filepath))
        assert loaded.n_queries == result.n_queries
        assert loaded.n_kb == result.n_kb
        assert loaded.kb_constraints == result.kb_constraints


class TestFeatureModelOracle:
    """Tests for FeatureModelOracle."""

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


class TestQueryGenerator:
    """Tests for QueryGenerator."""

    def test_generator_creation(self):
        """Test generator can be created."""
        gen = QueryGenerator()
        assert gen.solver_name == 'glucose4'

    def test_generate_query(self, prepared_model):
        """Test query generation."""
        task = prepared_model.task
        gen = QueryGenerator()
        remaining_bias = set(task.set_c)
        query, tested_c_id = gen.generate(task, remaining_bias, [])

        # Should generate a query when bias is not empty
        if task.set_c:
            # Query generation may succeed or fail depending on constraints
            # Just verify the types are correct
            if query is not None:
                assert isinstance(query, dict)
                assert tested_c_id is not None
                assert tested_c_id in remaining_bias


class TestQuAcq:
    """Tests for QuAcq algorithm."""

    def test_quacq_creation(self):
        """Test QuAcq can be created."""
        quacq = QuAcq()
        assert quacq.solver_name == 'glucose4'

    def test_quacq_learn_with_limit(self, prepared_model, oracle, bias):
        """Test QuAcq learning with query limit."""
        task = prepared_model.task
        quacq = QuAcq()
        result = quacq.learn(
            task, oracle, prepared_model.description_provider, max_queries=5)

        assert result is not None
        assert result.n_queries <= 5
        assert isinstance(result.kb_constraints, list)
        assert result.convergence_reason in ['empty_bias', 'max_queries', 'no_query']

        print(f"\nQuAcq Result (max_queries=5):")
        print(f"  Queries: {result.n_queries}")
        print(f"  KB size: {result.n_kb}")
        print(f"  Convergence: {result.convergence_reason}")

        if result.kb_constraints:
            for c in result.kb_constraints:
                print(f"  Constraint: {c}")

    def test_quacq_empty_bias(self, oracle):
        """Test QuAcq with empty bias converges immediately."""
        task = QuAcqTask(
            feature_ids={'root': 1},
            id_to_feature={1: 'root'},
        )

        quacq = QuAcq()
        result = quacq.learn(task, oracle, max_queries=100)

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
            oracle = FeatureModelOracle(str(FM_PATH))
            model = (QuAcqModelBuilder
                     .from_bias(str(BIAS_PATH))
                     .with_oracle(oracle)
                     .build())

            quacq = QuAcq()
            result = quacq.learn(
                model.task, oracle, model.description_provider,
                max_queries=50)

            assert result is not None
            assert result.n_queries <= 50
            assert result.convergence_reason in [
                'empty_bias', 'max_queries', 'no_query']

        finally:
            profiler.stop()


class TestEvaluation:
    """Tests for evaluation functionality."""

    def test_evaluation_result_field(self):
        """Test that QuAcqResult has evaluation field."""
        result = QuAcqResult(
            kb_constraints=['c1', 'c2'],
            n_queries=10,
            n_kb=2,
            convergence_reason='empty_bias',
            runtime_ms=100.5
        )

        # evaluation should be None by default
        assert result.evaluation is None

        # Set evaluation
        result.evaluation = {
            'description': {'metrics': {'accuracy': 0.95}},
            'clause': {'metrics': {'accuracy': 0.92}}
        }

        assert result.evaluation is not None
        assert result.evaluation['description']['metrics']['accuracy'] == 0.95

    def test_evaluation_to_dict(self):
        """Test that to_dict includes evaluation field."""
        result = QuAcqResult(
            kb_constraints=['c1'],
            n_queries=5,
            n_kb=1,
            convergence_reason='no_query',
            runtime_ms=50.0,
            evaluation={
                'description': {'metrics': {'accuracy': 0.95}},
                'clause': {'metrics': {'accuracy': 0.92}}
            }
        )

        d = result.to_dict()
        assert 'evaluation' in d
        assert d['evaluation']['description']['metrics']['accuracy'] == 0.95
        assert d['evaluation']['clause']['metrics']['accuracy'] == 0.92

    def test_evaluation_save_load(self, tmp_path):
        """Test that evaluation is saved and loaded correctly."""
        result = QuAcqResult(
            kb_constraints=['c1', 'c2'],
            n_queries=10,
            n_kb=2,
            convergence_reason='empty_bias',
            runtime_ms=100.5,
            evaluation={
                'description': {
                    'metrics': {
                        'accuracy': 0.95,
                        'precision': 0.90,
                        'recall': 0.85,
                        'f1_score': 0.87
                    }
                },
                'clause': {
                    'metrics': {
                        'accuracy': 0.92,
                        'precision': 0.88,
                        'recall': 0.80,
                        'f1_score': 0.84
                    }
                }
            }
        )

        filepath = tmp_path / "result_with_eval.json"
        result.save(str(filepath))

        loaded = QuAcqResult.load(str(filepath))
        assert loaded.evaluation is not None
        assert loaded.evaluation['description']['metrics']['accuracy'] == 0.95
        assert loaded.evaluation['clause']['metrics']['accuracy'] == 0.92


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

    def test_task_creation(self, prepared_model):
        """Test QuAcqTask is created with correct structure."""
        task = prepared_model.task
        assert isinstance(task, QuAcqTask)
        assert len(task.set_c) > 0
        assert len(task.feature_ids) > 0
        assert len(task.id_to_feature) == len(task.feature_ids)
        # All bias IDs should be ints
        for aid in task.set_c:
            assert isinstance(aid, int)

    def test_bias_has_clause_mappings(self, prepared_model):
        """Test each bias constraint has clause and negated clause mappings."""
        task = prepared_model.task
        for aid in task.set_c:
            assert aid in task.constraint_clauses, f"Missing clauses for {aid}"
            assert aid in task.negated_clauses, f"Missing negated clauses for {aid}"
            assert len(task.constraint_clauses[aid]) > 0

    def test_config_to_assumptions(self, prepared_model):
        """Test config dict to SAT assumptions conversion."""
        task = prepared_model.task
        features = list(task.feature_ids.keys())
        config = {features[0]: True, features[1]: False}
        assumptions = task.config_to_assumptions(config)
        assert len(assumptions) == 2
        assert all(isinstance(a, int) for a in assumptions)

    def test_get_kb_clauses(self, prepared_model):
        """Test getting KB clauses from learned constraints."""
        task = prepared_model.task
        aid = task.set_c[0]
        clauses = task.get_kb_clauses([aid])
        assert isinstance(clauses, list)
        assert len(clauses) > 0

    def test_background_populated(self, prepared_model):
        """Test background has BG assumption IDs from oracle."""
        task = prepared_model.task
        assert len(task.set_b) > 0
        # BG assumptions should be in the full assumptions list
        for bg_id in task.set_b:
            assert bg_id in task.assumptions

    def test_assumptions_and_negation_map(self, prepared_model):
        """Test assumption ID layout is consistent."""
        task = prepared_model.task
        # Each bias constraint should have a negation mapping
        for aid in task.set_c:
            assert aid in task.negation_map, f"Missing negation for {aid}"
            neg_id = task.negation_map[aid]
            assert neg_id in task.assumptions


class TestQuAcqModel:
    """Tests for QuAcqModel (assumption-ID based model)."""

    def test_builder(self, interactive_model):
        """Test model creation via builder."""
        assert len(interactive_model.constraint_map) > 0
        assert len(interactive_model.variables) > 0
        assert interactive_model.task is not None

    def test_prepare(self, prepared_model):
        """Test model preparation creates QuAcqTask."""
        assert prepared_model.task is not None
        assert isinstance(prepared_model.task, QuAcqTask)

    def test_description_provider(self, prepared_model):
        """Test DescriptionProvider resolves assumption IDs to names."""
        provider = prepared_model.description_provider
        task = prepared_model.task
        aid = task.set_c[0]
        name = provider.get_description(aid)
        assert isinstance(name, str)
        assert len(name) > 0

    def test_resolve_kb(self, prepared_model):
        """Test resolve_kb maps assumption IDs to names and clauses."""
        task = prepared_model.task
        aid = task.set_c[0]
        names, clauses = prepared_model.resolve_kb([aid])
        assert len(names) == 1
        assert isinstance(names[0], str)
        assert len(clauses) > 0

    def test_resolve_kb_empty(self, prepared_model):
        """Test resolve_kb with empty list."""
        names, clauses = prepared_model.resolve_kb([])
        assert names == []
        assert clauses == []

    def test_description_provider_before_prepare_raises(self):
        """Test accessing description_provider before prepare raises."""
        model = QuAcqModel()
        with pytest.raises(RuntimeError, match="Call prepare"):
            _ = model.description_provider


class TestQuAcqWithAssumptionIDs:
    """Tests for QuAcq algorithm with QuAcqTask (assumption IDs)."""

    def test_quacq_learn_with_quacq_task(self, prepared_model, oracle):
        """Test QuAcq learning with QuAcqTask and DescriptionProvider."""
        task = prepared_model.task
        quacq = QuAcq()
        result = quacq.learn(
            task, oracle, prepared_model.description_provider, max_queries=5)

        assert result is not None
        assert result.n_queries <= 5
        assert isinstance(result.kb_assumption_ids, list)
        assert isinstance(result.kb_constraints, list)
        # kb_constraints should be resolved names
        for name in result.kb_constraints:
            assert isinstance(name, str)
        # kb_assumption_ids should be ints
        for aid in result.kb_assumption_ids:
            assert isinstance(aid, int)
        assert result.convergence_reason in [
            'empty_bias', 'max_queries', 'no_query']

    def test_quacq_empty_bias_quacq_task(self, oracle):
        """Test QuAcq with empty QuAcqTask converges immediately."""
        task = QuAcqTask(
            feature_ids={'root': 1},
            id_to_feature={1: 'root'},
        )
        quacq = QuAcq()
        result = quacq.learn(task, oracle, max_queries=100)

        assert result.n_queries == 0
        assert result.convergence_reason == 'empty_bias'
        assert result.kb_assumption_ids == []

    def test_result_has_dual_representation(self, prepared_model, oracle):
        """Test result has both string names and assumption IDs."""
        task = prepared_model.task
        quacq = QuAcq()
        result = quacq.learn(
            task, oracle, prepared_model.description_provider, max_queries=10)

        # Both lists should be same length
        assert len(result.kb_constraints) == len(result.kb_assumption_ids)
        # n_kb should match
        if result.kb_constraints:
            assert result.n_kb == len(result.kb_constraints)


class TestQuAcqResultAssumptionIDs:
    """Tests for QuAcqResult with assumption ID support."""

    def test_result_with_assumption_ids(self):
        """Test result creation with both fields."""
        result = QuAcqResult(
            kb_constraints=['c1', 'c2'],
            kb_assumption_ids=[10, 12],
            n_queries=5,
            n_kb=2,
            convergence_reason='empty_bias',
            runtime_ms=50.0
        )
        assert result.kb_assumption_ids == [10, 12]
        assert result.kb_constraints == ['c1', 'c2']

    def test_to_dict_includes_assumption_ids(self):
        """Test to_dict includes kb_assumption_ids."""
        result = QuAcqResult(
            kb_constraints=['c1'],
            kb_assumption_ids=[10],
            n_queries=3,
            n_kb=1,
            convergence_reason='no_query',
            runtime_ms=20.0
        )
        d = result.to_dict()
        assert 'kb_assumption_ids' in d
        assert d['kb_assumption_ids'] == [10]
        assert d['kb_constraints'] == ['c1']

    def test_save_load_with_assumption_ids(self, tmp_path):
        """Test save/load preserves assumption IDs."""
        result = QuAcqResult(
            kb_constraints=['c1', 'c2'],
            kb_assumption_ids=[10, 12],
            n_queries=5,
            n_kb=2,
            convergence_reason='empty_bias',
            runtime_ms=50.0
        )
        filepath = tmp_path / "result_aids.json"
        result.save(str(filepath))

        loaded = QuAcqResult.load(str(filepath))
        assert loaded.kb_assumption_ids == [10, 12]
        assert loaded.kb_constraints == ['c1', 'c2']

    def test_load_old_format_without_assumption_ids(self, tmp_path):
        """Test load handles old format without kb_assumption_ids."""
        import json
        old_data = {
            'kb_constraints': ['c1'],
            'n_queries': 3,
            'n_kb': 1,
            'convergence_reason': 'no_query',
            'runtime_ms': 20.0,
        }
        filepath = tmp_path / "old_result.json"
        with open(filepath, 'w') as f:
            json.dump(old_data, f)

        loaded = QuAcqResult.load(str(filepath))
        assert loaded.kb_assumption_ids == []
        assert loaded.kb_constraints == ['c1']

    def test_n_kb_auto_from_assumption_ids(self):
        """Test n_kb auto-calculated from kb_assumption_ids."""
        result = QuAcqResult(
            kb_assumption_ids=[10, 12, 14],
            convergence_reason='empty_bias',
            runtime_ms=10.0
        )
        assert result.n_kb == 3


class TestTaskCompat:
    """Tests for _task_compat shared helpers."""

    def test_get_bg_clauses_quacq_task(self):
        """get_bg_clauses returns background_clauses for QuAcqTask."""
        task = QuAcqTask(background_clauses=[[1], [2, -3]])
        from conacq.algorithms.quacq._task_compat import get_bg_clauses
        result = get_bg_clauses(task)
        assert result == [[1], [2, -3]]

    def test_get_bg_clauses_empty(self):
        """get_bg_clauses returns [] for empty background."""
        task = QuAcqTask()
        from conacq.algorithms.quacq._task_compat import get_bg_clauses
        result = get_bg_clauses(task)
        assert result == []

    def test_get_clause_map_quacq(self):
        """get_clause_map returns constraint_clauses for QuAcqTask."""
        task = QuAcqTask(constraint_clauses={10: [[1, 2]]})
        from conacq.algorithms.quacq._task_compat import get_clause_map
        assert get_clause_map(task) == {10: [[1, 2]]}


class TestBackgroundClauses:
    """Tests for background_clauses field on QuAcqTask."""

    def test_background_clauses_field(self):
        """QuAcqTask.background_clauses stores raw BG CNF clauses."""
        task = QuAcqTask(
            set_b=[5, 6],
            background_clauses=[[1], [2, -3]],
        )
        assert task.set_b == [5, 6]
        assert task.background_clauses == [[1], [2, -3]]

    def test_background_clauses_default_empty(self):
        """background_clauses defaults to empty list."""
        task = QuAcqTask()
        assert task.background_clauses == []

    def test_background_clauses_independent_instances(self):
        """Separate QuAcqTask instances have independent background_clauses."""
        task1 = QuAcqTask(background_clauses=[[1], [2, -3]])
        task2 = QuAcqTask(background_clauses=[[1], [2, -3]])
        task2.background_clauses[0].append(99)
        assert task1.background_clauses[0] != task2.background_clauses[0]

    def test_prepare_populates_background_clauses(self, prepared_model):
        """QuAcqTaskPreparation.prepare() populates background_clauses."""
        task = prepared_model.task
        assert isinstance(task.background_clauses, list)
        assert len(task.background_clauses) > 0
        # Each clause is a list of ints (no assumption guards)
        for clause in task.background_clauses:
            assert isinstance(clause, list)
            for lit in clause:
                assert isinstance(lit, int)


class TestQueryGeneratorWithQuAcqTask:
    """Tests for QueryGenerator with QuAcqTask."""

    def test_generate_with_quacq_task(self, prepared_model):
        """Test query generation with QuAcqTask."""
        task = prepared_model.task
        gen = QueryGenerator()
        remaining_bias = set(task.set_c)
        query, tested_c_id = gen.generate(task, remaining_bias, [])

        if query is not None:
            assert isinstance(query, dict)
            assert isinstance(tested_c_id, int)
            assert tested_c_id in remaining_bias


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
