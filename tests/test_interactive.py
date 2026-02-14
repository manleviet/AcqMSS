"""
Tests for Interactive (QuAcq) constraint acquisition algorithm.

Uses REAL-FM-7 feature model with generated bias.
Tests core components: QueryGenerator, QuAcq, InteractiveLearner.
"""

import pytest
from pathlib import Path

from acqmss.oracle import FeatureModelOracle, Oracle, CachedOracle
from acqmss.bias import BiasIO
from acqmss.algorithms.interactive import (
    InteractiveTask,
    InteractiveResult,
    QuAcq,
    InteractiveLearner,
)
from acqmss.example_generators import QueryGenerator
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
def interactive_task(oracle, bias):
    """Create InteractiveTask from oracle and bias."""
    feature_ids = oracle.get_feature_ids()
    id_to_feature = {v: k for k, v in feature_ids.items()}

    constraint_map = bias.to_constraint_map()
    negated_constraint_map = {}
    for constraint in bias.constraints:
        if constraint.clauses:
            negated_constraint_map[constraint.id] = [[-lit] for lit in constraint.clauses[0]]

    task = InteractiveTask(
        bias=[c.id for c in bias.constraints],
        learned_kb=[],
        background=[],
        feature_ids=feature_ids,
        id_to_feature=id_to_feature,
        constraint_map=constraint_map,
        negated_constraint_map=negated_constraint_map
    )

    return task


class TestInteractiveTask:
    """Tests for InteractiveTask data structure."""

    def test_task_creation(self, interactive_task):
        """Test task can be created with correct structure."""
        assert len(interactive_task.bias) > 0
        assert len(interactive_task.learned_kb) == 0
        assert len(interactive_task.feature_ids) > 0
        assert len(interactive_task.constraint_map) == len(interactive_task.bias)

    def test_add_to_kb(self, interactive_task):
        """Test adding constraint to KB."""
        c_id = next(iter(interactive_task.bias))
        interactive_task.add_to_kb(c_id)

        assert c_id in interactive_task.learned_kb
        assert len(interactive_task.learned_kb) == 1

    def test_remove_from_bias(self, interactive_task):
        """Test removing constraints from bias."""
        initial_size = len(interactive_task.bias)
        bias_iter = iter(interactive_task.bias)
        to_remove = [next(bias_iter), next(bias_iter)]
        interactive_task.remove_from_bias(to_remove)

        assert len(interactive_task.bias) == initial_size - 2
        for c_id in to_remove:
            assert c_id not in interactive_task.bias

    def test_record_query(self, interactive_task):
        """Test recording queries."""
        config = {'feature1': True, 'feature2': False}
        interactive_task.record_query(config, True)

        assert interactive_task.n_queries == 1
        assert len(interactive_task.query_history) == 1
        assert interactive_task.query_history[0] == (config, True)

    def test_get_kb_clauses(self, interactive_task):
        """Test getting KB clauses."""
        # Add some constraints to KB
        bias_iter = iter(interactive_task.bias)
        interactive_task.add_to_kb(next(bias_iter))
        interactive_task.add_to_kb(next(bias_iter))

        clauses = interactive_task.get_kb_clauses()
        assert isinstance(clauses, list)
        assert len(clauses) > 0

    def test_clone(self, interactive_task):
        """Test cloning task."""
        cloned = interactive_task.clone()

        assert cloned.bias == interactive_task.bias
        assert cloned.learned_kb == interactive_task.learned_kb
        assert cloned is not interactive_task


