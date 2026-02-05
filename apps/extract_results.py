#!/usr/bin/env python
"""
Extract evaluation results and generate tables for the paper.

Usage:
    PYTHONPATH=. python apps/extract_results.py [--results-dir data/results] [--output-dir paper/tables]

Tables generated:
    - Table: Accuracy by Sampling Strategy (similar to Tables 9-11 in paper)
    - Table: Performance Metrics (similar to Tables 7-8 in paper)
    - Table: KB Size Statistics
    - Table: Incremental vs Non-incremental comparison
"""

import argparse
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import re


# KB name mapping (paper names)
KB_MAPPING = {
    'REAL-FM-7': 'KB1',
    'fqa': 'KB2',
    'arcade': 'KB3',
    'REAL-FM-4': 'KB4',
}

# Reverse mapping
KB_REVERSE = {v: k for k, v in KB_MAPPING.items()}

# Sampling strategies in order
STRATEGIES = ['rs_1n', 'rs_2n', 'rs_3n', 'rs_m', '2cov', 'ff']

# Strategy display names
STRATEGY_NAMES = {
    'rs_1n': 'RS(1n)',
    'rs_2n': 'RS(2n)',
    'rs_3n': 'RS(3n)',
    'rs_m': 'RS(m)',
    '2cov': '2-COV',
    'ff': 'FF',
}


@dataclass
class CVResult:
    """Cross-validation result data."""
    model: str
    strategy: str
    mode: str  # 'incremental' or 'non-incremental'
    n_folds: int
    mean_accuracy: float
    std_accuracy: float
    fold_accuracies: List[float]
    # Performance
    runtime_mean_ms: float
    runtime_std_ms: float
    checks_mean: float
    checks_std: float
    memory_max_mb: float
    # KB size
    n_bias: int
    n_mss_mean: float
    n_kb_mean: float
    n_intersected: int
    total_runtime_ms: float
    # Example counts (from training set)
    n_positive: int = 0  # |E+|
    n_negative: int = 0  # |E-|


