"""
Unit tests for the evaluation module.

Uses REAL-FM-7 feature model with generated bias and results.
"""

import pytest
from pathlib import Path

from conacq.eval import (
    EvaluationMetrics,
    compute_metrics,
    Bias,
    BiasIO,
    ConGenResultData,
    AccuracyCalculator,
    AccuracyResult,
    PerformanceMetrics,
    aggregate_metrics,
    KBComparator,
    ComparationStrategy,
    generate_evaluation_report,
    generate_accuracy_report,
)


# Test data paths
DATA_DIR = Path(__file__).parent.parent / "data"
FM_PATH = DATA_DIR / "fms" / "REAL-FM-7.uvl"
BIAS_PATH = DATA_DIR / "bias" / "REAL-FM-7-bias.json"
RESULT_PATH = DATA_DIR / "results" / "old_results" / "REAL-FM-7_rs_1n_non-incremental_fold1_kb.json"
EXAMPLES_RS_1N_PATH = DATA_DIR / "examples" / "REAL-FM-7_rs_1n.json"


class TestEvaluationMetrics:
    """Test EvaluationMetrics class."""

    def test_accuracy_calculation(self):
        """Test accuracy formula: (TP + TN) / (TP + TN + FP + FN)"""
        metrics = EvaluationMetrics(
            true_positives=8,
            true_negatives=2,
            false_positives=0,
            false_negatives=0
        )
        assert metrics.accuracy == 1.0

    def test_accuracy_with_errors(self):
        """Test accuracy with some errors."""
        metrics = EvaluationMetrics(
            true_positives=7,
            true_negatives=1,
            false_positives=1,
            false_negatives=1
        )
        # (7 + 1) / (7 + 1 + 1 + 1) = 8/10 = 0.8
        assert metrics.accuracy == 0.8

    def test_precision(self):
        """Test precision = TP / (TP + FP)"""
        metrics = EvaluationMetrics(
            true_positives=8,
            true_negatives=1,
            false_positives=2,
            false_negatives=1
        )
        # 8 / (8 + 2) = 0.8
        assert metrics.precision == 0.8

    def test_recall(self):
        """Test recall = TP / (TP + FN)"""
        metrics = EvaluationMetrics(
            true_positives=8,
            true_negatives=1,
            false_positives=0,
            false_negatives=2
        )
        # 8 / (8 + 2) = 0.8
        assert metrics.recall == 0.8

    def test_f1_score(self):
        """Test F1 = 2 * P * R / (P + R)"""
        metrics = EvaluationMetrics(
            true_positives=8,
            true_negatives=0,
            false_positives=2,
            false_negatives=2
        )
        # P = 8/10 = 0.8, R = 8/10 = 0.8
        # F1 = 2 * 0.8 * 0.8 / (0.8 + 0.8) = 0.8
        assert abs(metrics.f1_score - 0.8) < 1e-10

    def test_zero_division_handling(self):
        """Test handling of zero division cases."""
        metrics = EvaluationMetrics(
            true_positives=0,
            true_negatives=0,
            false_positives=0,
            false_negatives=0
        )
        assert metrics.accuracy == 0.0
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1_score == 0.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        metrics = EvaluationMetrics(
            true_positives=5,
            true_negatives=3,
            false_positives=1,
            false_negatives=1
        )
        d = metrics.to_dict()
        assert 'accuracy' in d
        assert 'precision' in d
        assert 'recall' in d
        assert 'f1_score' in d
        assert d['true_positives'] == 5


class TestComputeMetrics:
    """Test compute_metrics function for clause comparison."""

    def test_perfect_match(self):
        """Test when KB exactly matches Oracle."""
        kb_set = {(1, 2), (3, 4), (5, 6)}
        oracle_set = {(1, 2), (3, 4), (5, 6)}
        bias_set = {(1, 2), (3, 4), (5, 6), (7, 8)}

        metrics = compute_metrics(kb_set, oracle_set, bias_set)
        assert metrics.true_positives == 3
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0

    def test_partial_match(self):
        """Test partial match between KB and Oracle."""
        kb_set = {(1, 2), (3, 4)}
        oracle_set = {(1, 2), (5, 6)}

        metrics = compute_metrics(kb_set, oracle_set)
        assert metrics.true_positives == 1  # (1, 2)
        assert metrics.false_positives == 1  # (3, 4)
        assert metrics.false_negatives == 1  # (5, 6)