class TestInteractiveResult:
    """Tests for InteractiveResult data structure."""

    def test_result_creation(self):
        """Test result can be created."""
        result = InteractiveResult(
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
        result = InteractiveResult(
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
        result = InteractiveResult(
            kb_constraints=['c1', 'c2'],
            n_queries=10,
            n_kb=2,
            convergence_reason='empty_bias',
            runtime_ms=100.5,
            query_history=[({'f1': True}, True), ({'f1': False}, False)]
        )

        filepath = tmp_path / "result.json"
        result.save(str(filepath))

        loaded = InteractiveResult.load(str(filepath))
        assert loaded.n_queries == result.n_queries
        assert loaded.n_kb == result.n_kb
        assert loaded.kb_constraints == result.kb_constraints


class TestFeatureModelOracle:
    """Tests for FeatureModelOracle."""

    def test_oracle_creation(self, oracle):
        """Test oracle can be created."""
        assert oracle.get_feature_count() > 0

    def test_oracle_valid_config(self, oracle):
        """Test oracle accepts valid configuration."""
        # Get a valid configuration directly from oracle
        valid_config = oracle.get_valid_configuration()
        if valid_config:
            assert oracle.ask(valid_config) is True

    def test_oracle_invalid_config(self, oracle):
        """Test oracle rejects invalid configuration."""
        # Create an invalid config (all features false including root)
        features = oracle.get_features()
        invalid_config = {f: False for f in features}
        assert oracle.ask(invalid_config) is False


class TestCachedOracle:
    """Tests for CachedOracle."""

    def test_cached_oracle_caches_results(self, oracle):
        """Test cached oracle caches results."""
        cached = CachedOracle(oracle)

        # First query
        config = {'A': True}
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

    def test_generate_query(self, interactive_task):
        """Test query generation."""
        gen = QueryGenerator()
        query, tested_c_id = gen.generate(interactive_task)

        # Should generate a query when bias is not empty
        if interactive_task.bias:
            # Query generation may succeed or fail depending on constraints
            # Just verify the types are correct
            if query is not None:
                assert isinstance(query, dict)
                assert tested_c_id is not None
                assert tested_c_id in interactive_task.bias


class TestQuAcq:
    """Tests for QuAcq algorithm."""

    def test_quacq_creation(self):
        """Test QuAcq can be created."""
        quacq = QuAcq()
        assert quacq.solver_name == 'glucose4'

    def test_quacq_learn_with_limit(self, interactive_task, oracle, bias):
        """Test QuAcq learning with query limit."""
        # Use a small query limit for testing
        quacq = QuAcq()
        result = quacq.learn(interactive_task, oracle, max_queries=5)

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
                # print constraints by bias.get_constraint_by_id() for readability
                constraint = bias.get_constraint_by_id(c)
                print(f"  Constraint: {constraint} (ID: {c})")

    def test_quacq_empty_bias(self, oracle):
        """Test QuAcq with empty bias converges immediately."""
        task = InteractiveTask(
            bias=[],
            learned_kb=[],
            background=[],
            feature_ids={'root': 1},
            id_to_feature={1: 'root'},
            constraint_map={},
            negated_constraint_map={}
        )

        quacq = QuAcq()
        result = quacq.learn(task, oracle, max_queries=100)

        assert result.n_queries == 0
        assert result.convergence_reason == 'empty_bias'


class TestInteractiveLearner:
    """Tests for InteractiveLearner high-level interface."""

    def test_learner_from_files(self):
        """Test learner creation from files."""
        if not FM_PATH.exists() or not BIAS_PATH.exists():
            pytest.skip("Test data files not found")

        learner = InteractiveLearner.from_files(
            fm_path=str(FM_PATH),
            bias_path=str(BIAS_PATH),
            enable_profiling=False
        )

        assert learner.task is not None
        assert len(learner.task.bias) > 0
        assert learner.oracle is not None

        # Verify root feature ID in background
        assert len(learner.task.background) > 0, "Background should contain root"
        root_name = learner.oracle.get_root_feature()
        root_id = learner.oracle.get_feature_ids()[root_name]
        assert root_id in learner.task.background, "Root feature ID should be in background"

    def test_build_task_from_bias_includes_root(self):
        """Verify _build_task_from_bias sets background with root."""
        if not FM_PATH.exists() or not BIAS_PATH.exists():
            pytest.skip("Test data files not found")

        oracle = FeatureModelOracle(str(FM_PATH))
        bias = BiasIO.load_from_json(str(BIAS_PATH))

        task = InteractiveLearner._build_task_from_bias(bias, oracle)

        root_name = oracle.get_root_feature()
        root_id = oracle.get_feature_ids()[root_name]
        assert task.background == [root_id], \
            f"Expected background=[{root_id}], got {task.background}"

    def test_learner_learn_automated(self):
        """Test learner in automated mode."""
        if not FM_PATH.exists() or not BIAS_PATH.exists():
            pytest.skip("Test data files not found")

        learner = InteractiveLearner.from_files(
            fm_path=str(FM_PATH),
            bias_path=str(BIAS_PATH),
            enable_profiling=False
        )

        result = learner.learn(mode='automated', max_queries=10)

        assert result is not None
        assert result.n_queries <= 10

        print(f"\nInteractiveLearner Result:")
        print(f"  Queries: {result.n_queries}")
        print(f"  KB size: {result.n_kb}")
        print(f"  Convergence: {result.convergence_reason}")
        print(f"  Runtime: {result.runtime_ms:.2f} ms")


class TestIntegration:
    """Integration tests for full learning pipeline."""

    @pytest.mark.slow
    def test_full_learning_small_limit(self):
        """Test full learning with small query limit."""
        if not FM_PATH.exists() or not BIAS_PATH.exists():
            pytest.skip("Test data files not found")

        # Enable profiling
        profiler = use_global_profiler(ProfilerPreset.BENCHMARK)
        profiler.start()

        try:
            learner = InteractiveLearner.from_files(
                fm_path=str(FM_PATH),
                bias_path=str(BIAS_PATH)
            )

            result = learner.learn(mode='automated', max_queries=50)

            assert result is not None
            assert result.n_queries <= 50

            print(f"\nFull Learning Result (max_queries=50):")
            print(f"  Queries: {result.n_queries}")
            print(f"  KB size: {result.n_kb}")
            print(f"  Convergence: {result.convergence_reason}")
            print(f"  Runtime: {result.runtime_ms:.2f} ms")

            if result.kb_constraints:
                print(f"  Constraints: {result.kb_constraints[:5]}...")

        finally:
            profiler.stop()


class TestEvaluation:
    """Tests for evaluation functionality."""

    def test_evaluation_result_field(self):
        """Test that InteractiveResult has evaluation field."""
        result = InteractiveResult(
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
        result = InteractiveResult(
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
        result = InteractiveResult(
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

        loaded = InteractiveResult.load(str(filepath))
        assert loaded.evaluation is not None
        assert loaded.evaluation['description']['metrics']['accuracy'] == 0.95
        assert loaded.evaluation['clause']['metrics']['accuracy'] == 0.92

    def test_learner_evaluate(self):
        """Test InteractiveLearner.evaluate() method."""
        if not FM_PATH.exists() or not BIAS_PATH.exists():
            pytest.skip("Test data files not found")

        learner = InteractiveLearner.from_files(
            fm_path=str(FM_PATH),
            bias_path=str(BIAS_PATH),
            enable_profiling=False
        )

        # Run with small limit
        result = learner.learn(mode='automated', max_queries=20)

        # Evaluate
        evaluation = learner.evaluate(result)

        assert evaluation is not None
        assert 'description' in evaluation
        assert 'clause' in evaluation

        # Check description-based metrics
        desc = evaluation['description']
        assert 'metrics' in desc
        assert 'accuracy' in desc['metrics']
        assert 'precision' in desc['metrics']
        assert 'recall' in desc['metrics']
        assert 'f1_score' in desc['metrics']

        # Check clause-based metrics
        clause = evaluation['clause']
        assert 'metrics' in clause
        assert 'accuracy' in clause['metrics']
        assert 'precision' in clause['metrics']
        assert 'recall' in clause['metrics']
        assert 'f1_score' in clause['metrics']

        # Result should have evaluation stored
        assert result.evaluation is not None
        assert result.evaluation == evaluation

        print(f"\nEvaluation Results:")
        print(f"  Description-based:")
        print(f"    Accuracy:  {desc['metrics']['accuracy']:.4f}")
        print(f"    Precision: {desc['metrics']['precision']:.4f}")
        print(f"    Recall:    {desc['metrics']['recall']:.4f}")
        print(f"    F1 Score:  {desc['metrics']['f1_score']:.4f}")
        print(f"  Clause-based:")
        print(f"    Accuracy:  {clause['metrics']['accuracy']:.4f}")
        print(f"    Precision: {clause['metrics']['precision']:.4f}")
        print(f"    Recall:    {clause['metrics']['recall']:.4f}")
        print(f"    F1 Score:  {clause['metrics']['f1_score']:.4f}")

    def test_learner_evaluate_requires_paths(self):
        """Test that evaluate raises error when paths not available."""
        # Create learner without file paths
        task = InteractiveTask(
            bias=[],
            learned_kb=[],
            background=[],
            feature_ids={'root': 1},
            id_to_feature={1: 'root'},
            constraint_map={},
            negated_constraint_map={}
        )
        learner = InteractiveLearner(task=task)

        result = InteractiveResult(
            kb_constraints=[],
            n_queries=0,
            n_kb=0,
            convergence_reason='empty_bias',
            runtime_ms=0.0
        )

        with pytest.raises(ValueError, match="FM path and bias path are required"):
            learner.evaluate(result)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
