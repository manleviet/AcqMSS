#!/usr/bin/env python
"""
Evaluate ConGen results against Oracle FM.

Evaluates KB results using both description-based and clause-based strategies.

Usage:
    # Evaluate all intersected_kb files in data/results
    PYTHONPATH=. python apps/evaluate_congen_results.py

    # Evaluate specific files
    PYTHONPATH=. python apps/evaluate_congen_results.py data/results/arcade-game_2cov_non-incremental_intersected_kb.json

    # With TOML config
    PYTHONPATH=. python apps/evaluate_congen_results.py apps/conf/evaluate_congen_config.toml
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from acqmss.eval.evaluator import Evaluator, EvaluationStrategy
from acqmss.eval.result_loader import ConGenResultData


@dataclass
class EvaluationEntry:
    """Single evaluation result entry."""
    model: str
    strategy: str  # rs_1n, rs_2n, etc.
    mode: str  # incremental, non-incremental
    n_kb: int
    # Description-based metrics
    desc_accuracy: float
    desc_precision: float
    desc_recall: float
    desc_f1: float
    desc_tp: int
    desc_fp: int
    desc_fn: int
    # Clause-based metrics
    clause_accuracy: float
    clause_precision: float
    clause_recall: float
    clause_f1: float
    clause_tp: int
    clause_fp: int
    clause_fn: int
    clause_tn: int
    # Source file
    source_file: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'model': self.model,
            'strategy': self.strategy,
            'mode': self.mode,
            'n_kb': self.n_kb,
            'description': {
                'accuracy': self.desc_accuracy,
                'precision': self.desc_precision,
                'recall': self.desc_recall,
                'f1_score': self.desc_f1,
                'tp': self.desc_tp,
                'fp': self.desc_fp,
                'fn': self.desc_fn,
            },
            'clause': {
                'accuracy': self.clause_accuracy,
                'precision': self.clause_precision,
                'recall': self.clause_recall,
                'f1_score': self.clause_f1,
                'tp': self.clause_tp,
                'fp': self.clause_fp,
                'fn': self.clause_fn,
                'tn': self.clause_tn,
            },
            'source_file': self.source_file,
        }


def parse_result_filename(filepath: Path) -> Dict[str, str]:
    """
    Parse result filename to extract model, strategy, and mode.

    Expected format: {model}_{strategy}_{mode}_intersected_kb.json
    Examples:
        - arcade-game_2cov_non-incremental_intersected_kb.json
        - REAL-FM-7_rs_1n_incremental_intersected_kb.json
    """
    filename = filepath.stem  # Remove .json

    # Remove _intersected_kb suffix
    if filename.endswith('_intersected_kb'):
        filename = filename[:-len('_intersected_kb')]

    # Split by mode (incremental or non-incremental)
    if '_non-incremental' in filename:
        parts = filename.rsplit('_non-incremental', 1)
        mode = 'non-incremental'
    elif '_incremental' in filename:
        parts = filename.rsplit('_incremental', 1)
        mode = 'incremental'
    else:
        return {'model': filename, 'strategy': 'unknown', 'mode': 'unknown'}

    # Parse model and strategy
    model_strategy = parts[0]

    # Known strategies
    strategies = ['rs_1n', 'rs_2n', 'rs_3n', 'rs_m', '2cov', 'ff']

    for strat in strategies:
        if model_strategy.endswith(f'_{strat}'):
            model = model_strategy[:-len(f'_{strat}')]
            return {'model': model, 'strategy': strat, 'mode': mode}

    # Fallback
    return {'model': model_strategy, 'strategy': 'unknown', 'mode': mode}


def find_fm_and_bias(model: str, fm_dir: Path, bias_dir: Path) -> tuple:
    """
    Find FM and bias files for a model.

    Returns:
        (fm_path, bias_path) or (None, None) if not found
    """
    fm_path = fm_dir / f"{model}.uvl"
    bias_path = bias_dir / f"{model}-bias.json"

    if fm_path.exists() and bias_path.exists():
        return fm_path, bias_path

    return None, None


def evaluate_result_file(
    result_path: Path,
    fm_dir: Path,
    bias_dir: Path,
    verbose: bool = False
) -> Optional[EvaluationEntry]:
    """
    Evaluate a single ConGen result file.

    Args:
        result_path: Path to intersected_kb.json file
        fm_dir: Directory containing FM files
        bias_dir: Directory containing bias files
        verbose: Enable verbose output

    Returns:
        EvaluationEntry or None if evaluation failed
    """
    # Parse filename
    info = parse_result_filename(result_path)
    model = info['model']
    strategy = info['strategy']
    mode = info['mode']

    if verbose:
        print(f"  Processing: {result_path.name}")
        print(f"    Model: {model}, Strategy: {strategy}, Mode: {mode}")

    # Find FM and bias files
    fm_path, bias_path = find_fm_and_bias(model, fm_dir, bias_dir)

    if fm_path is None:
        if verbose:
            print(f"    Warning: FM or bias not found for model '{model}'")
        return None

    # Load result
    with open(result_path, 'r') as f:
        result_data = json.load(f)

    kb_constraints = result_data.get('kb_constraints', [])
    stats = result_data.get('statistics', {})
    n_kb = stats.get('n_kb', len(kb_constraints))

    # Create evaluator
    try:
        evaluator = Evaluator.from_files(fm_path, bias_path)
    except Exception as e:
        if verbose:
            print(f"    Error creating evaluator: {e}")
        return None

    # Create ConGenResultData
    congen_result = ConGenResultData(
        kb_constraints=kb_constraints,
        redundant_constraints=[],
        n_bias=len(evaluator.bias.constraints),
        n_mss=0,
        n_kb=n_kb,
        bg_clauses=result_data.get('bg_clauses', [])
    )

    # Evaluate with both strategies
    try:
        desc_eval = evaluator.evaluate(congen_result, EvaluationStrategy.DESCRIPTION)
        clause_eval = evaluator.evaluate(congen_result, EvaluationStrategy.CLAUSE)
    except Exception as e:
        if verbose:
            print(f"    Error during evaluation: {e}")
        return None

    desc_m = desc_eval.metrics
    clause_m = clause_eval.metrics

    entry = EvaluationEntry(
        model=model,
        strategy=strategy,
        mode=mode,
        n_kb=n_kb,
        # Description metrics
        desc_accuracy=desc_m.accuracy,
        desc_precision=desc_m.precision,
        desc_recall=desc_m.recall,
        desc_f1=desc_m.f1_score,
        desc_tp=desc_m.true_positives,
        desc_fp=desc_m.false_positives,
        desc_fn=desc_m.false_negatives,
        # Clause metrics
        clause_accuracy=clause_m.accuracy,
        clause_precision=clause_m.precision,
        clause_recall=clause_m.recall,
        clause_f1=clause_m.f1_score,
        clause_tp=clause_m.true_positives,
        clause_fp=clause_m.false_positives,
        clause_fn=clause_m.false_negatives,
        clause_tn=clause_m.true_negatives,
        source_file=str(result_path)
    )

    if verbose:
        print(f"    |KB|={n_kb}, Desc.Acc={desc_m.accuracy:.4f}, Clause.Acc={clause_m.accuracy:.4f}")

    return entry


def print_summary_table(entries: List[EvaluationEntry]) -> str:
    """Generate summary table."""
    lines = []

    # Header
    lines.append("=" * 120)
    lines.append("ConGen Evaluation Results (Both Strategies)")
    lines.append("=" * 120)

    header = (f"{'Model':<15} {'Strategy':<8} {'Mode':<15} {'|KB|':>5} "
              f"{'Desc.Acc':>9} {'Desc.P':>7} {'Desc.R':>7} {'Desc.F1':>8} "
              f"{'Cls.Acc':>8} {'Cls.P':>6} {'Cls.R':>6} {'Cls.F1':>7}")
    lines.append(header)
    lines.append("-" * 120)

    # Group by model
    models = sorted(set(e.model for e in entries))

    for model in models:
        model_entries = [e for e in entries if e.model == model]
        for e in sorted(model_entries, key=lambda x: (x.strategy, x.mode)):
            line = (f"{e.model:<15} {e.strategy:<8} {e.mode:<15} {e.n_kb:>5} "
                    f"{e.desc_accuracy:>9.4f} {e.desc_precision:>7.4f} {e.desc_recall:>7.4f} {e.desc_f1:>8.4f} "
                    f"{e.clause_accuracy:>8.4f} {e.clause_precision:>6.4f} {e.clause_recall:>6.4f} {e.clause_f1:>7.4f}")
            lines.append(line)
        lines.append("-" * 120)

    # Summary statistics
    if entries:
        avg_desc_acc = sum(e.desc_accuracy for e in entries) / len(entries)
        avg_clause_acc = sum(e.clause_accuracy for e in entries) / len(entries)
        lines.append(f"Average: Desc.Accuracy={avg_desc_acc:.4f}, Clause.Accuracy={avg_clause_acc:.4f}")

    lines.append("=" * 120)

    return "\n".join(lines)


def load_config(config_path: str) -> Dict[str, Any]:
    """Load TOML configuration file."""
    with open(config_path, 'rb') as f:
        return tomllib.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate ConGen results against Oracle FM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Evaluate all intersected_kb files
    PYTHONPATH=. python apps/evaluate_congen_results.py

    # Evaluate specific files
    PYTHONPATH=. python apps/evaluate_congen_results.py data/results/arcade-game_2cov_non-incremental_intersected_kb.json

    # With TOML config
    PYTHONPATH=. python apps/evaluate_congen_results.py apps/conf/evaluate_congen_config.toml
        """
    )
    parser.add_argument('inputs', nargs='*',
                        help='Result files or TOML config (default: all intersected_kb.json in data/results)')
    parser.add_argument('-o', '--output-dir', default='data/kb_eval',
                        help='Output directory (default: data/kb_eval)')
    parser.add_argument('--fm-dir', default='data/fms',
                        help='Directory containing FM files')
    parser.add_argument('--bias-dir', default='data/bias',
                        help='Directory containing bias files')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')

    args = parser.parse_args()

    fm_dir = Path(args.fm_dir)
    bias_dir = Path(args.bias_dir)
    output_dir = Path(args.output_dir)

    # Determine input files
    result_files = []

    if not args.inputs:
        # Default: all intersected_kb.json files
        results_dir = Path('data/results')
        if results_dir.exists():
            result_files = list(results_dir.glob('*_intersected_kb.json'))
    else:
        for input_path in args.inputs:
            path = Path(input_path)
            if path.suffix == '.toml':
                # Load TOML config
                config = load_config(input_path)
                general = config.get('general', {})

                # Override directories from config if not specified in CLI
                if args.fm_dir == 'data/fms' and 'fm_dir' in general:
                    fm_dir = Path(general['fm_dir'])
                if args.bias_dir == 'data/bias' and 'bias_dir' in general:
                    bias_dir = Path(general['bias_dir'])
                if args.output_dir == 'data/kb_eval' and 'output_dir' in general:
                    output_dir = Path(general['output_dir'])

                # Get files list from config
                files = general.get('files', config.get('files', []))
                for f in files:
                    fp = Path(f)
                    if fp.exists():
                        result_files.append(fp)
                    else:
                        print(f"Warning: File not found: {f}")
            elif path.suffix == '.json':
                if path.exists():
                    result_files.append(path)
            elif path.is_dir():
                result_files.extend(path.glob('*_intersected_kb.json'))

    if not result_files:
        print("No result files found.")
        sys.exit(1)

    print("=" * 80)
    print("ConGen Results Evaluation")
    print("=" * 80)
    print(f"Input files: {len(result_files)}")
    print(f"FM directory: {fm_dir}")
    print(f"Bias directory: {bias_dir}")
    print(f"Output directory: {output_dir}")
    print()

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Evaluate each file
    entries = []

    for result_file in sorted(result_files):
        entry = evaluate_result_file(result_file, fm_dir, bias_dir, args.verbose)
        if entry:
            entries.append(entry)

    if not entries:
        print("No successful evaluations.")
        sys.exit(1)

    # Print summary
    print()
    summary = print_summary_table(entries)
    print(summary)

    # Save results
    # 1. JSON with all details
    output_json = output_dir / "congen_evaluation.json"
    with open(output_json, 'w') as f:
        json.dump({
            'evaluations': [e.to_dict() for e in entries],
            'summary': {
                'n_files': len(entries),
                'avg_desc_accuracy': sum(e.desc_accuracy for e in entries) / len(entries),
                'avg_clause_accuracy': sum(e.clause_accuracy for e in entries) / len(entries),
            }
        }, f, indent=2)
    print(f"\nSaved: {output_json}")

    # 2. Summary table as text
    output_txt = output_dir / "congen_evaluation_summary.txt"
    with open(output_txt, 'w') as f:
        f.write(summary)
    print(f"Saved: {output_txt}")

    # 3. CSV for easy analysis
    output_csv = output_dir / "congen_evaluation.csv"
    with open(output_csv, 'w') as f:
        # Header
        f.write("model,strategy,mode,n_kb,"
                "desc_accuracy,desc_precision,desc_recall,desc_f1,desc_tp,desc_fp,desc_fn,"
                "clause_accuracy,clause_precision,clause_recall,clause_f1,clause_tp,clause_fp,clause_fn,clause_tn\n")
        for e in entries:
            f.write(f"{e.model},{e.strategy},{e.mode},{e.n_kb},"
                    f"{e.desc_accuracy:.6f},{e.desc_precision:.6f},{e.desc_recall:.6f},{e.desc_f1:.6f},"
                    f"{e.desc_tp},{e.desc_fp},{e.desc_fn},"
                    f"{e.clause_accuracy:.6f},{e.clause_precision:.6f},{e.clause_recall:.6f},{e.clause_f1:.6f},"
                    f"{e.clause_tp},{e.clause_fp},{e.clause_fn},{e.clause_tn}\n")
    print(f"Saved: {output_csv}")

    print()
    print(f"Successfully evaluated {len(entries)} result files.")


if __name__ == '__main__':
    main()
