"""
Report generation for CONGEN evaluation.

Generates formatted reports and saves results to JSON.
"""

from pathlib import Path
from typing import Optional
import json

from .evaluator import EvaluationResult
from .accuracy import AccuracyResult
from .cross_validation import CrossValidationResult


def generate_evaluation_report(
        result: EvaluationResult,
        output_path: Optional[Path] = None
) -> str:
    """
    Generate evaluation report.

    Args:
        result: EvaluationResult from Evaluator
        output_path: Optional path to save JSON report

    Returns:
        Formatted report string
    """
    m = result.metrics
    report = f"""
=== CONGEN Evaluation Report ===
Strategy: {result.strategy}

Metrics:
  Accuracy:    {m.accuracy:.4f}
  Precision:   {m.precision:.4f}
  Recall:      {m.recall:.4f}
  F1 Score:    {m.f1_score:.4f}

Counts:
  True Positives:  {m.true_positives}
  True Negatives:  {m.true_negatives}
  False Positives: {m.false_positives}
  False Negatives: {m.false_negatives}

KB Statistics:
  KB Size:           {len(result.kb_constraints)}
  Matched:           {len(result.matched_constraints)}
  Missed:            {len(result.missed_constraints)}
  Extra:             {len(result.extra_constraints)}
  Reduction Ratio:   {result.kb_reduction_ratio:.4f}

Matched Constraints: {_format_list(result.matched_constraints, 10)}
Missed Constraints:  {_format_list(result.missed_constraints, 10)}
Extra Constraints:   {_format_list(result.extra_constraints, 10)}
"""

    if output_path:
        _save_json(result.to_dict(), output_path)

    return report


def generate_accuracy_report(
        result: AccuracyResult,
        output_path: Optional[Path] = None
) -> str:
    """
    Generate accuracy report.

    Args:
        result: AccuracyResult from AccuracyCalculator
        output_path: Optional path to save JSON report

    Returns:
        Formatted report string
    """
    m = result.metrics
    report = f"""
=== KB Accuracy Report ===

Metrics (Formula 1 from paper):
  Accuracy:    {m.accuracy:.4f}
  Precision:   {m.precision:.4f}
  Recall:      {m.recall:.4f}
  F1 Score:    {m.f1_score:.4f}

Counts:
  TP (E+ accepted):  {m.true_positives}
  TN (E- rejected):  {m.true_negatives}
  FP (E- accepted):  {m.false_positives} (errors)
  FN (E+ rejected):  {m.false_negatives} (errors)

Examples:
  TP Examples: {_format_list(result.tp_examples, 10)}
  TN Examples: {_format_list(result.tn_examples, 10)}
  FP Examples: {_format_list(result.fp_examples, 10)}
  FN Examples: {_format_list(result.fn_examples, 10)}
"""

    if output_path:
        _save_json(result.to_dict(), output_path)

    return report


def generate_cv_report(
        result: CrossValidationResult,
        output_path: Optional[Path] = None
) -> str:
    """
    Generate cross-validation report.

    Args:
        result: CrossValidationResult from n_fold_cross_validation
        output_path: Optional path to save JSON report

    Returns:
        Formatted report string
    """
    p = result.performance
    report = f"""
=== Cross-Validation Report ===

Folds: {result.n_folds}

Accuracy:
  Mean:  {result.mean_accuracy:.4f}
  Std:   {result.std_accuracy:.4f}
  Per Fold: {', '.join(f'{a:.4f}' for a in result.fold_accuracies)}

Performance (aggregated):
  Runtime:
    Mean:  {p.runtime_mean_ms:.2f} ms
    Std:   {p.runtime_std_ms:.2f} ms
    Range: [{p.runtime_min_ms:.2f}, {p.runtime_max_ms:.2f}] ms

  Consistency Checks:
    Mean:  {p.checks_mean:.1f}
    Std:   {p.checks_std:.1f}
    Range: [{p.checks_min}, {p.checks_max}]

  Memory:
    Mean:  {p.memory_mean_mb:.2f} MB
    Max:   {p.memory_max_mb:.2f} MB

  KB Size:
    n_mss Mean: {p.n_mss_mean:.1f}
    n_kb Mean:  {p.n_kb_mean:.1f}
"""

    if output_path:
        _save_json(result.to_dict(), output_path)

    return report


def _format_list(items: list, max_items: int = 10) -> str:
    """Format list for display, truncating if necessary."""
    if not items:
        return "(none)"
    if len(items) <= max_items:
        return ', '.join(str(i) for i in items)
    return ', '.join(str(i) for i in items[:max_items]) + f'... (+{len(items) - max_items} more)'


def _save_json(data: dict, path: Path) -> None:
    """Save data to JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
