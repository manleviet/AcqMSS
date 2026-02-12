"""
n-fold cross validation with CONGEN.

Standard cross-validation according to the paper (page 6):
1. Split examples into n folds
2. For each fold i: train KB on (n-1) folds, test accuracy on fold i
3. Report mean accuracy ± std across all folds

Also saves:
- KB for each fold
- Intersected KB (constraints common to all folds)
"""

from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
import random
import logging
import time

from .metrics import EvaluationMetrics
from .accuracy import AccuracyCalculator
from .congen_runner import CONGENRunner
from .fold_io import FoldData, apply_folds
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
    # KB data
    kb_constraints: List[str]
    redundant_constraints: List[str]
    n_bias: int
    n_mss: int
    n_kb: int
    # Train/test sizes
    n_train_pos: int
    n_train_neg: int
    n_test_pos: int
    n_test_neg: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'fold_index': self.fold_index,
            'accuracy': self.accuracy,
            'metrics': self.metrics.to_dict(),
            'performance': {
                'runtime_ms': self.performance.runtime_ms,
                'consistency_checks': self.performance.consistency_checks,
                'memory_peak_mb': self.performance.memory_peak_mb,
                'n_mss': self.performance.n_mss,
                'n_kb': self.performance.n_kb,
            },
            'kb_constraints': self.kb_constraints,
            'redundant_constraints': self.redundant_constraints,
            'statistics': {
                'n_bias': self.n_bias,
                'n_mss': self.n_mss,
                'n_kb': self.n_kb,
            },
            'train_size': {'positive': self.n_train_pos, 'negative': self.n_train_neg},
            'test_size': {'positive': self.n_test_pos, 'negative': self.n_test_neg},
        }

    def to_kb_dict(self) -> dict:
        """Convert to KB file format."""
        return {
            'kb_constraints': self.kb_constraints,
            'redundant_constraints': self.redundant_constraints,
            'statistics': {
                'n_bias': self.n_bias,
                'n_mss': self.n_mss,
                'n_kb': self.n_kb,
            },
            'fold': self.fold_index + 1,
            'accuracy': self.accuracy,
        }


