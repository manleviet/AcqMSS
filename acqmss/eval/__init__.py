"""
Evaluation module for CONGEN constraint acquisition.

This module provides tools to evaluate the quality of learned KBs by comparing
with the Oracle (original Feature Model) and calculating accuracy metrics.

Main components:
- Evaluator: Main class for evaluating CONGEN results
- AccuracyCalculator: Calculate accuracy of KB against test examples
- n_fold_cross_validation: Cross-validation for generalizability assessment
- CONGENRunner: Run CONGEN with performance metrics collection

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
    >>> evaluator = Evaluator.from_files('model.uvl', 'bias.json')
    >>> result = evaluator.evaluate(congen_result, EvaluationStrategy.DESCRIPTION)
    >>> print(f"Accuracy: {result.metrics.accuracy:.4f}")
"""

# Metrics
from .metrics import EvaluationMetrics, compute_metrics

# Data loaders
from .bias_loader import BiasData, BiasConstraint
from .result_loader import CONGENResultData
from .oracle_extractor import OracleData

# Accuracy calculation
from .accuracy import AccuracyCalculator, AccuracyResult

# Performance metrics
from .performance_metrics import (
    PerformanceMetrics,
    AggregatedPerformanceMetrics,
    aggregate_metrics
)

# CONGEN runner
from .congen_runner import CONGENRunner, CONGENRunResult

# Cross-validation
from .cross_validation import (
    n_fold_cross_validation,
    CrossValidationResult,
    CrossValidationFoldResult
)

# Main evaluator
from .evaluator import Evaluator, EvaluationStrategy, EvaluationResult

# Report generation
from .report import (
    generate_evaluation_report,
    generate_accuracy_report,
    generate_cv_report
)

__all__ = [
    # Metrics
    'EvaluationMetrics',
    'compute_metrics',

    # Data loaders
    'BiasData',
    'BiasConstraint',
    'CONGENResultData',
    'OracleData',

    # Accuracy
    'AccuracyCalculator',
    'AccuracyResult',

    # Performance
    'PerformanceMetrics',
    'AggregatedPerformanceMetrics',
    'aggregate_metrics',

    # CONGEN runner
    'CONGENRunner',
    'CONGENRunResult',

    # Cross-validation
    'n_fold_cross_validation',
    'CrossValidationResult',
    'CrossValidationFoldResult',

    # Evaluator
    'Evaluator',
    'EvaluationStrategy',
    'EvaluationResult',

    # Reports
    'generate_evaluation_report',
    'generate_accuracy_report',
    'generate_cv_report',
]