class TestBiasLoading:
    """Test Bias loading via BiasIO."""

    def test_load_from_json(self, tmp_path):
        """Test loading bias from JSON file."""
        # Create a test bias file
        bias_json = tmp_path / "test_bias.json"
        bias_json.write_text('''
        {
            "features": [
                {"name": "A", "id": 1},
                {"name": "B", "id": 2}
            ],
            "constraints": [
                {
                    "id": "c1",
                    "operator": "mandatory",
                    "clauses": [[-1, 2], [-2, 1]],
                    "description": "A --mandatory--> B"
                }
            ]
        }
        ''')

        bias = BiasIO.load_from_json(str(bias_json))

        assert len(bias.features) == 2
        assert bias.feature_ids['A'] == 1
        assert len(bias) == 1
        assert bias.get_description('c1') == "A --mandatory--> B"

    def test_get_clauses(self, tmp_path):
        """Test getting clauses for a constraint."""
        bias_json = tmp_path / "test_bias.json"
        bias_json.write_text('''
        {
            "features": [],
            "constraints": [
                {"id": "c1", "operator": "mandatory", "clauses": [[1, 2], [3]], "description": "test"}
            ]
        }
        ''')

        bias = BiasIO.load_from_json(str(bias_json))
        clauses = bias.get_clauses('c1')

        assert len(clauses) == 2
        assert clauses[0] == [1, 2]


class TestCONGENResultData:
    """Test ConGenResultData loading."""

    def test_load_from_json(self, tmp_path):
        """Test loading result from JSON file."""
        result_json = tmp_path / "test_result.json"
        result_json.write_text('''
        {
            "kb_constraints": ["c1", "c2", "c3"],
            "redundant_constraints": ["c4"],
            "statistics": {
                "n_bias": 100,
                "n_mss": 50,
                "n_kb": 3
            },
            "metadata": {}
        }
        ''')

        result = ConGenResultData.from_json(result_json)

        assert len(result.kb_constraints) == 3
        assert result.n_bias == 100
        assert result.n_kb == 3

    def test_bg_clauses_default_empty(self):
        """Verify bg_clauses defaults to empty, no impact on eval."""
        result = ConGenResultData(kb_constraints=[], n_bias=10, n_kb=0)
        assert result.bg_clauses == []

    def test_kb_reduction_ratio(self, tmp_path):
        """Test KB reduction ratio calculation."""
        result_json = tmp_path / "test_result.json"
        result_json.write_text('''
        {
            "kb_constraints": ["c1", "c2"],
            "redundant_constraints": [],
            "statistics": {"n_bias": 100, "n_mss": 50, "n_kb": 20}
        }
        ''')

        result = ConGenResultData.from_json(result_json)

        # reduction = 1 - (20/100) = 0.8
        assert result.kb_reduction_ratio == 0.8


class TestAccuracyCalculator:
    """Test AccuracyCalculator class."""

    def test_perfect_accuracy(self):
        """Test when KB accepts all E+ and rejects all E-."""
        # KB: A must be true
        kb_clauses = [[1]]

        with AccuracyCalculator(kb_clauses, {'A': 1}) as calc:
            positive = [{'A': True}]
            negative = [{'A': False}]

            result = calc.calculate(positive, negative)

            assert result.metrics.accuracy == 1.0
            assert result.metrics.true_positives == 1
            assert result.metrics.true_negatives == 1
            assert result.metrics.false_positives == 0
            assert result.metrics.false_negatives == 0

    def test_false_negative(self):
        """Test when KB incorrectly rejects a positive example."""
        # KB: A and B must be true
        kb_clauses = [[1], [2]]

        with AccuracyCalculator(kb_clauses, {'A': 1, 'B': 2}) as calc:
            # E+ has A=True, B=False (should be rejected by this KB)
            positive = [{'A': True, 'B': False}]
            negative = []

            result = calc.calculate(positive, negative)

            assert result.metrics.false_negatives == 1

    def test_false_positive(self):
        """Test when KB incorrectly accepts a negative example."""
        # KB: A or B (always satisfiable if A=True)
        kb_clauses = [[1, 2]]

        with AccuracyCalculator(kb_clauses, {'A': 1, 'B': 2}) as calc:
            positive = []
            # E- has A=True (should be accepted by this KB)
            negative = [{'A': True, 'B': False}]

            result = calc.calculate(positive, negative)

            assert result.metrics.false_positives == 1


