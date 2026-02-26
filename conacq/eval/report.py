"""
Report generation for ConGen evaluation.

Generates formatted reports and saves results to JSON.
"""

from pathlib import Path
from typing import Optional
import json

from .kb_comparator import ComparationResult
from .accuracy import AccuracyResult
from .cross_validation import CrossValidationResult


def generate_evaluation_report(
        result: ComparationResult,
        output_path: Optional[Path] = None
) -> str:
    """
    Generate evaluation report.

    Args:
        result: EvaluationResult from KBComparator
        output_path: Optional path to save JSON report

    Returns:
        Formatted report string
    """
    m = result.metrics
    report = f"""
=== ConGen Evaluation Report ===
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

    Standard CV report shows mean accuracy ± std across folds.

    Args:
        result: CrossValidationResult from n_fold_cross_validation
        output_path: Optional path to save JSON report

    Returns:
        Formatted report string
    """
    p = result.performance

    # Format per-fold results
    fold_details = []
    for fr in result.fold_results:
        fold_details.append(
            f"  Fold {fr.fold_index + 1}: accuracy={fr.accuracy:.4f}, "
            f"KB={fr.n_kb}, TP={fr.metrics.true_positives}, TN={fr.metrics.true_negatives}, "
            f"FP={fr.metrics.false_positives}, FN={fr.metrics.false_negatives}"
        )

    report = f"""
=== Cross-Validation Report ===

Folds: {result.n_folds}

Accuracy (Formula 1 from paper):
  Mean:  {result.mean_accuracy:.4f}
  Std:   {result.std_accuracy:.4f}
  Per Fold: {', '.join(f'{a:.4f}' for a in result.fold_accuracies)}

Fold Details:
{chr(10).join(fold_details)}

Intersected KB: {len(result.intersected_kb)} constraints

Performance:
  Total CV Runtime: {result.total_runtime_ms:.2f} ms

  ConGen Runtime (per fold):
    Mean:  {p.runtime_mean_ms:.2f} ms
    Std:   {p.runtime_std_ms:.2f} ms
    Range: [{p.runtime_min_ms:.2f}, {p.runtime_max_ms:.2f}] ms

  Consistency Checks:
    Mean:  {p.checks_mean:.1f}
    Range: [{p.checks_min}, {p.checks_max}]

  KB Size:
    Mean:  {p.n_kb_mean:.1f}

  Memory:
    Max:   {p.memory_max_mb:.2f} MB
"""

    if output_path:
        _save_json(result.to_dict(), output_path)

    return report


def save_kb_result(
        kb_constraints: list,
        redundant_constraints: list,
        n_bias: int,
        n_mss: int,
        n_kb: int,
        output_path: Path,
        bg_clauses: Optional[list] = None,
        metadata: Optional[dict] = None
) -> None:
    """
    Save KB result to JSON file.

    This saves the generated knowledge base from ConGen in the same format
    as the original run_congen.py output.

    Args:
        kb_constraints: List of constraint IDs in the learned KB
        redundant_constraints: List of redundant constraint IDs
        n_bias: Original number of bias constraints
        n_mss: Size of MSS before REDUCE
        n_kb: Final KB size
        output_path: Path to save JSON file
        bg_clauses: Background knowledge clauses (e.g., [[1]] for root)
        metadata: Optional metadata dict
    """
    data = {
        'kb_constraints': kb_constraints,
        'redundant_constraints': redundant_constraints,
        'bg_clauses': bg_clauses or [],
        'statistics': {
            'n_bias': n_bias,
            'n_mss': n_mss,
            'n_kb': n_kb
        }
    }
    if metadata:
        data['metadata'] = metadata

    _save_json(data, output_path)


def save_cv_kb_files(
        cv_result: CrossValidationResult,
        output_dir: Path,
        model_name: str,
        mode_name: str
) -> dict:
    """
    Save KB files from cross-validation.

    Saves:
    1. KB for each fold: {model_name}_{mode}_fold{i}_kb.json
    2. Intersected KB: {model_name}_{mode}_intersected_kb.json

    Args:
        cv_result: CrossValidationResult with fold_results and intersected_kb
        output_dir: Output directory
        model_name: Model name for file naming
        mode_name: Mode name (incremental/non-incremental)

    Returns:
        Dict with paths to saved files
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files = {'fold_kbs': [], 'intersected_kb': None}

    # Save KB for each fold
    for fold_result in cv_result.fold_results:
        fold_path = output_dir / f"{model_name}_{mode_name}_fold{fold_result.fold_index + 1}_kb.json"
        _save_json(fold_result.to_kb_dict(), fold_path)
        saved_files['fold_kbs'].append(str(fold_path))

    # Save intersected KB
    intersected_path = output_dir / f"{model_name}_{mode_name}_intersected_kb.json"
    intersected_data = {
        'kb_constraints': cv_result.intersected_kb,
        'bg_clauses': cv_result.bg_clauses,
        'statistics': {
            'n_kb': len(cv_result.intersected_kb),
            'n_folds': cv_result.n_folds,
            'fold_kb_sizes': [fr.n_kb for fr in cv_result.fold_results],
        },
        'cv_accuracy': {
            'mean': cv_result.mean_accuracy,
            'std': cv_result.std_accuracy,
        }
    }
    _save_json(intersected_data, intersected_path)
    saved_files['intersected_kb'] = str(intersected_path)

    return saved_files


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
