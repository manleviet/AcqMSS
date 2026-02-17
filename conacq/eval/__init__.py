"""
Evaluation module for ConGen constraint acquisition.

This module provides tools to evaluate the quality of learned KBs by comparing
with the Oracle (original Feature Model) and calculating accuracy metrics.

Main components:
- Evaluator: Main class for evaluating ConGen results
- AccuracyCalculator: Calculate accuracy of KB against test examples
- n_fold_cross_validation: Cross-validation for generalizability assessment
- ConGenRunner: Run ConGen with performance metrics collection

Evaluation strategies:
1. Description-based (recommended): Compare constraint descriptions
2. Clause-based: Compare CNF clauses (semantic)

Metrics (Formula 1 from paper):
- Accuracy = (TP + TN) / (TP + TN + FP + FN) - PRIMARY METRIC
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2 * P * R / (P + R)

Example usage:
    >>> from acqmss.eval import Evaluator, EvaluationStrategy
    >>> evaluator = Evaluator.from_bias_and_fm_fide('model.uvl', 'bias.json')
    >>> result = evaluator.evaluate(congen_result, EvaluationStrategy.DESCRIPTION)
    >>> print(f"Accuracy: {result.metrics.accuracy:.4f}")
"""

# Metrics
from .metrics import EvaluationMetrics, compute_metrics

# Data loaders
from .bias_loader import BiasData, BiasConstraint
from .result_loader import ConGenResultData
from acqmss.oracle.extractor import GroundTruthData, OracleData

# Accuracy calculation
from .accuracy import AccuracyCalculator, AccuracyResult

# Performance metrics
from .performance_metrics import (
    PerformanceMetrics,
    AggregatedPerformanceMetrics,
    aggregate_metrics
)

# Runners (re-exported from acqmss.runners for backward compat)
from acqmss.runners import ConGenRunner, ConGenRunResult
from acqmss.runners import InteractiveRunner, InteractiveRunResult

# Cross-validation
from .cross_validation import (
    n_fold_cross_validation,
    n_fold_cross_validation_interactive,
    CrossValidationResult,
    CrossValidationFoldResult
)

# Fold I/O
from .fold_io import FoldData, generate_folds, save_folds, load_folds, apply_folds

# Main evaluator
from .evaluator import Evaluator, EvaluationStrategy, EvaluationResult

# Report generation
from .report import (
    generate_evaluation_report,
    generate_accuracy_report,
    generate_cv_report,
    save_kb_result,
    save_cv_kb_files
)

__all__ = [
    # Metrics
    'EvaluationMetrics',
    'compute_metrics',

    # Data loaders
    'BiasData',
    'BiasConstraint',
    'ConGenResultData',
    'GroundTruthData',
    'OracleData',  # backward compat alias

    # Accuracy
    'AccuracyCalculator',
    'AccuracyResult',

    # Performance
    'PerformanceMetrics',
    'AggregatedPerformanceMetrics',
    'aggregate_metrics',

    # ConGen runner
    'ConGenRunner',
    'ConGenRunResult',

    # Interactive runner
    'InteractiveRunner',
    'InteractiveRunResult',

    # Cross-validation
    'n_fold_cross_validation',
    'n_fold_cross_validation_interactive',
    'CrossValidationResult',
    'CrossValidationFoldResult',

    # Evaluator
    'Evaluator',
    'EvaluationStrategy',
    'EvaluationResult',

    # Fold I/O
    'FoldData',
    'generate_folds',
    'save_folds',
    'load_folds',
    'apply_folds',

    # Reports
    'generate_evaluation_report',
    'generate_accuracy_report',
    'generate_cv_report',
    'save_kb_result',
    'save_cv_kb_files',
]
