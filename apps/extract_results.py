#!/usr/bin/env python
"""
Extract evaluation results and generate tables for the paper.

Usage:
    python -m apps.extract_results [--results-dir data/results] [--output-dir paper/tables]

Tables generated:
    - Paper Tables 7, 9, 10, 11 (consistency checks, accuracy by strategy)
    - Fold metrics (Precision/Recall/F1)
    - Performance, KB summary, incremental comparison
"""

import argparse
import json
import re
import statistics
import tomllib
from pathlib import Path

from conacq.atomic_io import write_text_atomic
from apps._harness import build_parser, load_config
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple


# KB name mapping (paper names)
KB_MAPPING = {
    'REAL-FM-7': 'KB1',
    'fqa': 'KB2',
    'arcade': 'KB3',
    'REAL-FM-4': 'KB4',
}
KB_REVERSE = {v: k for k, v in KB_MAPPING.items()}
KB_NAMES = ['KB1', 'KB2', 'KB3', 'KB4']

# Sampling strategies in order
STRATEGIES = ['rs_1n', 'rs_2n', 'rs_3n', 'rs_m', '2cov', 'ff']
STRATEGY_NAMES = {
    'rs_1n': 'RS(1n)', 'rs_2n': 'RS(2n)', 'rs_3n': 'RS(3n)',
    'rs_m': 'RS(m)', '2cov': '2-COV', 'ff': 'FF',
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
    n_positive: int = 0
    n_negative: int = 0
    # Fold-level metrics (precision, recall, F1, specificity)
    precision_mean: float = 0.0
    precision_std: float = 0.0
    recall_mean: float = 0.0
    recall_std: float = 0.0
    f1_mean: float = 0.0
    f1_std: float = 0.0
    specificity_mean: float = 0.0
    specificity_std: float = 0.0
    # Strategy evaluation on intersected KB (description strategy)
    desc_accuracy: float = 0.0
    desc_precision: float = 0.0
    desc_recall: float = 0.0
    desc_f1: float = 0.0
    # Strategy evaluation on intersected KB (clause strategy)
    clause_accuracy: float = 0.0
    clause_precision: float = 0.0
    clause_recall: float = 0.0
    clause_f1: float = 0.0
    has_strategy_eval: bool = False


# =============================================================================
# Data Loading
# =============================================================================

_CV_PATTERN = re.compile(r'^(.+)_cv_(incremental|non-incremental)(?:_.+)?\.json$')


def parse_filename(filename: str) -> Optional[Tuple[str, str, str]]:
    """Parse CV result filename → (model, strategy, mode) or None.

    Handles both standard and interactive filenames:
      model_cv_incremental.json
      model_cv_incremental_example_only.json
    """
    m = _CV_PATTERN.match(filename)
    if not m:
        return None

    base, mode = m.group(1), m.group(2)

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

    perf = data.get('performance', {})
    runtime = perf.get('runtime', {})
    checks = perf.get('consistency_checks', {})
    memory = perf.get('memory', {})
    kb_size = perf.get('kb_size', {})

    # Extract per-fold data
    n_bias, n_positive, n_negative = 0, 0, 0
    fold_precisions, fold_recalls, fold_f1s, fold_specificities = [], [], [], []
    if data.get('folds'):
        first_fold = data['folds'][0]
        n_bias = first_fold.get('statistics', {}).get('n_bias', 0)
        train_size = first_fold.get('train_size', {})
        n_positive = train_size.get('positive', 0)
        n_negative = train_size.get('negative', 0)
        for fold in data['folds']:
            metrics = fold.get('metrics', {})
            if metrics:
                fold_precisions.append(metrics.get('precision', 0.0))
                fold_recalls.append(metrics.get('recall', 0.0))
                fold_f1s.append(metrics.get('f1_score', 0.0))
                fold_specificities.append(metrics.get('specificity', 0.0))

    def _mean_std(values):
        if not values:
            return 0.0, 0.0
        m = statistics.mean(values)
        s = statistics.pstdev(values) if len(values) > 1 else 0.0
        return m, s

    prec_m, prec_s = _mean_std(fold_precisions)
    rec_m, rec_s = _mean_std(fold_recalls)
    f1_m, f1_s = _mean_std(fold_f1s)
    spec_m, spec_s = _mean_std(fold_specificities)

    # Extract strategy evaluation on intersected KB
    # Priority: unified format (intersected_kb.evaluation) > old embedded format
    intersected_data = data.get('intersected_kb', {})
    if isinstance(intersected_data, dict):
        intersected_eval = intersected_data.get('evaluation') or {}
    else:
        intersected_eval = {}
    if not intersected_eval:
        intersected_eval = data.get('intersected_evaluation', {})
    has_strategy_eval = bool(intersected_eval)
    desc_eval = intersected_eval.get('description', {}).get('metrics', {})
    clause_eval = intersected_eval.get('clause', {}).get('metrics', {})

    return CVResult(
        model=model, strategy=strategy, mode=mode,
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
        n_mss_mean=kb_size.get('n_mss_mean') or 0,
        n_kb_mean=kb_size.get('n_kb_mean', 0),
        n_intersected=(intersected_data.get('n_kb', 0)
                       if isinstance(intersected_data, dict)
                       else data.get('n_intersected', 0)),
        total_runtime_ms=data.get('total_runtime_ms', 0),
        n_positive=n_positive, n_negative=n_negative,
        precision_mean=prec_m, precision_std=prec_s,
        recall_mean=rec_m, recall_std=rec_s,
        f1_mean=f1_m, f1_std=f1_s,
        specificity_mean=spec_m, specificity_std=spec_s,
        desc_accuracy=desc_eval.get('accuracy', 0.0),
        desc_precision=desc_eval.get('precision', 0.0),
        desc_recall=desc_eval.get('recall', 0.0),
        desc_f1=desc_eval.get('f1_score', 0.0),
        clause_accuracy=clause_eval.get('accuracy', 0.0),
        clause_precision=clause_eval.get('precision', 0.0),
        clause_recall=clause_eval.get('recall', 0.0),
        clause_f1=clause_eval.get('f1_score', 0.0),
        has_strategy_eval=has_strategy_eval,
    )


def load_eval_result(eval_path: Path) -> Optional[Dict]:
    """Load evaluation metrics from a *_eval.json file (from run_compare.py).

    Returns:
        Dict with 'description' and/or 'clause' strategy metrics, or None
    """
    try:
        with open(eval_path) as f:
            data = json.load(f)
        return data.get('evaluation', {})
    except Exception:
        return None


def _find_matching_eval(results_dir: Path, model: str, strategy: str, mode: str) -> Optional[Dict]:
    """Find *_eval.json matching a CV result by model/strategy/mode.

    Looks for patterns like:
    - {model}_{strategy}_{mode}_intersected_kb_eval.json  (new run_compare output)
    - {model}_{strategy}_intersected_eval_{mode}.json      (old run_congen_eval output)
    """
    # New format: run_compare.py saves {kb_stem}_eval.json
    # KB stem for intersected: {model}_{strategy}_{mode}_intersected_kb
    new_pattern = f"{model}_{strategy}_{mode}_intersected_kb_eval.json"
    new_path = results_dir / new_pattern
    if new_path.exists():
        return load_eval_result(new_path)

    # Old format from run_congen_eval.py
    old_pattern = f"{model}_{strategy}_intersected_eval_{mode}.json"
    old_path = results_dir / old_pattern
    if old_path.exists():
        return load_eval_result(old_path)

    return None


def load_all_results(results_dir: Path) -> Dict[str, Dict[str, Dict[str, CVResult]]]:
    """Load all CV results. Returns: {model: {strategy: {mode: CVResult}}}

    Priority: embedded eval in unified JSON > separate *_eval.json > nothing
    """
    results = {}
    for filepath in results_dir.glob('*_cv_*.json'):
        result = load_cv_result(filepath)
        if result:
            # Only look for external eval if embedded is absent
            if not result.has_strategy_eval:
                ext_eval = _find_matching_eval(results_dir, result.model,
                                               result.strategy, result.mode)
                if ext_eval:
                    desc_eval = ext_eval.get('description', {}).get('metrics', {})
                    clause_eval = ext_eval.get('clause', {}).get('metrics', {})
                    result.desc_accuracy = desc_eval.get('accuracy', result.desc_accuracy)
                    result.desc_precision = desc_eval.get('precision', result.desc_precision)
                    result.desc_recall = desc_eval.get('recall', result.desc_recall)
                    result.desc_f1 = desc_eval.get('f1_score', result.desc_f1)
                    result.clause_accuracy = clause_eval.get('accuracy', result.clause_accuracy)
                    result.clause_precision = clause_eval.get('precision', result.clause_precision)
                    result.clause_recall = clause_eval.get('recall', result.clause_recall)
                    result.clause_f1 = clause_eval.get('f1_score', result.clause_f1)
                    result.has_strategy_eval = True

            results.setdefault(result.model, {}).setdefault(result.strategy, {})[result.mode] = result
    return results


# =============================================================================
# Table Helpers — DRY formatting infrastructure
# =============================================================================

def _get_result(results: Dict, kb_name: str, strategy: str, mode: str) -> Optional[CVResult]:
    """Look up a CVResult by KB name, strategy, and mode."""
    model = KB_REVERSE.get(kb_name)
    if model and model in results and strategy in results[model] and mode in results[model][strategy]:
        return results[model][strategy][mode]
    return None


def _compact_grid_md(
    title: str, results: Dict, mode: str,
    cell_fn: Callable[[CVResult], str],
    strategies: List[str] = None, align: str = ':---:'
) -> str:
    """Generate a compact KB-rows × Strategy-columns table in Markdown."""
    strats = strategies or STRATEGIES
    lines = [f"## {title} - {mode.capitalize()} Mode", ""]

    header = "| KB |" + "".join(f" {STRATEGY_NAMES[s]} |" for s in strats)
    sep = "|:---|" + "".join(f"{align}|" for _ in strats)
    lines.extend([header, sep])

    for kb in KB_NAMES:
        row = f"| {kb} |"
        for s in strats:
            r = _get_result(results, kb, s, mode)
            row += f" {cell_fn(r)} |" if r else " - |"
        lines.append(row)
    return "\n".join(lines)


def _latex_wrap(title: str, label: str, col_spec: str, header: str,
                body_lines: List[str], mode: str = '') -> str:
    """Wrap body lines in LaTeX table boilerplate."""
    caption = f"{title} ({mode.capitalize()})" if mode else title
    full_label = f"{label}_{mode}" if mode else label
    lines = [
        f"% {caption}",
        "\\begin{table}[htbp]", "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{tab:{full_label}}}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\toprule", header, "\\midrule",
    ]
    lines.extend(body_lines)
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    return "\n".join(lines)


def _compact_grid_latex(
    title: str, label: str, results: Dict, mode: str,
    cell_fn: Callable[[CVResult], str],
    strategies: List[str] = None
) -> str:
    """Generate a compact KB-rows × Strategy-columns table in LaTeX."""
    strats = strategies or STRATEGIES
    col_spec = "l" + "c" * len(strats)
    header = "KB" + "".join(f" & {STRATEGY_NAMES[s]}" for s in strats) + " \\\\"
    body = []
    for kb in KB_NAMES:
        row = kb
        for s in strats:
            r = _get_result(results, kb, s, mode)
            row += f" & {cell_fn(r)}" if r else " & -"
        row += " \\\\"
        body.append(row)
    return _latex_wrap(title, label, col_spec, header, body, mode)


# =============================================================================
# Table Generators — Compact grid tables (unified MD + LaTeX)
# =============================================================================

def generate_accuracy_table(results: Dict, mode: str, fmt: str) -> str:
    """Accuracy by Sampling Strategy (mean ± std)."""
    title = "Accuracy by Sampling Strategy"
    if fmt == 'md':
        return _compact_grid_md(f"Table: {title}", results, mode,
                                lambda r: f"{r.mean_accuracy:.4f} ± {r.std_accuracy:.4f}")
    return _compact_grid_latex(title, "accuracy", results, mode,
                               lambda r: f"{r.mean_accuracy:.4f} $\\pm$ {r.std_accuracy:.4f}")


def generate_accuracy_compact(results: Dict, mode: str) -> str:
    """Compact accuracy (fewer decimals, MD only)."""
    return _compact_grid_md("Table: Accuracy (Compact)", results, mode,
                            lambda r: f"{r.mean_accuracy:.2f}±{r.std_accuracy:.2f}")


def generate_fold_metrics_table(results: Dict, mode: str, fmt: str) -> str:
    """Fold-level Precision/Recall/F1."""
    title = "Precision / Recall / F1"
    cell = lambda r: f"{r.precision_mean:.2f}/{r.recall_mean:.2f}/{r.f1_mean:.2f}"
    if fmt == 'md':
        return _compact_grid_md(f"Table: Fold Metrics ({title})", results, mode, cell)
    return _compact_grid_latex(title, "fold_metrics", results, mode, cell)


def generate_runtime_compact(results: Dict, mode: str) -> str:
    """Compact runtime table (MD only)."""
    def cell(r):
        if r.runtime_mean_ms > 1000:
            return f"{r.runtime_mean_ms/1000:.2f}s"
        return f"{r.runtime_mean_ms:.0f}"
    return _compact_grid_md("Table: Runtime (ms)", results, mode, cell, align='---:')


def generate_checks_compact(results: Dict, mode: str) -> str:
    """Compact consistency checks (MD only)."""
    return _compact_grid_md("Table: Consistency Checks", results, mode,
                            lambda r: f"{r.checks_mean:.0f}", align='---:')


def generate_strategy_eval_table(results: Dict, mode: str, fmt: str, eval_strategy: str) -> str:
    """Strategy evaluation on intersected KB (Acc/Prec/Rec/F1)."""
    title = f"Strategy Eval ({eval_strategy.capitalize()}) on Intersected KB"

    if eval_strategy == 'description':
        cell = lambda r: (
            f"{r.desc_precision:.2f}/{r.desc_recall:.2f}/{r.desc_f1:.2f}"
            if r.has_strategy_eval else "-"
        )
    else:
        cell = lambda r: (
            f"{r.clause_precision:.2f}/{r.clause_recall:.2f}/{r.clause_f1:.2f}"
            if r.has_strategy_eval else "-"
        )

    if fmt == 'md':
        return _compact_grid_md(f"Table: {title}", results, mode, cell)
    return _compact_grid_latex(title, f"eval_{eval_strategy}", results, mode, cell)


# =============================================================================
# Table Generators — Detail tables (KB × Strategy rows)
# =============================================================================

def generate_performance_table(results: Dict, mode: str, fmt: str) -> str:
    """Performance metrics detail table."""
    if fmt == 'md':
        lines = [f"## Table: Performance Metrics ({mode.capitalize()})", "",
                 "| KB | Strategy | Runtime (ms) | #Checks | Memory (MB) | n_bias | n_mss | n_kb |",
                 "|:---|:---|---:|---:|---:|---:|---:|---:|"]
        for kb in KB_NAMES:
            for s in STRATEGIES:
                r = _get_result(results, kb, s, mode)
                if not r:
                    continue
                lines.append(
                    f"| {kb} | {STRATEGY_NAMES[s]} |"
                    f" {r.runtime_mean_ms:.2f} ± {r.runtime_std_ms:.2f} |"
                    f" {r.checks_mean:.0f} ± {r.checks_std:.0f} |"
                    f" {r.memory_max_mb:.2f} | {r.n_bias} |"
                    f" {r.n_mss_mean:.1f} | {r.n_kb_mean:.1f} |")
        return "\n".join(lines)

    # LaTeX
    body = []
    for kb in KB_NAMES:
        first_row = True
        for s in STRATEGIES:
            r = _get_result(results, kb, s, mode)
            if not r:
                continue
            kb_col = kb if first_row else ""
            body.append(
                f"{kb_col} & {STRATEGY_NAMES[s]} &"
                f" {r.runtime_mean_ms:.2f} $\\pm$ {r.runtime_std_ms:.2f} &"
                f" {r.checks_mean:.0f} $\\pm$ {r.checks_std:.0f} &"
                f" {r.memory_max_mb:.2f} & {r.n_bias} &"
                f" {r.n_mss_mean:.1f} & {r.n_kb_mean:.1f} \\\\")
            first_row = False
        if not first_row:
            body.append("\\midrule")
    if body and body[-1] == "\\midrule":
        body.pop()
    return _latex_wrap("Performance Metrics", "performance", "llrrrrrr",
                       "KB & Strategy & Runtime (ms) & \\#Checks & Memory (MB) & $|B|$ & $|MSS|$ & $|KB|$ \\\\",
                       body, mode)


def generate_kb_summary(results: Dict, mode: str, fmt: str) -> str:
    """KB summary table (bias/kb/intersected/reduction)."""
    def _reduction(r):
        return (1 - r.n_kb_mean / r.n_bias) * 100 if r.n_bias > 0 else 0

    if fmt == 'md':
        lines = [f"## Table: KB Summary ({mode.capitalize()})", "",
                 "| KB | Strategy | n_bias | n_kb (mean) | n_intersected | Reduction |",
                 "|:---|:---|---:|---:|---:|---:|"]
        for kb in KB_NAMES:
            for s in STRATEGIES:
                r = _get_result(results, kb, s, mode)
                if not r:
                    continue
                lines.append(
                    f"| {kb} | {STRATEGY_NAMES[s]} |"
                    f" {r.n_bias} | {r.n_kb_mean:.1f} |"
                    f" {r.n_intersected} | {_reduction(r):.1f}% |")
        return "\n".join(lines)

    # LaTeX
    body = []
    for kb in KB_NAMES:
        first_row = True
        for s in STRATEGIES:
            r = _get_result(results, kb, s, mode)
            if not r:
                continue
            kb_col = kb if first_row else ""
            body.append(
                f"{kb_col} & {STRATEGY_NAMES[s]} &"
                f" {r.n_bias} & {r.n_kb_mean:.1f} &"
                f" {r.n_intersected} & {_reduction(r):.1f}\\% \\\\")
            first_row = False
        if not first_row:
            body.append("\\midrule")
    if body and body[-1] == "\\midrule":
        body.pop()
    return _latex_wrap("KB Summary", "kb_summary", "llrrrr",
                       "KB & Strategy & $|B|$ & $|KB|$ (mean) & $|KB_{\\cap}|$ & Reduction \\\\",
                       body, mode)


def generate_incremental_comparison(results: Dict, fmt: str) -> str:
    """Incremental vs Non-Incremental comparison table."""
    if fmt == 'md':
        lines = ["## Table: Incremental vs Non-Incremental Comparison", "",
                 "| KB | Strategy | Mode | Accuracy | Runtime (ms) | #Checks |",
                 "|:---|:---|:---|---:|---:|---:|"]
        for kb in KB_NAMES:
            for s in STRATEGIES:
                for mode in ['incremental', 'non-incremental']:
                    r = _get_result(results, kb, s, mode)
                    if not r:
                        continue
                    ms = 'Inc' if mode == 'incremental' else 'Non-Inc'
                    lines.append(
                        f"| {kb} | {STRATEGY_NAMES[s]} | {ms} |"
                        f" {r.mean_accuracy:.4f} | {r.runtime_mean_ms:.2f} |"
                        f" {r.checks_mean:.0f} |")
        return "\n".join(lines)

    # LaTeX
    body = []
    for kb in KB_NAMES:
        first_kb = True
        for s in STRATEGIES:
            first_s = True
            for mode in ['incremental', 'non-incremental']:
                r = _get_result(results, kb, s, mode)
                if not r:
                    continue
                kb_col = kb if first_kb else ""
                s_col = STRATEGY_NAMES[s] if first_s else ""
                ms = 'Inc' if mode == 'incremental' else 'Non-Inc'
                body.append(
                    f"{kb_col} & {s_col} & {ms} &"
                    f" {r.mean_accuracy:.4f} & {r.runtime_mean_ms:.2f} &"
                    f" {r.checks_mean:.0f} \\\\")
                first_kb = False
                first_s = False
        body.append("\\midrule")
    if body and body[-1] == "\\midrule":
        body.pop()
    return _latex_wrap("Incremental vs Non-Incremental Comparison", "inc_vs_noninc",
                       "lllrrr",
                       "KB & Strategy & Mode & Accuracy & Runtime (ms) & \\#Checks \\\\",
                       body)


# =============================================================================
# Paper Tables (Tables 7, 9, 10, 11)
# =============================================================================

def generate_table7(results: Dict, mode: str, fmt: str) -> str:
    """Table 7: AcqMSS #consistency checks and runtime (msec)."""
    def _row_data(strategy):
        n_pos, n_neg = '-', '-'
        for kb in KB_NAMES:
            r = _get_result(results, kb, strategy, mode)
            if r and (r.n_positive > 0 or r.n_negative > 0):
                n_pos, n_neg = str(r.n_positive), str(r.n_negative)
                break
        cells = []
        for kb in KB_NAMES:
            r = _get_result(results, kb, strategy, mode)
            cells.append(f"{r.checks_mean:.0f} / {r.runtime_mean_ms:.1f}" if r else "-")
        return n_pos, n_neg, cells

    title = "AcqMSS #consistency checks and runtime (msec)"
    if fmt == 'md':
        lines = [f"## Table 7: {title} - {mode.capitalize()} Mode", "",
                 "| Strategy | |E+| | |E-| | KB1 | KB2 | KB3 | KB4 |",
                 "|:---|---:|---:|:---:|:---:|:---:|:---:|"]
        for s in STRATEGIES:
            np, nn, cells = _row_data(s)
            lines.append(f"| {STRATEGY_NAMES[s]} | {np} | {nn} | " + " | ".join(cells) + " |")
        return "\n".join(lines)

    # LaTeX
    body = []
    for s in STRATEGIES:
        np, nn, cells = _row_data(s)
        body.append(f"{STRATEGY_NAMES[s]} & {np} & {nn} & " + " & ".join(cells) + " \\\\")
    return _latex_wrap(f"AcqMSS \\#consistency checks and runtime (msec) - {mode.capitalize()}",
                       f"table7_{mode}", "lrrcccc",
                       "Strategy & $|E^+|$ & $|E^-|$ & KB1 & KB2 & KB3 & KB4 \\\\",
                       body)


def generate_table9(results: Dict, mode: str, fmt: str) -> str:
    """Table 9: Accuracy with Random Sampling (RS)."""
    rs = ['rs_1n', 'rs_2n', 'rs_3n', 'rs_m']
    title = "Accuracy with Random Sampling (RS)"

    if fmt == 'md':
        lines = [f"## Table 9: {title} - {mode.capitalize()} Mode", "",
                 "| Strategy | KB1 | KB2 | KB3 | KB4 |",
                 "|:---|:---:|:---:|:---:|:---:|"]
        for s in rs:
            row = f"| {STRATEGY_NAMES[s]} |"
            for kb in KB_NAMES:
                r = _get_result(results, kb, s, mode)
                row += f" {r.mean_accuracy:.4f} ± {r.std_accuracy:.4f} |" if r else " - |"
            lines.append(row)
        return "\n".join(lines)

    # LaTeX
    body = []
    for s in rs:
        row = STRATEGY_NAMES[s]
        for kb in KB_NAMES:
            r = _get_result(results, kb, s, mode)
            row += f" & {r.mean_accuracy:.4f} $\\pm$ {r.std_accuracy:.4f}" if r else " & -"
        body.append(row + " \\\\")
    return _latex_wrap(f"{title} - {mode.capitalize()}", f"table9_{mode}",
                       "lcccc", "Strategy & KB1 & KB2 & KB3 & KB4 \\\\", body)


def generate_single_strategy_table(
    results: Dict, mode: str, fmt: str, strategy: str, table_num: int, title: str
) -> str:
    """Tables 10/11: single-strategy accuracy table (2-COV or FF)."""
    if fmt == 'md':
        lines = [f"## Table {table_num}: {title} - {mode.capitalize()} Mode", "",
                 "| KB | Accuracy |", "|:---|:---:|"]
        for kb in KB_NAMES:
            r = _get_result(results, kb, strategy, mode)
            if r:
                lines.append(f"| {kb} | {r.mean_accuracy:.4f} ± {r.std_accuracy:.4f} |")
            else:
                lines.append(f"| {kb} | - |")
        return "\n".join(lines)

    # LaTeX
    body = []
    for kb in KB_NAMES:
        r = _get_result(results, kb, strategy, mode)
        if r:
            body.append(f"{kb} & {r.mean_accuracy:.4f} $\\pm$ {r.std_accuracy:.4f} \\\\")
        else:
            body.append(f"{kb} & - \\\\")
    return _latex_wrap(f"{title} - {mode.capitalize()}", f"table{table_num}_{mode}",
                       "lc", "KB & Accuracy \\\\", body)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = build_parser(
        description='Extract evaluation results and generate tables',
        config='optional',
        verbose=False,
        epilog='Usage: PYTHONPATH=. python apps/extract_results.py apps/conf/extract_results_config.toml'
    )
    parser.add_argument('--results-dir', type=str, default=None,
                        help='Directory containing CV result JSON files')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Directory to save generated tables')
    parser.add_argument('--mode', type=str, choices=['incremental', 'non-incremental', 'both'],
                        default=None, help='Solver mode to include in tables')
    args = parser.parse_args()

    # Load defaults from TOML config if provided
    toml_config = {}
    if args.config and Path(args.config).exists():
        toml_config = load_config(args.config)

    general = toml_config.get('general', {})
    results_dir = Path(args.results_dir or general.get('results_dir', 'data/results'))
    output_dir = Path(args.output_dir or general.get('output_dir', 'paper/tables'))
    output_dir.mkdir(parents=True, exist_ok=True)

    mode = args.mode or general.get('mode', 'both')

    print(f"Loading results from: {results_dir}")
    results = load_all_results(results_dir)

    # Summary
    print(f"\nLoaded results:")
    for model in sorted(results.keys()):
        strats = sorted(results[model].keys())
        modes = set()
        for s in strats:
            modes.update(results[model][s].keys())
        print(f"  {model}: {len(strats)} strategies, modes: {sorted(modes)}")

    print(f"\nGenerating tables to: {output_dir}")
    modes_to_gen = ['incremental', 'non-incremental'] if mode == 'both' else [mode]

    md_content = [
        "# Evaluation Results\n",
        f"Generated from: {results_dir}\n",
        "KB Mapping: KB1=REAL-FM-7, KB2=fqa, KB3=arcade, KB4=REAL-FM-4\n",
    ]
    latex_content = [
        "% Evaluation Results",
        "% KB Mapping: KB1=REAL-FM-7, KB2=fqa, KB3=arcade, KB4=REAL-FM-4",
        "\\usepackage{booktabs}", "",
    ]

    for mode in modes_to_gen:
        # Paper Tables
        md_content.append(f"\n# Paper Tables ({mode.capitalize()})")
        for gen in [
            generate_table7,
            generate_table9,
            lambda r, m, f: generate_single_strategy_table(r, m, f, '2cov', 10, 'Accuracy with 2-COV'),
            lambda r, m, f: generate_single_strategy_table(r, m, f, 'ff', 11, 'Accuracy with FF'),
        ]:
            md_content.append("\n" + gen(results, mode, 'md'))
            latex_content.append("\n" + gen(results, mode, 'latex'))

        # Additional Tables
        md_content.append(f"\n# Additional Tables ({mode.capitalize()})")
        md_content.append("\n" + generate_fold_metrics_table(results, mode, 'md'))
        latex_content.append("\n" + generate_fold_metrics_table(results, mode, 'latex'))
        md_content.append("\n" + generate_accuracy_compact(results, mode))
        md_content.append("\n" + generate_accuracy_table(results, mode, 'md'))
        latex_content.append("\n" + generate_accuracy_table(results, mode, 'latex'))
        md_content.append("\n" + generate_runtime_compact(results, mode))
        md_content.append("\n" + generate_checks_compact(results, mode))
        md_content.append("\n" + generate_performance_table(results, mode, 'md'))
        latex_content.append("\n" + generate_performance_table(results, mode, 'latex'))
        md_content.append("\n" + generate_kb_summary(results, mode, 'md'))
        latex_content.append("\n" + generate_kb_summary(results, mode, 'latex'))

        # Strategy evaluation tables (only if any result has eval data)
        has_eval = any(
            r.has_strategy_eval
            for model_strats in results.values()
            for strat_modes in model_strats.values()
            for r in strat_modes.values()
            if r.mode == mode
        )
        if has_eval:
            md_content.append(f"\n# Strategy Evaluation ({mode.capitalize()})")
            for eval_strat in ['description', 'clause']:
                md_content.append("\n" + generate_strategy_eval_table(results, mode, 'md', eval_strat))
                latex_content.append("\n" + generate_strategy_eval_table(results, mode, 'latex', eval_strat))

    if mode == 'both':
        md_content.append("\n" + generate_incremental_comparison(results, 'md'))
        latex_content.append("\n" + generate_incremental_comparison(results, 'latex'))

    md_file = output_dir / "results_tables.md"
    write_text_atomic(md_file, "\n".join(md_content))
    print(f"  Markdown tables: {md_file}")

    latex_file = output_dir / "results_tables.tex"
    write_text_atomic(latex_file, "\n".join(latex_content))
    print(f"  LaTeX tables: {latex_file}")

    print("\nDone!")


if __name__ == '__main__':
    main()
