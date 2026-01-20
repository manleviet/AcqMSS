"""
n-fold cross validation with CONGEN.

Runs CONGEN directly for each fold and collects:
- Accuracy metrics (TP, TN, FP, FN)
- Performance metrics (runtime, #checks, memory, n_mss, n_kb)

According to the paper (page 6), n-fold cross validation evaluates
the generalizability of the learned KB.
"""

from typing import List, Dict
from dataclasses import dataclass
import random
import logging

from .metrics import EvaluationMetrics
from .accuracy import AccuracyCalculator
from .congen_runner import CONGENRunner, CONGENRunResult
from .performance_metrics import (
    PerformanceMetrics,
    AggregatedPerformanceMetrics,
    aggregate_metrics
)


@dataclass
class CrossValidationFoldResult:
    """Result of a single fold."""
    fold_index: int
    accuracy: float
    metrics: EvaluationMetrics
    performance: PerformanceMetrics
    kb_constraints: List[str]


@dataclass
class CrossValidationResult:
    """
    Result of n-fold cross validation.

    Attributes:
        n_folds: Number of folds
        fold_accuracies: Accuracy of each fold
        mean_accuracy: Mean accuracy across folds
        std_accuracy: Standard deviation of accuracies
        fold_metrics: EvaluationMetrics for each fold
        performance: Aggregated performance metrics
        fold_results: Detailed results for each fold
    """
    n_folds: int
    fold_accuracies: List[float]
    mean_accuracy: float
    std_accuracy: float
    fold_metrics: List[EvaluationMetrics]
    performance: AggregatedPerformanceMetrics
    fold_results: List[CrossValidationFoldResult] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'n_folds': self.n_folds,
            'fold_accuracies': self.fold_accuracies,
            'mean_accuracy': self.mean_accuracy,
            'std_accuracy': self.std_accuracy,
            'performance': self.performance.to_dict(),
        }


def n_fold_cross_validation(
        positive_examples: List[Dict[str, bool]],
        negative_examples: List[Dict[str, bool]],
        n_folds: int,
        bias_clauses: Dict[str, List[List[int]]],
        feature_ids: Dict[str, int],
        seed: int = None,
        solver_name: str = 'glucose4',
        is_incremental: bool = True,
        shuffle_each_fold: bool = True
) -> CrossValidationResult:
    """
    n-fold cross validation according to the paper (page 6).

    Runs CONGEN directly for each fold and collects:
    - Accuracy: (TP + TN) / (TP + TN + FP + FN)
    - Performance: runtime, #checks, memory, n_mss, n_kb

    IMPORTANT: When shuffle_each_fold is True, randomly shuffles examples
    before each CONGEN call since order may affect learned KB.

    Args:
        positive_examples: List of E+ ({feature: True/False})
        negative_examples: List of E- ({feature: True/False})
        n_folds: Number of folds (e.g., 5 or 10)
        bias_clauses: {constraint_id: clauses} from bias file
        feature_ids: {feature_name: SAT_variable_id}
        seed: Random seed for reproducibility
        solver_name: SAT solver name
        is_incremental: Use incremental solver mode
        shuffle_each_fold: Shuffle training examples before each fold

    Returns:
        CrossValidationResult with accuracy and performance metrics
    """
    if seed is not None:
        random.seed(seed)

    logging.debug('>>> n_fold_cross_validation(n=%d, |E+|=%d, |E-|=%d)',
                  n_folds, len(positive_examples), len(negative_examples))

    # Create CONGEN runner
    runner = CONGENRunner(
        bias_clauses=bias_clauses,
        feature_ids=feature_ids,
        solver_name=solver_name,
        is_incremental=is_incremental
    )

    # Shuffle and split into folds
    pos_folds = _split_into_folds(positive_examples, n_folds)
    neg_folds = _split_into_folds(negative_examples, n_folds)

    fold_accuracies = []
    fold_metrics = []
    performance_list = []
    fold_results = []

    for fold_idx in range(n_folds):
        logging.info('=== Fold %d/%d ===', fold_idx + 1, n_folds)

        # Prepare train and test sets
        train_pos = [ex for i, fold in enumerate(pos_folds) for ex in fold if i != fold_idx]
        train_neg = [ex for i, fold in enumerate(neg_folds) for ex in fold if i != fold_idx]
        test_pos = pos_folds[fold_idx]
        test_neg = neg_folds[fold_idx]

        # Shuffle training examples if requested
        if shuffle_each_fold:
            random.shuffle(train_pos)
            random.shuffle(train_neg)

        logging.debug('Fold %d: train=(%d+, %d-), test=(%d+, %d-)',
                      fold_idx + 1, len(train_pos), len(train_neg),
                      len(test_pos), len(test_neg))

        # Run CONGEN on training set
        congen_result = runner.run(train_pos, train_neg)

        # Collect performance metrics
        perf = congen_result.get_performance_metrics()
        performance_list.append(perf)

        # Test accuracy on test set
        with AccuracyCalculator(congen_result.kb_clauses, solver_name) as calculator:
            accuracy_result = calculator.calculate(test_pos, test_neg, feature_ids)

        fold_accuracies.append(accuracy_result.metrics.accuracy)
        fold_metrics.append(accuracy_result.metrics)

        # Store fold result
        fold_results.append(CrossValidationFoldResult(
            fold_index=fold_idx,
            accuracy=accuracy_result.metrics.accuracy,
            metrics=accuracy_result.metrics,
            performance=perf,
            kb_constraints=congen_result.kb_constraints
        ))

        logging.info('Fold %d: accuracy=%.4f, KB=%d, runtime=%.2fms',
                     fold_idx + 1, accuracy_result.metrics.accuracy,
                     congen_result.n_kb, congen_result.runtime_ms)

    # Calculate mean and std of accuracy
    mean_acc = sum(fold_accuracies) / len(fold_accuracies)
    if len(fold_accuracies) > 1:
        variance = sum((x - mean_acc) ** 2 for x in fold_accuracies) / len(fold_accuracies)
        std_acc = variance ** 0.5
    else:
        std_acc = 0.0

    # Aggregate performance metrics
    agg_performance = aggregate_metrics(performance_list)

    logging.info('CV result: accuracy=%.4f +/- %.4f, avg_runtime=%.2fms',
                 mean_acc, std_acc, agg_performance.runtime_mean_ms)

    return CrossValidationResult(
        n_folds=n_folds,
        fold_accuracies=fold_accuracies,
        mean_accuracy=mean_acc,
        std_accuracy=std_acc,
        fold_metrics=fold_metrics,
        performance=agg_performance,
        fold_results=fold_results
    )


def _split_into_folds(items: List, n_folds: int) -> List[List]:
    """
    Split items into n approximately equal folds.

    Args:
        items: List of items to split
        n_folds: Number of folds

    Returns:
        List of fold lists
    """
    shuffled = items.copy()
    random.shuffle(shuffled)
    folds = [[] for _ in range(n_folds)]
    for i, item in enumerate(shuffled):
        folds[i % n_folds].append(item)
    return folds
