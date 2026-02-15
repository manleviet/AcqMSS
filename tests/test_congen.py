"""
Tests for ConGen constraint acquisition algorithm.

Uses REAL-FM-7 feature model with generated bias and examples.
Supports both incremental and non-incremental solver modes.
"""

import pytest
from pathlib import Path
from acqmss.oracle import FeatureModelOracle
from acqmss.bias import BiasIO
from acqmss.algorithms import (
    ConGen, AcqMSS, Reduce, GenerateNE,
    ConGenModelBuilder
)
from explanation.operations.algorithms.checker import (
    IncrementalPySATChecker,
    CheckerFactory
)
from explanation.operations.algorithms.profiler import get_global_profiler


# Test data paths
DATA_DIR = Path(__file__).parent.parent / "data"
FM_PATH = DATA_DIR / "fms" / "REAL-FM-7.uvl"
BIAS_PATH = DATA_DIR / "bias" / "REAL-FM-7-bias.json"
EXAMPLES_RS_1N_PATH = DATA_DIR / "examples" / "REAL-FM-7_rs_1n.json"
EXAMPLES_FF_PATH = DATA_DIR / "examples" / "REAL-FM-7_ff.json"


@pytest.fixture
def bias():
    """Load REAL-FM-7 bias."""
    if not BIAS_PATH.exists():
        pytest.skip(f"Bias file not found: {BIAS_PATH}")
    return BiasIO.load_from_json(str(BIAS_PATH))


def create_checker_and_task(bias_path, fm_path, examples_path, is_incremental=True):
    """Helper to create checker and task for tests.

    Args:
        bias_path: Path to bias JSON file
        fm_path: Path to feature model (.uvl) file
        examples_path: Path to examples JSON file
        is_incremental: Use incremental mode

    Returns:
        Tuple of (checker, task, profiler, root_id)
    """
    profiler = get_global_profiler()
    model = (ConGenModelBuilder
             .from_bias_and_fm_uvl(bias_path, fm_path)
             .with_examples(examples_path)
             .use_incremental(is_incremental)
             .build())

    # Get root_id from model for test assertions
    oracle = FeatureModelOracle(fm_path)
    root_name = oracle.get_root_feature()
    root_id = model.variables[root_name]

    task = model.task
    checker = CheckerFactory.create_from_model(model, 'glucose4', profiler)

    return checker, task, profiler, root_id