@dataclass
class CrossValidationResult:
    """
    Result of n-fold cross validation.

    Standard CV: each fold trains on (n-1) folds and tests on 1 fold.
    Reports mean accuracy ± std across all folds.

    Also includes:
    - KB for each fold (in fold_results)
    - Intersected KB (constraints common to all folds)
    - Total CV runtime (entire process)
    """
    n_folds: int
    fold_accuracies: List[float]
    mean_accuracy: float
    std_accuracy: float
    fold_results: List[CrossValidationFoldResult]
    performance: AggregatedPerformanceMetrics
    # Intersected KB
    intersected_kb: List[str] = field(default_factory=list)
    # Total CV runtime (ms)
    total_runtime_ms: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'n_folds': self.n_folds,
            'fold_accuracies': self.fold_accuracies,
            'mean_accuracy': self.mean_accuracy,
            'std_accuracy': self.std_accuracy,
            'intersected_kb': self.intersected_kb,
            'n_intersected': len(self.intersected_kb),
            'total_runtime_ms': self.total_runtime_ms,
            'folds': [fr.to_dict() for fr in self.fold_results],
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
        shuffle_each_fold: bool = True,
        fold_data: Optional[FoldData] = None,
        shuffle_bias: bool = False
) -> CrossValidationResult:
    """
    Standard n-fold cross validation according to the paper (page 6).

    Process:
    1. Split examples into n folds
    2. For each fold i:
       - Train: run CONGEN on (n-1) folds to learn KB
       - Test: calculate accuracy on fold i (held-out)
    3. Report mean accuracy ± std
    4. Compute intersected KB (constraints common to all folds)

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
        fold_data: Optional pre-generated fold assignments (for shared folds)
        shuffle_bias: Shuffle bias ordering per fold using fold_data.shuffle_seeds

    Returns:
        CrossValidationResult with mean accuracy ± std and KB data
    """
    if seed is not None:
        random.seed(seed)

    # Use pre-generated folds if provided
    if fold_data is not None:
        n_folds = fold_data.n_folds

    logging.info('>>> n_fold_cross_validation(n=%d, |E+|=%d, |E-|=%d, shared_folds=%s)',
                 n_folds, len(positive_examples), len(negative_examples),
                 fold_data is not None)

    # Start total time measurement
    cv_start_time = time.perf_counter()

    # Create CONGEN runner
    runner = CONGENRunner(
        bias_clauses=bias_clauses,
        feature_ids=feature_ids,
        solver_name=solver_name,
        is_incremental=is_incremental
    )

    # Split into folds: use pre-generated or generate on-the-fly
    if fold_data is None:
        pos_folds = _split_into_folds(positive_examples, n_folds)
        neg_folds = _split_into_folds(negative_examples, n_folds)

    fold_accuracies: List[float] = []
    fold_results: List[CrossValidationFoldResult] = []
    performance_list: List[PerformanceMetrics] = []
    fold_kbs: List[Set[str]] = []  # For intersection

    for fold_idx in range(n_folds):
        logging.info('=== Fold %d/%d ===', fold_idx + 1, n_folds)

        if fold_data is not None:
            # Use pre-generated folds
            train_pos, train_neg, test_pos, test_neg = apply_folds(
                fold_data, positive_examples, negative_examples, fold_idx
            )
        else:
            # On-the-fly folds (backward compat)
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

        # Determine bias shuffle seed for this fold
        fold_shuffle_seed = None
        if shuffle_bias and fold_data is not None:
            fold_shuffle_seed = fold_data.shuffle_seeds[fold_idx]

        # Train: run CONGEN on training set
        congen_result = runner.run(train_pos, train_neg,
                                   shuffle_seed=fold_shuffle_seed)

        # Collect KB for intersection
        fold_kbs.append(set(congen_result.kb_constraints))

        # Collect performance metrics
        perf = congen_result.get_performance_metrics()
        performance_list.append(perf)

        # Test: calculate accuracy on held-out fold
        with AccuracyCalculator(congen_result.kb_clauses, solver_name) as calculator:
            accuracy_result = calculator.calculate(test_pos, test_neg, feature_ids)

        fold_accuracy = accuracy_result.metrics.accuracy
        fold_accuracies.append(fold_accuracy)

        # Store fold result with KB data
        fold_results.append(CrossValidationFoldResult(
            fold_index=fold_idx,
            accuracy=fold_accuracy,
            metrics=accuracy_result.metrics,
            performance=perf,
            kb_constraints=congen_result.kb_constraints,
            redundant_constraints=congen_result.redundant_constraints,
            n_bias=congen_result.n_bias,
            n_mss=congen_result.n_mss,
            n_kb=congen_result.n_kb,
            n_train_pos=len(train_pos),
            n_train_neg=len(train_neg),
            n_test_pos=len(test_pos),
            n_test_neg=len(test_neg)
        ))

        logging.info('Fold %d: accuracy=%.4f (TP=%d, TN=%d, FP=%d, FN=%d), KB=%d',
                     fold_idx + 1, fold_accuracy,
                     accuracy_result.metrics.true_positives,
                     accuracy_result.metrics.true_negatives,
                     accuracy_result.metrics.false_positives,
                     accuracy_result.metrics.false_negatives,
                     congen_result.n_kb)

    # Calculate mean and std of accuracy
    mean_acc = sum(fold_accuracies) / len(fold_accuracies)
    if len(fold_accuracies) > 1:
        variance = sum((x - mean_acc) ** 2 for x in fold_accuracies) / (len(fold_accuracies) - 1)
        std_acc = variance ** 0.5
    else:
        std_acc = 0.0

    # Compute intersected KB
    if fold_kbs:
        intersected = fold_kbs[0]
        for kb in fold_kbs[1:]:
            intersected = intersected & kb
        intersected_kb = sorted(list(intersected))
    else:
        intersected_kb = []

    logging.info('Intersected KB: %d constraints (from fold sizes: %s)',
                 len(intersected_kb), [len(kb) for kb in fold_kbs])

    # Aggregate performance metrics
    agg_performance = aggregate_metrics(performance_list)

    # Calculate total CV time
    cv_end_time = time.perf_counter()
    total_runtime_ms = (cv_end_time - cv_start_time) * 1000

    logging.info('CV result: accuracy = %.4f +/- %.4f, total_time = %.2f ms',
                 mean_acc, std_acc, total_runtime_ms)

    return CrossValidationResult(
        n_folds=n_folds,
        fold_accuracies=fold_accuracies,
        mean_accuracy=mean_acc,
        std_accuracy=std_acc,
        fold_results=fold_results,
        performance=agg_performance,
        intersected_kb=intersected_kb,
        total_runtime_ms=total_runtime_ms
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