def parse_filename(filename: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse CV result filename to extract model, strategy, mode.

    Pattern: {model}_{strategy}_cv_{mode}.json
    Example: REAL-FM-7_rs_1n_cv_incremental.json

    Returns: (model, strategy, mode) or None if not matching
    """
    if not filename.endswith('_cv_incremental.json') and not filename.endswith('_cv_non-incremental.json'):
        return None

    # Determine mode
    if filename.endswith('_cv_incremental.json'):
        mode = 'incremental'
        base = filename[:-len('_cv_incremental.json')]
    else:
        mode = 'non-incremental'
        base = filename[:-len('_cv_non-incremental.json')]

    # Try to match strategy
    for strategy in STRATEGIES:
        if base.endswith(f'_{strategy}'):
            model = base[:-len(f'_{strategy}')]
            return (model, strategy, mode)

    return None


def load_cv_result(filepath: Path) -> Optional[CVResult]:
    """Load CV result from JSON file."""
    parsed = parse_filename(filepath.name)
    if not parsed:
        return None

    model, strategy, mode = parsed

    try:
        with open(filepath) as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None

    # Extract performance data
    perf = data.get('performance', {})
    runtime = perf.get('runtime', {})
    checks = perf.get('consistency_checks', {})
    memory = perf.get('memory', {})
    kb_size = perf.get('kb_size', {})

    # Get n_bias and example counts from first fold
    n_bias = 0
    n_positive = 0
    n_negative = 0
    if data.get('folds'):
        first_fold = data['folds'][0]
        n_bias = first_fold.get('statistics', {}).get('n_bias', 0)
        # Get example counts from train_size
        train_size = first_fold.get('train_size', {})
        n_positive = train_size.get('positive', 0)
        n_negative = train_size.get('negative', 0)

    return CVResult(
        model=model,
        strategy=strategy,
        mode=mode,
        n_folds=data.get('n_folds', 5),
        mean_accuracy=data.get('mean_accuracy', 0),
        std_accuracy=data.get('std_accuracy', 0),
        fold_accuracies=data.get('fold_accuracies', []),
        runtime_mean_ms=runtime.get('mean_ms', 0),
        runtime_std_ms=runtime.get('std_ms', 0),
        checks_mean=checks.get('mean', 0),
        checks_std=checks.get('std', 0),
        memory_max_mb=memory.get('max_mb', 0),
        n_bias=n_bias,
        n_mss_mean=kb_size.get('n_mss_mean', 0),
        n_kb_mean=kb_size.get('n_kb_mean', 0),
        n_intersected=data.get('n_intersected', 0),
        total_runtime_ms=data.get('total_runtime_ms', 0),
        n_positive=n_positive,
        n_negative=n_negative,
    )


def load_all_results(results_dir: Path) -> Dict[str, Dict[str, Dict[str, CVResult]]]:
    """
    Load all CV results from directory.

    Returns: {model: {strategy: {mode: CVResult}}}
    """
    results = {}

    for filepath in results_dir.glob('*_cv_*.json'):
        result = load_cv_result(filepath)
        if result:
            if result.model not in results:
                results[result.model] = {}
            if result.strategy not in results[result.model]:
                results[result.model][result.strategy] = {}
            results[result.model][result.strategy][result.mode] = result

    return results


# =============================================================================
# Table Generators
# =============================================================================

def generate_accuracy_table_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate accuracy table in Markdown format.

    Similar to Tables 9-11 in paper: accuracy by sampling strategy.
    """
    lines = []
    lines.append("## Table: Accuracy by Sampling Strategy ({})".format(mode.capitalize()))
    lines.append("")

    # Header
    header = "| KB |"
    for s in STRATEGIES:
        header += f" {STRATEGY_NAMES[s]} |"
    lines.append(header)

    # Separator
    sep = "|:---|"
    for _ in STRATEGIES:
        sep += ":---:|"
    lines.append(sep)

    # Data rows - ordered by KB1, KB2, KB3, KB4
    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        row = f"| {kb_name} |"
        for strategy in STRATEGIES:
            if strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                row += f" {r.mean_accuracy:.4f} ± {r.std_accuracy:.4f} |"
            else:
                row += " - |"
        lines.append(row)

    return "\n".join(lines)


def generate_accuracy_table_latex(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate accuracy table in LaTeX format.
    """
    lines = []
    lines.append("% Table: Accuracy by Sampling Strategy ({})".format(mode.capitalize()))
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{Accuracy by Sampling Strategy (" + mode.capitalize() + ")}")
    lines.append("\\label{tab:accuracy_" + mode + "}")

    # Column spec
    col_spec = "l" + "c" * len(STRATEGIES)
    lines.append("\\begin{tabular}{" + col_spec + "}")
    lines.append("\\toprule")

    # Header
    header = "KB"
    for s in STRATEGIES:
        header += f" & {STRATEGY_NAMES[s]}"
    header += " \\\\"
    lines.append(header)
    lines.append("\\midrule")

    # Data rows
    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        row = f"{kb_name}"
        for strategy in STRATEGIES:
            if strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                row += f" & {r.mean_accuracy:.4f} $\\pm$ {r.std_accuracy:.4f}"
            else:
                row += " & -"
        row += " \\\\"
        lines.append(row)

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def generate_performance_table_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate performance metrics table in Markdown format.

    Similar to Tables 7-8 in paper.
    """
    lines = []
    lines.append("## Table: Performance Metrics ({})".format(mode.capitalize()))
    lines.append("")
    lines.append("| KB | Strategy | Runtime (ms) | #Checks | Memory (MB) | n_bias | n_mss | n_kb |")
    lines.append("|:---|:---|---:|---:|---:|---:|---:|---:|")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        for strategy in STRATEGIES:
            if strategy not in results[model] or mode not in results[model][strategy]:
                continue

            r = results[model][strategy][mode]
            row = f"| {kb_name} | {STRATEGY_NAMES[strategy]} |"
            row += f" {r.runtime_mean_ms:.2f} ± {r.runtime_std_ms:.2f} |"
            row += f" {r.checks_mean:.0f} ± {r.checks_std:.0f} |"
            row += f" {r.memory_max_mb:.2f} |"
            row += f" {r.n_bias} |"
            row += f" {r.n_mss_mean:.1f} |"
            row += f" {r.n_kb_mean:.1f} |"
            lines.append(row)

    return "\n".join(lines)


def generate_performance_table_latex(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate performance metrics table in LaTeX format.
    """
    lines = []
    lines.append("% Table: Performance Metrics ({})".format(mode.capitalize()))
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{Performance Metrics (" + mode.capitalize() + ")}")
    lines.append("\\label{tab:performance_" + mode + "}")
    lines.append("\\begin{tabular}{llrrrrrr}")
    lines.append("\\toprule")
    lines.append("KB & Strategy & Runtime (ms) & \\#Checks & Memory (MB) & $|B|$ & $|MSS|$ & $|KB|$ \\\\")
    lines.append("\\midrule")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        first_row = True
        for strategy in STRATEGIES:
            if strategy not in results[model] or mode not in results[model][strategy]:
                continue

            r = results[model][strategy][mode]
            kb_col = kb_name if first_row else ""
            row = f"{kb_col} & {STRATEGY_NAMES[strategy]} &"
            row += f" {r.runtime_mean_ms:.2f} $\\pm$ {r.runtime_std_ms:.2f} &"
            row += f" {r.checks_mean:.0f} $\\pm$ {r.checks_std:.0f} &"
            row += f" {r.memory_max_mb:.2f} &"
            row += f" {r.n_bias} &"
            row += f" {r.n_mss_mean:.1f} &"
            row += f" {r.n_kb_mean:.1f} \\\\"
            lines.append(row)
            first_row = False

        if not first_row:
            lines.append("\\midrule")

    # Remove last midrule
    if lines[-1] == "\\midrule":
        lines = lines[:-1]

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def generate_incremental_comparison_md(results: Dict) -> str:
    """
    Generate table comparing incremental vs non-incremental modes.
    """
    lines = []
    lines.append("## Table: Incremental vs Non-Incremental Comparison")
    lines.append("")
    lines.append("| KB | Strategy | Mode | Accuracy | Runtime (ms) | #Checks |")
    lines.append("|:---|:---|:---|---:|---:|---:|")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        for strategy in STRATEGIES:
            if strategy not in results[model]:
                continue

            for mode in ['incremental', 'non-incremental']:
                if mode not in results[model][strategy]:
                    continue

                r = results[model][strategy][mode]
                mode_short = 'Inc' if mode == 'incremental' else 'Non-Inc'
                row = f"| {kb_name} | {STRATEGY_NAMES[strategy]} | {mode_short} |"
                row += f" {r.mean_accuracy:.4f} |"
                row += f" {r.runtime_mean_ms:.2f} |"
                row += f" {r.checks_mean:.0f} |"
                lines.append(row)

    return "\n".join(lines)


def generate_incremental_comparison_latex(results: Dict) -> str:
    """
    Generate table comparing incremental vs non-incremental modes in LaTeX.
    """
    lines = []
    lines.append("% Table: Incremental vs Non-Incremental Comparison")
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{Incremental vs Non-Incremental Comparison}")
    lines.append("\\label{tab:inc_vs_noninc}")
    lines.append("\\begin{tabular}{lllrrr}")
    lines.append("\\toprule")
    lines.append("KB & Strategy & Mode & Accuracy & Runtime (ms) & \\#Checks \\\\")
    lines.append("\\midrule")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        first_kb_row = True
        for strategy in STRATEGIES:
            if strategy not in results[model]:
                continue

            first_strategy_row = True
            for mode in ['incremental', 'non-incremental']:
                if mode not in results[model][strategy]:
                    continue

                r = results[model][strategy][mode]
                kb_col = kb_name if first_kb_row else ""
                strategy_col = STRATEGY_NAMES[strategy] if first_strategy_row else ""
                mode_short = 'Inc' if mode == 'incremental' else 'Non-Inc'

                row = f"{kb_col} & {strategy_col} & {mode_short} &"
                row += f" {r.mean_accuracy:.4f} &"
                row += f" {r.runtime_mean_ms:.2f} &"
                row += f" {r.checks_mean:.0f} \\\\"
                lines.append(row)

                first_kb_row = False
                first_strategy_row = False

        lines.append("\\midrule")

    # Remove last midrule
    if lines[-1] == "\\midrule":
        lines = lines[:-1]

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def generate_kb_summary_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate KB summary table showing intersected KB statistics.
    """
    lines = []
    lines.append("## Table: KB Summary ({})".format(mode.capitalize()))
    lines.append("")
    lines.append("| KB | Strategy | n_bias | n_kb (mean) | n_intersected | Reduction |")
    lines.append("|:---|:---|---:|---:|---:|---:|")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        for strategy in STRATEGIES:
            if strategy not in results[model] or mode not in results[model][strategy]:
                continue

            r = results[model][strategy][mode]
            reduction = (1 - r.n_kb_mean / r.n_bias) * 100 if r.n_bias > 0 else 0

            row = f"| {kb_name} | {STRATEGY_NAMES[strategy]} |"
            row += f" {r.n_bias} |"
            row += f" {r.n_kb_mean:.1f} |"
            row += f" {r.n_intersected} |"
            row += f" {reduction:.1f}% |"
            lines.append(row)

    return "\n".join(lines)


def generate_kb_summary_latex(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate KB summary table in LaTeX.
    """
    lines = []
    lines.append("% Table: KB Summary ({})".format(mode.capitalize()))
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{KB Summary (" + mode.capitalize() + ")}")
    lines.append("\\label{tab:kb_summary_" + mode + "}")
    lines.append("\\begin{tabular}{llrrrr}")
    lines.append("\\toprule")
    lines.append("KB & Strategy & $|B|$ & $|KB|$ (mean) & $|KB_{\\cap}|$ & Reduction \\\\")
    lines.append("\\midrule")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        first_row = True
        for strategy in STRATEGIES:
            if strategy not in results[model] or mode not in results[model][strategy]:
                continue

            r = results[model][strategy][mode]
            reduction = (1 - r.n_kb_mean / r.n_bias) * 100 if r.n_bias > 0 else 0

            kb_col = kb_name if first_row else ""
            row = f"{kb_col} & {STRATEGY_NAMES[strategy]} &"
            row += f" {r.n_bias} &"
            row += f" {r.n_kb_mean:.1f} &"
            row += f" {r.n_intersected} &"
            row += f" {reduction:.1f}\\% \\\\"
            lines.append(row)
            first_row = False

        if not first_row:
            lines.append("\\midrule")

    # Remove last midrule
    if lines[-1] == "\\midrule":
        lines = lines[:-1]

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def generate_accuracy_compact_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate compact accuracy table similar to paper Table 9.
    Shows mean ± std for each KB/strategy combination.
    """
    lines = []
    lines.append("## Table: Accuracy (Compact) - {} Mode".format(mode.capitalize()))
    lines.append("")

    # Header
    header = "| KB |"
    for s in STRATEGIES:
        header += f" {STRATEGY_NAMES[s]} |"
    lines.append(header)

    # Separator
    sep = "|:---|"
    for _ in STRATEGIES:
        sep += ":---:|"
    lines.append(sep)

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        row = f"| {kb_name} |"
        for strategy in STRATEGIES:
            if strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                # Format: mean ± std (without too many decimals)
                row += f" {r.mean_accuracy:.2f}±{r.std_accuracy:.2f} |"
            else:
                row += " - |"
        lines.append(row)

    return "\n".join(lines)


# =============================================================================
# Paper Tables (Tables 7-12 format)
# =============================================================================

def generate_table7_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate Table 7: ACQMSS #consistency checks and runtime (in msec).

    Format from paper:
    | Strategy | |E+| | |E-| | KB1 | KB2 | KB3 | KB4 |

    Values: #checks / runtime(ms)
    """
    lines = []
    lines.append("## Table 7: ACQMSS #consistency checks and runtime (msec) - {} Mode".format(mode.capitalize()))
    lines.append("")
    lines.append("| Strategy | |E+| | |E-| | KB1 | KB2 | KB3 | KB4 |")
    lines.append("|:---|---:|---:|:---:|:---:|:---:|:---:|")

    for strategy in STRATEGIES:
        # Get |E+| and |E-| from first available model for this strategy
        n_pos, n_neg = '-', '-'
        for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
            model = KB_REVERSE.get(kb_name)
            if model and model in results and strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                if r.n_positive > 0 or r.n_negative > 0:
                    n_pos = str(r.n_positive)
                    n_neg = str(r.n_negative)
                    break

        row = f"| {STRATEGY_NAMES[strategy]} | {n_pos} | {n_neg} |"
        for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
            model = KB_REVERSE.get(kb_name)
            if model and model in results and strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                # Format: #checks / runtime
                row += f" {r.checks_mean:.0f} / {r.runtime_mean_ms:.1f} |"
            else:
                row += " - |"
        lines.append(row)

    return "\n".join(lines)


def generate_table7_latex(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate Table 7 in LaTeX format.
    """
    lines = []
    lines.append("% Table 7: ACQMSS #consistency checks and runtime (msec)")
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{ACQMSS \\#consistency checks and runtime (msec) - " + mode.capitalize() + "}")
    lines.append("\\label{tab:table7_" + mode + "}")
    lines.append("\\begin{tabular}{lrrcccc}")
    lines.append("\\toprule")
    lines.append("Strategy & $|E^+|$ & $|E^-|$ & KB1 & KB2 & KB3 & KB4 \\\\")
    lines.append("\\midrule")

    for strategy in STRATEGIES:
        # Get |E+| and |E-| from first available model for this strategy
        n_pos, n_neg = '-', '-'
        for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
            model = KB_REVERSE.get(kb_name)
            if model and model in results and strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                if r.n_positive > 0 or r.n_negative > 0:
                    n_pos = str(r.n_positive)
                    n_neg = str(r.n_negative)
                    break

        row = f"{STRATEGY_NAMES[strategy]} & {n_pos} & {n_neg}"
        for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
            model = KB_REVERSE.get(kb_name)
            if model and model in results and strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                row += f" & {r.checks_mean:.0f} / {r.runtime_mean_ms:.1f}"
            else:
                row += " & -"
        row += " \\\\"
        lines.append(row)

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def generate_table9_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate Table 9: Accuracy with Random Sampling (RS).

    Shows accuracy for RS strategies: rs_1n, rs_2n, rs_3n, rs_m
    """
    rs_strategies = ['rs_1n', 'rs_2n', 'rs_3n', 'rs_m']

    lines = []
    lines.append("## Table 9: Accuracy with Random Sampling (RS) - {} Mode".format(mode.capitalize()))
    lines.append("")
    lines.append("| Strategy | KB1 | KB2 | KB3 | KB4 |")
    lines.append("|:---|:---:|:---:|:---:|:---:|")

    for strategy in rs_strategies:
        row = f"| {STRATEGY_NAMES[strategy]} |"
        for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
            model = KB_REVERSE.get(kb_name)
            if model and model in results and strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                row += f" {r.mean_accuracy:.4f} ± {r.std_accuracy:.4f} |"
            else:
                row += " - |"
        lines.append(row)

    return "\n".join(lines)


def generate_table9_latex(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate Table 9 in LaTeX format.
    """
    rs_strategies = ['rs_1n', 'rs_2n', 'rs_3n', 'rs_m']

    lines = []
    lines.append("% Table 9: Accuracy with Random Sampling (RS)")
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{Accuracy with Random Sampling (RS) - " + mode.capitalize() + "}")
    lines.append("\\label{tab:table9_" + mode + "}")
    lines.append("\\begin{tabular}{lcccc}")
    lines.append("\\toprule")
    lines.append("Strategy & KB1 & KB2 & KB3 & KB4 \\\\")
    lines.append("\\midrule")

    for strategy in rs_strategies:
        row = f"{STRATEGY_NAMES[strategy]}"
        for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
            model = KB_REVERSE.get(kb_name)
            if model and model in results and strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                row += f" & {r.mean_accuracy:.4f} $\\pm$ {r.std_accuracy:.4f}"
            else:
                row += " & -"
        row += " \\\\"
        lines.append(row)

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def generate_table10_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate Table 10: Accuracy with 2-wise coverage (2-COV).
    """
    lines = []
    lines.append("## Table 10: Accuracy with 2-wise coverage (2-COV) - {} Mode".format(mode.capitalize()))
    lines.append("")
    lines.append("| KB | Accuracy |")
    lines.append("|:---|:---:|")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if model and model in results and '2cov' in results[model] and mode in results[model]['2cov']:
            r = results[model]['2cov'][mode]
            lines.append(f"| {kb_name} | {r.mean_accuracy:.4f} ± {r.std_accuracy:.4f} |")
        else:
            lines.append(f"| {kb_name} | - |")

    return "\n".join(lines)


def generate_table10_latex(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate Table 10 in LaTeX format.
    """
    lines = []
    lines.append("% Table 10: Accuracy with 2-wise coverage (2-COV)")
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{Accuracy with 2-wise coverage (2-COV) - " + mode.capitalize() + "}")
    lines.append("\\label{tab:table10_" + mode + "}")
    lines.append("\\begin{tabular}{lc}")
    lines.append("\\toprule")
    lines.append("KB & Accuracy \\\\")
    lines.append("\\midrule")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if model and model in results and '2cov' in results[model] and mode in results[model]['2cov']:
            r = results[model]['2cov'][mode]
            lines.append(f"{kb_name} & {r.mean_accuracy:.4f} $\\pm$ {r.std_accuracy:.4f} \\\\")
        else:
            lines.append(f"{kb_name} & - \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def generate_table11_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate Table 11: Accuracy with Feature Frequency (FF).
    """
    lines = []
    lines.append("## Table 11: Accuracy with Feature Frequency (FF) - {} Mode".format(mode.capitalize()))
    lines.append("")
    lines.append("| KB | Accuracy |")
    lines.append("|:---|:---:|")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if model and model in results and 'ff' in results[model] and mode in results[model]['ff']:
            r = results[model]['ff'][mode]
            lines.append(f"| {kb_name} | {r.mean_accuracy:.4f} ± {r.std_accuracy:.4f} |")
        else:
            lines.append(f"| {kb_name} | - |")

    return "\n".join(lines)


def generate_table11_latex(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate Table 11 in LaTeX format.
    """
    lines = []
    lines.append("% Table 11: Accuracy with Feature Frequency (FF)")
    lines.append("\\begin{table}[htbp]")
    lines.append("\\centering")
    lines.append("\\caption{Accuracy with Feature Frequency (FF) - " + mode.capitalize() + "}")
    lines.append("\\label{tab:table11_" + mode + "}")
    lines.append("\\begin{tabular}{lc}")
    lines.append("\\toprule")
    lines.append("KB & Accuracy \\\\")
    lines.append("\\midrule")

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if model and model in results and 'ff' in results[model] and mode in results[model]['ff']:
            r = results[model]['ff'][mode]
            lines.append(f"{kb_name} & {r.mean_accuracy:.4f} $\\pm$ {r.std_accuracy:.4f} \\\\")
        else:
            lines.append(f"{kb_name} & - \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")

    return "\n".join(lines)


def generate_runtime_compact_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate compact runtime table.
    Shows runtime mean ± std for each KB/strategy combination.
    """
    lines = []
    lines.append("## Table: Runtime (ms) - {} Mode".format(mode.capitalize()))
    lines.append("")

    # Header
    header = "| KB |"
    for s in STRATEGIES:
        header += f" {STRATEGY_NAMES[s]} |"
    lines.append(header)

    # Separator
    sep = "|:---|"
    for _ in STRATEGIES:
        sep += "---:|"
    lines.append(sep)

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        row = f"| {kb_name} |"
        for strategy in STRATEGIES:
            if strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                # Format runtime in seconds if > 1000ms
                if r.runtime_mean_ms > 1000:
                    row += f" {r.runtime_mean_ms/1000:.2f}s |"
                else:
                    row += f" {r.runtime_mean_ms:.0f} |"
            else:
                row += " - |"
        lines.append(row)

    return "\n".join(lines)


def generate_checks_compact_md(results: Dict, mode: str = 'incremental') -> str:
    """
    Generate compact consistency checks table.
    """
    lines = []
    lines.append("## Table: Consistency Checks - {} Mode".format(mode.capitalize()))
    lines.append("")

    # Header
    header = "| KB |"
    for s in STRATEGIES:
        header += f" {STRATEGY_NAMES[s]} |"
    lines.append(header)

    # Separator
    sep = "|:---|"
    for _ in STRATEGIES:
        sep += "---:|"
    lines.append(sep)

    for kb_name in ['KB1', 'KB2', 'KB3', 'KB4']:
        model = KB_REVERSE.get(kb_name)
        if not model or model not in results:
            continue

        row = f"| {kb_name} |"
        for strategy in STRATEGIES:
            if strategy in results[model] and mode in results[model][strategy]:
                r = results[model][strategy][mode]
                row += f" {r.checks_mean:.0f} |"
            else:
                row += " - |"
        lines.append(row)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Extract evaluation results and generate tables')
    parser.add_argument('--results-dir', type=str, default='data/results',
                        help='Directory containing CV result JSON files')
    parser.add_argument('--output-dir', type=str, default='paper/tables',
                        help='Directory to save generated tables')
    parser.add_argument('--mode', type=str, choices=['incremental', 'non-incremental', 'both'],
                        default='both', help='Solver mode to include in tables')
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading results from: {results_dir}")
    results = load_all_results(results_dir)

    # Summary
    print(f"\nLoaded results:")
    for model in sorted(results.keys()):
        strategies = sorted(results[model].keys())
        modes = set()
        for s in strategies:
            modes.update(results[model][s].keys())
        print(f"  {model}: {len(strategies)} strategies, modes: {sorted(modes)}")

    # Generate tables
    print(f"\nGenerating tables to: {output_dir}")

    modes_to_generate = ['incremental', 'non-incremental'] if args.mode == 'both' else [args.mode]

    md_content = []
    latex_content = []

    md_content.append("# Evaluation Results\n")
    md_content.append(f"Generated from: {results_dir}\n")
    md_content.append("KB Mapping: KB1=REAL-FM-7, KB2=fqa, KB3=arcade, KB4=REAL-FM-4\n")

    latex_content.append("% Evaluation Results")
    latex_content.append("% KB Mapping: KB1=REAL-FM-7, KB2=fqa, KB3=arcade, KB4=REAL-FM-4")
    latex_content.append("\\usepackage{booktabs}")
    latex_content.append("")

    for mode in modes_to_generate:
        # =====================================================================
        # Paper Tables (Tables 7, 9, 10, 11)
        # =====================================================================
        md_content.append("\n# Paper Tables ({})".format(mode.capitalize()))

        # Table 7: ACQMSS #consistency checks and runtime
        md_content.append("\n" + generate_table7_md(results, mode))
        latex_content.append("\n" + generate_table7_latex(results, mode))

        # Table 9: Accuracy with Random Sampling (RS)
        md_content.append("\n" + generate_table9_md(results, mode))
        latex_content.append("\n" + generate_table9_latex(results, mode))

        # Table 10: Accuracy with 2-COV
        md_content.append("\n" + generate_table10_md(results, mode))
        latex_content.append("\n" + generate_table10_latex(results, mode))

        # Table 11: Accuracy with FF
        md_content.append("\n" + generate_table11_md(results, mode))
        latex_content.append("\n" + generate_table11_latex(results, mode))

        # =====================================================================
        # Additional Tables
        # =====================================================================
        md_content.append("\n# Additional Tables ({})".format(mode.capitalize()))

        # Accuracy tables (compact)
        md_content.append("\n" + generate_accuracy_compact_md(results, mode))
        md_content.append("\n" + generate_accuracy_table_md(results, mode))
        latex_content.append("\n" + generate_accuracy_table_latex(results, mode))

        # Runtime tables (compact)
        md_content.append("\n" + generate_runtime_compact_md(results, mode))

        # Consistency checks (compact)
        md_content.append("\n" + generate_checks_compact_md(results, mode))

        # Performance tables (detailed)
        md_content.append("\n" + generate_performance_table_md(results, mode))
        latex_content.append("\n" + generate_performance_table_latex(results, mode))

        # KB Summary
        md_content.append("\n" + generate_kb_summary_md(results, mode))
        latex_content.append("\n" + generate_kb_summary_latex(results, mode))

    # Incremental vs Non-incremental comparison
    if args.mode == 'both':
        md_content.append("\n" + generate_incremental_comparison_md(results))
        latex_content.append("\n" + generate_incremental_comparison_latex(results))

    # Write Markdown file
    md_file = output_dir / "results_tables.md"
    with open(md_file, 'w') as f:
        f.write("\n".join(md_content))
    print(f"  Markdown tables: {md_file}")

    # Write LaTeX file
    latex_file = output_dir / "results_tables.tex"
    with open(latex_file, 'w') as f:
        f.write("\n".join(latex_content))
    print(f"  LaTeX tables: {latex_file}")

    print("\nDone!")


if __name__ == '__main__':
    main()