class TestCONGEN:
    """Tests for main ConGen algorithm."""

    def test_congen_incremental_with_rs_examples(self, bias):
        """Test ConGen incremental mode with random sampling examples."""
        if not FM_PATH.exists() or not EXAMPLES_RS_1N_PATH.exists():
            pytest.skip("Test data files not found")
        checker, task, profiler, root_id = create_checker_and_task(
            str(BIAS_PATH), str(FM_PATH), str(EXAMPLES_RS_1N_PATH), is_incremental=True
        )

        try:
            # Verify set_b contains background knowledge (root assumption)
            assert len(task.set_b) > 0, "Background knowledge (set_b) should not be empty"

            congen = ConGen(checker, profiler)
            result = congen.acquire(
                set_b=task.set_c,
                set_bg=task.set_b,
                set_tc=task.set_tc,
                set_neg_tv=task.set_neg_tv,
                neg_c_map=task.neg_c_map,
                assumption_to_constraint=task.assumption_to_constraint
            )

            # Verify result
            assert result is not None
            # n_bias excludes FM constraints (moved to BG in migration)
            assert result.n_bias > 0
            assert result.n_kb >= 0
            assert isinstance(result.kb_constraints, list)

            # Verify bg_clauses is not empty (contains background knowledge)
            assert len(result.bg_clauses) > 0, "Background knowledge should not be empty"

            print(f"\nConGen Incremental Result (RS 1n):")
            print(f"  Bias: {result.n_bias}")
            print(f"  MSS: {result.n_mss}")
            print(f"  KB: {result.n_kb}")
            if result.kb_constraints:
                for c in result.kb_constraints:
                    # print constraints by bias.get_constraint_by_id() for readability
                    constraint = bias.get_constraint_by_id(c)
                    print(f"  Constraint: {constraint} (ID: {c})")

        finally:
            checker.cleanup()

    def test_congen_non_incremental_with_rs_examples(self, bias):
        """Test ConGen non-incremental mode with random sampling examples."""
        if not FM_PATH.exists() or not EXAMPLES_RS_1N_PATH.exists():
            pytest.skip("Test data files not found")
        checker, task, profiler, root_id = create_checker_and_task(
            str(BIAS_PATH), str(FM_PATH), str(EXAMPLES_RS_1N_PATH), is_incremental=False
        )

        try:
            # Verify set_b contains background knowledge (root assumption)
            assert len(task.set_b) > 0, "Background knowledge (set_b) should not be empty"

            congen = ConGen(checker, profiler)
            result = congen.acquire(
                set_b=task.set_c,
                set_bg=task.set_b,
                set_tc=task.set_tc,
                set_neg_tv=task.set_neg_tv,
                neg_c_map=task.neg_c_map,
                assumption_to_constraint=task.assumption_to_constraint
            )

            # Verify result
            assert result is not None
            # n_bias excludes FM constraints (moved to BG in migration)
            assert result.n_bias > 0
            assert result.n_kb >= 0
            assert isinstance(result.kb_constraints, list)

            # Verify bg_clauses is not empty (contains background knowledge)
            assert len(result.bg_clauses) > 0, "Background knowledge should not be empty"

            print(f"\nConGen Non-Incremental Result (RS 1n):")
            print(f"  Bias: {result.n_bias}")
            print(f"  MSS: {result.n_mss}")
            print(f"  KB: {result.n_kb}")

            if result.kb_constraints:
                for c in result.kb_constraints:
                    # print constraints by bias.get_constraint_by_id() for readability
                    constraint = bias.get_constraint_by_id(c)
                    print(f"  Constraint: {constraint} (ID: {c})")

        finally:
            checker.cleanup()

    def test_congen_incremental_with_ff_examples(self, bias):
        """Test ConGen incremental mode with feature frequency examples."""
        if not FM_PATH.exists() or not EXAMPLES_FF_PATH.exists():
            pytest.skip("Test data files not found")
        checker, task, profiler, root_id = create_checker_and_task(
            str(BIAS_PATH), str(FM_PATH), str(EXAMPLES_FF_PATH), is_incremental=True
        )

        try:
            # Verify set_b contains background knowledge (root assumption)
            assert len(task.set_b) > 0, "Background knowledge (set_b) should not be empty"

            congen = ConGen(checker, profiler)
            result = congen.acquire(
                set_b=task.set_c,
                set_bg=task.set_b,
                set_tc=task.set_tc,
                set_neg_tv=task.set_neg_tv,
                neg_c_map=task.neg_c_map,
                assumption_to_constraint=task.assumption_to_constraint
            )

            # Verify result
            assert result is not None
            # n_bias excludes FM constraints (moved to BG in migration)
            assert result.n_bias > 0

            # Verify bg_clauses is not empty (contains background knowledge)
            assert len(result.bg_clauses) > 0, "Background knowledge should not be empty"

            print(f"\nConGen Incremental Result (FF):")
            print(f"  Bias: {result.n_bias}")
            print(f"  MSS: {result.n_mss}")
            print(f"  KB: {result.n_kb}")

            if result.kb_constraints:
                for c in result.kb_constraints:
                    # print constraints by bias.get_constraint_by_id() for readability
                    constraint = bias.get_constraint_by_id(c)
                    print(f"  Constraint: {constraint} (ID: {c})")

        finally:
            checker.cleanup()


class TestACQMSS:
    """Tests for AcqMSS algorithm."""

    def test_acqmss_empty_bias(self):
        """Test AcqMSS with empty bias returns empty."""
        # Create simple checker
        checker = IncrementalPySATChecker([[1]], [1], 'glucose4')

        try:
            acqmss = AcqMSS(checker)
            result = acqmss.find_mss([], [], [], [1], [])

            assert result == []
        finally:
            checker.cleanup()

    def test_acqmss_single_constraint(self):
        """Test AcqMSS with single constraint."""
        # Create checker with simple clauses
        # Clause: (1 ∨ a) where a is assumption
        kb = [[1, 2]]  # 2 is assumption
        checker = IncrementalPySATChecker(kb, [2], 'glucose4')

        try:
            acqmss = AcqMSS(checker, m=1)
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
            result = generate_ne.generate([], [])

            assert result.new_clauses == []
            assert result.set_neg_tv == []
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

        assert oracle.get_feature_ids() == dict(sat.variables), \
            f"{name}: Oracle IDs don't match flamapy"
        del oracle

    @pytest.mark.parametrize("name,fm_path,bias_path", MODELS)
    def test_oracle_ids_match_bias(self, name, fm_path, bias_path):
        """Oracle feature_ids must match bias file IDs."""
        if not Path(fm_path).exists() or not Path(bias_path).exists():
            pytest.skip(f"Files not found: {fm_path} or {bias_path}")

        oracle = FeatureModelOracle(fm_path)
        bias = BiasIO.load_from_json(bias_path)
        bias_ids = bias.feature_ids

        assert oracle.get_feature_ids() == bias_ids, \
            f"{name}: Oracle IDs don't match bias"
        del oracle


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