class TestPerformanceMetrics:
    """Test performance metrics aggregation."""

    def test_aggregate_metrics(self):
        """Test aggregating metrics from multiple runs."""
        metrics_list = [
            PerformanceMetrics(
                runtime_ms=100,
                consistency_checks=50,
                memory_peak_mb=10,
                n_mss=20,
                n_kb=5
            ),
            PerformanceMetrics(
                runtime_ms=200,
                consistency_checks=70,
                memory_peak_mb=15,
                n_mss=25,
                n_kb=7
            ),
        ]

        agg = aggregate_metrics(metrics_list)

        assert agg.n_runs == 2
        assert agg.runtime_mean_ms == 150  # (100 + 200) / 2
        assert agg.runtime_min_ms == 100
        assert agg.runtime_max_ms == 200
        assert agg.checks_mean == 60  # (50 + 70) / 2
        assert agg.memory_max_mb == 15

    def test_aggregate_single_run(self):
        """Test aggregating a single run (std should be 0)."""
        metrics_list = [
            PerformanceMetrics(
                runtime_ms=100,
                consistency_checks=50,
                memory_peak_mb=10,
                n_mss=20,
                n_kb=5
            ),
        ]

        agg = aggregate_metrics(metrics_list)

        assert agg.n_runs == 1
        assert agg.runtime_std_ms == 0.0

    def test_aggregate_extended_metrics(self):
        """Test aggregating extended profiler metrics."""
        metrics_list = [
            PerformanceMetrics(
                runtime_ms=100, consistency_checks=50,
                memory_peak_mb=10, n_mss=20, n_kb=5,
                congen_runtime_ms=90, acqmss_runtime_ms=60,
                acqmss_calls=10, reduce_runtime_ms=20,
                solver_time_ms=50, is_consistent_calls=30,
                is_consistent_test_cases_calls=5,
                redundancy_consistency_checks=15,
            ),
            PerformanceMetrics(
                runtime_ms=200, consistency_checks=70,
                memory_peak_mb=15, n_mss=25, n_kb=7,
                congen_runtime_ms=180, acqmss_runtime_ms=120,
                acqmss_calls=20, reduce_runtime_ms=40,
                solver_time_ms=100, is_consistent_calls=50,
                is_consistent_test_cases_calls=7,
                redundancy_consistency_checks=25,
            ),
        ]

        agg = aggregate_metrics(metrics_list)

        # Verify extended runtime metrics
        assert agg.congen_runtime_mean_ms == 135  # (90 + 180) / 2
        assert agg.congen_runtime_min_ms == 90
        assert agg.congen_runtime_max_ms == 180
        assert agg.acqmss_runtime_mean_ms == 90  # (60 + 120) / 2
        assert agg.reduce_runtime_mean_ms == 30  # (20 + 40) / 2
        assert agg.solver_time_mean_ms == 75  # (50 + 100) / 2

        # Verify extended counter metrics
        assert agg.acqmss_calls_mean == 15  # (10 + 20) / 2
        assert agg.acqmss_calls_min == 10
        assert agg.acqmss_calls_max == 20
        assert agg.is_consistent_calls_mean == 40  # (30 + 50) / 2
        assert agg.is_consistent_tc_calls_mean == 6  # (5 + 7) / 2
        assert agg.redundancy_checks_mean == 20  # (15 + 25) / 2

    def test_aggregate_empty_list(self):
        """Test that empty list raises error."""
        with pytest.raises(ValueError):
            aggregate_metrics([])


