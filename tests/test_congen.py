"""
Tests for ConGen constraint acquisition algorithm.

Uses REAL-FM-7 feature model with generated bias and examples.
Supports both incremental and non-incremental solver modes.
"""

from pathlib import Path

import pytest

from conacq.algorithms import (
    ConGen, AcqMSS, Reduce,
    ConGenModelBuilder, ConGenTaskInput
)
from conacq.bias import BiasIO
from conacq.oracle import FMOracle
from explanation.checker.backend import (
    IncrementalPySATChecker,
    build_checker,
    SolverBackend,
)
from profiling import get_global_profiler

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
        Tuple of (checker, task, profiler, describe)
    """
    from conacq.examples import ExampleIO

    profiler = get_global_profiler()

    # Create oracle
    oracle = FMOracle(fm_path, use_incremental=False)

    # Build the pure-KB model, then prepare this example set's task explicitly.
    model = (ConGenModelBuilder
             .from_bias(bias_path)
             .with_oracle_data(oracle.oracle_data)
             .build())

    examples = ExampleIO.load_json(examples_path)
    pos = [e.assignments for e in examples.positive]
    neg = [e.assignments for e in examples.negative]
    prepared = model.prepare_task(
        ConGenTaskInput.from_examples(oracle.oracle_data, pos, neg))
    task = prepared.task

    checker = build_checker(
        task, SolverBackend.from_flags(use_incremental=is_incremental),
        'glucose4', profiler)

    return checker, task, profiler, prepared.describe


class TestCONGEN:
    """Tests for main ConGen algorithm."""

    def test_congen_incremental_with_rs_examples(self, bias):
        """Test ConGen incremental mode with random sampling examples."""
        if not FM_PATH.exists() or not EXAMPLES_RS_1N_PATH.exists():
            pytest.skip("Test data files not found")
        checker, task, profiler, provider = create_checker_and_task(
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
                negation_map=task.negation_map,
            )

            # Verify result
            assert result is not None
            # n_bias excludes FM constraints (moved to BG in migration)
            assert result.n_bias > 0
            assert result.n_kb >= 0
            assert isinstance(result.kb_assumption_ids, list)

            print(f"\nConGen Incremental Result (RS 1n):")
            print(f"  Bias: {result.n_bias}")
            print(f"  MSS: {result.n_mss}")
            print(f"  KB: {result.n_kb}")
            if result.kb_assumption_ids:
                for c in result.kb_assumption_ids:
                    # Bridge assumption ID (int) → constraint name (str) → Constraint
                    cname = provider.get_description(c)
                    constraint = bias.get_constraint_by_id(cname)
                    print(f"  Constraint: {constraint if constraint else cname} (ID: {c})")

            profiler.print_summary(include_raw_timers=True)

        finally:
            checker.cleanup()

    def test_congen_non_incremental_with_rs_examples(self, bias):
        """Test ConGen non-incremental mode with random sampling examples."""
        if not FM_PATH.exists() or not EXAMPLES_RS_1N_PATH.exists():
            pytest.skip("Test data files not found")
        checker, task, profiler, provider = create_checker_and_task(
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
                negation_map=task.negation_map,
            )

            # Verify result
            assert result is not None
            # n_bias excludes FM constraints (moved to BG in migration)
            assert result.n_bias > 0
            assert result.n_kb >= 0
            assert isinstance(result.kb_assumption_ids, list)

            print(f"\nConGen Non-Incremental Result (RS 1n):")
            print(f"  Bias: {result.n_bias}")
            print(f"  MSS: {result.n_mss}")
            print(f"  KB: {result.n_kb}")

            if result.kb_assumption_ids:
                for c in result.kb_assumption_ids:
                    # Bridge assumption ID (int) → constraint name (str) → Constraint
                    cname = provider.get_description(c)
                    constraint = bias.get_constraint_by_id(cname)
                    print(f"  Constraint: {constraint} (ID: {c})")

            profiler.print_summary(include_raw_timers=True)

        finally:
            checker.cleanup()

    def test_congen_incremental_with_ff_examples(self, bias):
        """Test ConGen incremental mode with feature frequency examples."""
        if not FM_PATH.exists() or not EXAMPLES_FF_PATH.exists():
            pytest.skip("Test data files not found")
        checker, task, profiler, provider = create_checker_and_task(
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
                negation_map=task.negation_map,
            )

            # Verify result
            assert result is not None
            # n_bias excludes FM constraints (moved to BG in migration)
            assert result.n_bias > 0

            print(f"\nConGen Incremental Result (FF):")
            print(f"  Bias: {result.n_bias}")
            print(f"  MSS: {result.n_mss}")
            print(f"  KB: {result.n_kb}")

            if result.kb_assumption_ids:
                for c in result.kb_assumption_ids:
                    # Bridge assumption ID (int) → constraint name (str) → Constraint
                    cname = provider.get_description(c)
                    constraint = bias.get_constraint_by_id(cname)
                    print(f"  Constraint: {constraint} (ID: {c})")

            profiler.print_summary(include_raw_timers=True)

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

    def test_generate_ne_empty_testsuite(self):
        """Test GenerateNE with empty testsuite returns empty."""
        if not FM_PATH.exists():
            pytest.skip("FM file not found")

        from conacq.algorithms.acqmss.generate_ne import GenerateNE
        from explanation.api import AssumptionIdAllocator
        from explanation.models.testsuite import TestSuite

        oracle = FMOracle(str(FM_PATH))
        generate_ne = GenerateNE(oracle.oracle_data)
        empty_ts = TestSuite(testcases=[])
        alloc = AssumptionIdAllocator(1000)
        results = generate_ne.generate(empty_ts, {}, [], [], alloc)

        assert results == []
        assert alloc.next_id == 1000
        del oracle


def _load_ff_examples():
    """Load REAL-FM-7 FF examples as (pos, neg) dict lists."""
    from conacq.examples import ExampleIO
    examples = ExampleIO.load_json(str(EXAMPLES_FF_PATH))
    pos = [e.assignments for e in examples.positive]
    neg = [e.assignments for e in examples.negative]
    return pos, neg


class TestConGenModelBuilder:
    """Tests for ConGenModelBuilder (pure KB) + prepare_task patterns."""

    def test_prepare_task_from_file(self):
        """Build a pure-KB model, then prepare a task from file-loaded examples."""
        if not FM_PATH.exists() or not EXAMPLES_FF_PATH.exists():
            pytest.skip("Test data files not found")

        oracle = FMOracle(str(FM_PATH), use_incremental=False)
        model = (ConGenModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle_data(oracle.oracle_data)
                 .build())
        pos, neg = _load_ff_examples()
        prepared = model.prepare_task(
            ConGenTaskInput.from_examples(oracle.oracle_data, pos, neg))
        assert prepared.task is not None
        assert len(prepared.task.set_kb) > 0

    def test_prepare_task_from_data(self):
        """prepare_task consumes raw example dicts directly (no builder plumbing)."""
        if not FM_PATH.exists() or not EXAMPLES_FF_PATH.exists():
            pytest.skip("Test data files not found")

        pos, neg = _load_ff_examples()
        oracle = FMOracle(str(FM_PATH), use_incremental=False)
        model = (ConGenModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle_data(oracle.oracle_data)
                 .build())
        prepared = model.prepare_task(
            ConGenTaskInput.from_examples(oracle.oracle_data, pos, neg))
        assert prepared.task is not None

    def test_build_without_oracle_raises(self):
        """build() without oracle → ValueError."""
        if not BIAS_PATH.exists():
            pytest.skip("Bias file not found")

        with pytest.raises(ValueError, match="OracleData required"):
            ConGenModelBuilder.from_bias(str(BIAS_PATH)).build()

    def test_prepare_task_is_pure_and_repeatable(self):
        """Build once, prepare_task per fold: same input → same task, fresh object."""
        if not FM_PATH.exists() or not EXAMPLES_FF_PATH.exists():
            pytest.skip("Test data files not found")

        oracle = FMOracle(str(FM_PATH), use_incremental=False)
        model = (ConGenModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle_data(oracle.oracle_data)
                 .build())
        pos, neg = _load_ff_examples()
        task_input = ConGenTaskInput.from_examples(oracle.oracle_data, pos, neg)

        p1 = model.prepare_task(task_input)
        p2 = model.prepare_task(task_input)

        assert p1.task.set_kb == p2.task.set_kb
        assert p1.task is not p2.task


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

        oracle = FMOracle(fm_path)
        fm = UVLReader(fm_path).transform()
        sat = FmToPysat(fm).transform()

        assert oracle.get_variable_ids() == dict(sat.variables), \
            f"{name}: Oracle IDs don't match flamapy"
        del oracle

    @pytest.mark.parametrize("name,fm_path,bias_path", MODELS)
    def test_oracle_ids_match_bias(self, name, fm_path, bias_path):
        """Oracle feature_ids must match bias file IDs."""
        if not Path(fm_path).exists() or not Path(bias_path).exists():
            pytest.skip(f"Files not found: {fm_path} or {bias_path}")

        oracle = FMOracle(fm_path)
        bias = BiasIO.load_from_json(bias_path)
        bias_ids = bias.feature_ids

        assert oracle.get_variable_ids() == bias_ids, \
            f"{name}: Oracle IDs don't match bias"
        del oracle


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
