"""
Tests for CONGEN constraint acquisition algorithm.

Uses REAL-FM-7 feature model with generated bias and examples.
Supports both incremental and non-incremental solver modes.
"""

import pytest
from pathlib import Path
from parameterized import parameterized

from acqmss.testcases import FeatureModelOracle, ExampleIO
from acqmss.bias import BiasIO
from acqmss.algorithms import (
    CONGEN, ACQMSS, Reduce, GenerateNE,
    CONGENModel,
    IncrementalCONGENTaskPreparation,
    NonIncrementalCONGENTaskPreparation
)
from explanation.operations.algorithms.checker import (
    IncrementalPySATChecker,
    NonIncrementalPySATChecker
)
from explanation.operations.algorithms.profiler import get_global_profiler


# Test data paths
DATA_DIR = Path(__file__).parent.parent / "data"
FM_PATH = DATA_DIR / "fms" / "REAL-FM-7.uvl"
BIAS_PATH = DATA_DIR / "bias" / "REAL-FM-7-bias.json"
EXAMPLES_RS_1N_PATH = DATA_DIR / "examples" / "REAL-FM-7_rs_1n.json"
EXAMPLES_FF_PATH = DATA_DIR / "examples" / "REAL-FM-7_ff.json"


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
def examples_rs():
    """Load REAL-FM-7 examples (RS 1n)."""
    if not EXAMPLES_RS_1N_PATH.exists():
        pytest.skip(f"Examples file not found: {EXAMPLES_RS_1N_PATH}")
    return ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))


@pytest.fixture
def examples_ff():
    """Load REAL-FM-7 examples (FF)."""
    if not EXAMPLES_FF_PATH.exists():
        pytest.skip(f"Examples file not found: {EXAMPLES_FF_PATH}")
    return ExampleIO.load_json(str(EXAMPLES_FF_PATH))


def create_checker_and_task(oracle, bias, examples, is_incremental=True):
    """Helper to create checker and task for tests.

    Args:
        oracle: FeatureModelOracle
        bias: Bias from BiasIO
        examples: Examples from ExampleIO
        is_incremental: Use incremental mode

    Returns:
        Tuple of (checker, task, profiler, root_id)
    """
    # Convert bias to constraint dict
    bias_constraints = {c.id: c.clauses for c in bias.constraints}

    # Convert examples to dict format
    positive_examples = [e.assignments for e in examples.positive]
    negative_examples = [e.assignments for e in examples.negative]

    # Extract root feature ID for background knowledge
    root_name = oracle.get_root_feature()
    root_id = oracle.get_feature_ids()[root_name]

    # Create model
    model = CONGENModel.from_bias_and_examples(
        bias_constraints=bias_constraints,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
        feature_ids=oracle.get_feature_ids(),
        root_feature_id=root_id
    )

    profiler = get_global_profiler()

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
        # NonIncrementalPySATChecker doesn't take KB - creates fresh solver per check
        checker = NonIncrementalPySATChecker('glucose4', profiler)

    return checker, task, profiler, root_id


class TestCONGEN:
    """Tests for main CONGEN algorithm."""

    def test_congen_incremental_with_rs_examples(self, oracle, bias, examples_rs):
        """Test CONGEN incremental mode with random sampling examples."""
        checker, task, profiler, root_id = create_checker_and_task(
            oracle, bias, examples_rs, is_incremental=True
        )

        try:
            # Verify root in set_b (incremental: List[int] of assumption IDs)
            assert root_id in task.set_b, "Root should be in set_b"

            congen = CONGEN(checker, profiler)
            result = congen.acquire(task)

            # Verify result
            assert result is not None
            assert result.n_bias == len(bias.constraints)
            assert result.n_kb >= 0
            assert isinstance(result.kb_constraints, list)

            # Verify bg_clauses contains root clause
            assert [root_id] in result.bg_clauses, "Root clause should be in bg_clauses"

            print(f"\nCONGEN Incremental Result (RS 1n):")
            print(f"  Bias: {result.n_bias}")
            print(f"  MSS: {result.n_mss}")
            print(f"  KB: {result.n_kb}")
            if result.kb_constraints:
                print(f"  Constraints: {result.kb_constraints[:5]}...")

        finally:
            checker.cleanup()

    def test_congen_non_incremental_with_rs_examples(self, oracle, bias, examples_rs):
        """Test CONGEN non-incremental mode with random sampling examples."""
        checker, task, profiler, root_id = create_checker_and_task(
            oracle, bias, examples_rs, is_incremental=False
        )

        try:
            # Verify root in set_b (non-incremental: List[List[List[int]]] clause lists)
            assert [[root_id]] in task.set_b, "Root should be in set_b"

            congen = CONGEN(checker, profiler)
            result = congen.acquire(task)

            # Verify result
            assert result is not None
            assert result.n_bias == len(bias.constraints)
            assert result.n_kb >= 0
            assert isinstance(result.kb_constraints, list)

            # Verify bg_clauses contains root clause
            assert [root_id] in result.bg_clauses, "Root clause should be in bg_clauses"

            print(f"\nCONGEN Non-Incremental Result (RS 1n):")
            print(f"  Bias: {result.n_bias}")
            print(f"  MSS: {result.n_mss}")
            print(f"  KB: {result.n_kb}")

        finally:
            checker.cleanup()

    def test_congen_incremental_with_ff_examples(self, oracle, bias, examples_ff):
        """Test CONGEN incremental mode with feature frequency examples."""
        checker, task, profiler, root_id = create_checker_and_task(
            oracle, bias, examples_ff, is_incremental=True
        )

        try:
            # Verify root in set_b (incremental: List[int] of assumption IDs)
            assert root_id in task.set_b, "Root should be in set_b"

            congen = CONGEN(checker, profiler)
            result = congen.acquire(task)

            # Verify result
            assert result is not None
            assert result.n_bias == len(bias.constraints)

            # Verify bg_clauses contains root clause
            assert [root_id] in result.bg_clauses, "Root clause should be in bg_clauses"

            print(f"\nCONGEN Incremental Result (FF):")
            print(f"  Bias: {result.n_bias}")
            print(f"  MSS: {result.n_mss}")
            print(f"  KB: {result.n_kb}")

        finally:
            checker.cleanup()