class TestReportGeneration:
    """Test report generation functions."""

    def test_generate_evaluation_report(self):
        """Test evaluation report generation."""
        from conacq.eval import ComparationResult

        result = ComparationResult(
            strategy='description',
            metrics=EvaluationMetrics(
                true_positives=5,
                true_negatives=3,
                false_positives=1,
                false_negatives=1
            ),
            kb_constraints=['c1', 'c2', 'c3'],
            matched_constraints=['c1', 'c2'],
            missed_constraints=['m1'],
            extra_constraints=['e1'],
            kb_reduction_ratio=0.9
        )

        report = generate_evaluation_report(result)

        assert 'ConGen Evaluation Report' in report
        assert 'Accuracy' in report
        assert 'Precision' in report
        assert 'description' in report

    def test_generate_accuracy_report(self):
        """Test accuracy report generation."""
        result = AccuracyResult(
            metrics=EvaluationMetrics(
                true_positives=8,
                true_negatives=2,
                false_positives=0,
                false_negatives=0
            ),
            tp_examples=['e1+', 'e2+'],
            tn_examples=['e1-'],
            fp_examples=[],
            fn_examples=[]
        )

        report = generate_accuracy_report(result)

        assert 'KB Accuracy Report' in report
        assert 'Formula 1' in report


class TestIntegration:
    """Integration tests with actual data files."""

    def test_evaluate_real_fm_7(self):
        """Test evaluation with REAL-FM-7 data."""
        comparator = KBComparator.from_files(FM_PATH, BIAS_PATH)
        result = ConGenResultData.from_json(RESULT_PATH)

        eval_result = comparator.compare(result, ComparationStrategy.DESCRIPTION)

        # Basic sanity checks
        assert eval_result.metrics.accuracy >= 0
        assert eval_result.metrics.accuracy <= 1
        assert len(eval_result.kb_constraints) > 0

    def test_accuracy_with_real_examples(self):
        """Test accuracy calculation with real examples."""
        from conacq.examples import ExampleIO

        bias = BiasIO.load_from_json(str(BIAS_PATH))
        examples = ExampleIO.load_json(EXAMPLES_RS_1N_PATH)
        result = ConGenResultData.from_json(RESULT_PATH)

        # Build KB clauses
        kb_clauses = []
        for cid in result.kb_constraints:
            if bias.has_constraint(cid):
                kb_clauses.extend(bias.get_clauses(cid))

        with AccuracyCalculator(kb_clauses, bias.feature_ids) as calc:
            pos_assignments = [e.assignments for e in examples.positive]
            neg_assignments = [e.assignments for e in examples.negative]
            accuracy_result = calc.calculate(
                pos_assignments,
                neg_assignments
            )

        # Sanity checks - accuracy should be valid
        assert 0 <= accuracy_result.metrics.accuracy <= 1
        # Should have processed all examples
        total = (accuracy_result.metrics.true_positives +
                 accuracy_result.metrics.true_negatives +
                 accuracy_result.metrics.false_positives +
                 accuracy_result.metrics.false_negatives)
        assert total == len(examples.positive) + len(examples.negative)

    def test_clause_eval_includes_bg_clauses(self):
        """Verify bg_clauses are unioned with kb_clauses in clause eval."""
        comparator = KBComparator.from_files(FM_PATH, BIAS_PATH)

        # Get root feature ID from oracle
        root_id = comparator.oracle.feature_map[comparator.oracle.root_feature]

        # Result with NO KB but WITH bg_clauses containing root
        result_with_bg = ConGenResultData(
            kb_constraints=[],
            n_bias=len(comparator.bias.constraints),
            n_kb=0,
            bg_clauses=[[root_id]]
        )

        # Result with NO KB and NO bg_clauses
        result_without_bg = ConGenResultData(
            kb_constraints=[],
            n_bias=len(comparator.bias.constraints),
            n_kb=0,
            bg_clauses=[]
        )

        eval_with = comparator.compare(result_with_bg, ComparationStrategy.CLAUSE)
        eval_without = comparator.compare(result_without_bg, ComparationStrategy.CLAUSE)

        # With bg_clauses: root clause should be TP → more TP, fewer FN
        assert eval_with.metrics.true_positives >= eval_without.metrics.true_positives
        assert eval_with.metrics.false_negatives <= eval_without.metrics.false_negatives