class TestACQMSS:
    """Tests for ACQMSS algorithm."""

    def test_acqmss_empty_bias(self):
        """Test ACQMSS with empty bias returns empty."""
        # Create simple checker
        checker = IncrementalPySATChecker([[1]], [1], 'glucose4')

        try:
            acqmss = ACQMSS(checker)
            result = acqmss.find_mss([], [], [], [1], [])

            assert result == []
        finally:
            checker.cleanup()

    def test_acqmss_single_constraint(self):
        """Test ACQMSS with single constraint."""
        # Create checker with simple clauses
        # Clause: (1 ∨ a) where a is assumption
        kb = [[1, 2]]  # 2 is assumption
        checker = IncrementalPySATChecker(kb, [2], 'glucose4')

        try:
            acqmss = ACQMSS(checker, m=1)
            # B = [2], should return [] since |B| <= m
            result = acqmss.find_mss([], [2], [], [1], [])

            assert result == []
        finally:
            checker.cleanup()


class TestReduce:
    """Tests for REDUCE algorithm."""

    def test_reduce_empty(self):
        """Test REDUCE with empty input returns empty."""
        checker = IncrementalPySATChecker([[1]], [1], 'glucose4')

        try:
            reduce = Reduce(checker)
            redundant, kb = reduce.reduce([], [], [], {})

            assert redundant == []
            assert kb == []
        finally:
            checker.cleanup()


class TestGenerateNE:
    """Tests for GenerateNE algorithm."""

    def test_generate_ne_empty(self):
        """Test GenerateNE with empty input returns empty."""
        checker = IncrementalPySATChecker([[1]], [1], 'glucose4')

        try:
            generate_ne = GenerateNE(checker)
            result = generate_ne.generate_from_examples([], [])

            assert result == []
        finally:
            checker.cleanup()


class TestOracleFeatureIds:
    """Regression tests: Oracle feature_ids must match flamapy and bias IDs."""

    MODELS = [
        ("REAL-FM-7", "data/fms/REAL-FM-7.uvl", "data/bias/REAL-FM-7-bias.json"),
        ("arcade-game", "data/fms/arcade-game.uvl", "data/bias/arcade-game-bias.json"),
        ("REAL-FM-4", "data/fms/REAL-FM-4.uvl", "data/bias/REAL-FM-4-bias.json"),
    ]

    @pytest.mark.parametrize("name,fm_path,bias_path", MODELS)
    def test_oracle_ids_match_flamapy(self, name, fm_path, bias_path):
        """Oracle feature_ids must match flamapy's variable assignment."""
        from flamapy.metamodels.fm_metamodel.transformations import UVLReader
        from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat

        if not Path(fm_path).exists():
            pytest.skip(f"FM not found: {fm_path}")

        oracle = FeatureModelOracle(fm_path)
        fm = UVLReader(fm_path).transform()
        sat = FmToPysat(fm).transform()

        assert oracle.feature_ids == dict(sat.variables), \
            f"{name}: Oracle IDs don't match flamapy"
        del oracle

    @pytest.mark.parametrize("name,fm_path,bias_path", MODELS)
    def test_oracle_ids_match_bias(self, name, fm_path, bias_path):
        """Oracle feature_ids must match bias file IDs."""
        if not Path(fm_path).exists() or not Path(bias_path).exists():
            pytest.skip(f"Files not found: {fm_path} or {bias_path}")

        oracle = FeatureModelOracle(fm_path)
        bias = BiasIO.load_from_json(bias_path)
        bias_ids = {f.name: f.id for f in bias.features}

        assert oracle.feature_ids == bias_ids, \
            f"{name}: Oracle IDs don't match bias"
        del oracle


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
