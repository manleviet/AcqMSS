#!/usr/bin/env python
"""
Compare learned KB(s) against ground truth feature model.

Config mode reads unified CV JSON files, compares each fold + intersected KB,
writes evaluation and summary back into the same file (idempotent).

CLI mode compares standalone KB files and saves separate eval JSONs.

Usage:
    # Config mode (batch all models — unified CV flow)
    python -m apps.run_compare apps/conf/run_compare_config.toml -v

    # CLI mode (single model — legacy standalone KB files)
    python -m apps.run_compare --kb data/results/model_kb.json --bias path --oracle path
"""

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import List

from conacq.config import (
    find_cv_files, find_kb_files, load_pipeline_config, parse_models,
)
from conacq.eval.kb_comparator import KBComparator, ComparationStrategy
from conacq.eval.result_loader import ConGenResultData
from conacq.oracle.ground_truth import GroundTruthData
from conacq.bias import BiasIO


def get_strategies(strategy_config: str) -> List[ComparationStrategy]:
    """Parse strategy config string into list of strategies.

    Options: 'all' (all 3), 'description', 'clause', 'semantic'
    """
    if strategy_config == 'all':
        return [
            ComparationStrategy.DESCRIPTION,
            ComparationStrategy.CLAUSE,
            ComparationStrategy.SEMANTIC,
        ]
    elif strategy_config == 'description':
        return [ComparationStrategy.DESCRIPTION]
    elif strategy_config == 'clause':
        return [ComparationStrategy.CLAUSE]
    elif strategy_config == 'semantic':
        return [ComparationStrategy.SEMANTIC]
    return [ComparationStrategy.DESCRIPTION]


# ── Unified CV flow (config mode) ──────────────────────────────


def compare_entry(entry: dict, comparator: KBComparator,
                  bias, strategies: List[ComparationStrategy],
                  verbose: bool, label: str = "") -> dict:
    """Compare a fold or intersected KB entry. Returns evaluation dict."""
    result_data = ConGenResultData.from_dict(entry)
    eval_dict = {}
    for strategy in strategies:
        com_result = comparator.compare(result_data, strategy)
        eval_dict[strategy.value] = com_result.to_enriched_dict(bias)
        if verbose:
            m = com_result.metrics
            print(f"    {label}{strategy.value}: "
                  f"P={m.precision:.4f}, R={m.recall:.4f}, F1={m.f1_score:.4f}")
    return eval_dict


def _mean_std(values: list) -> dict:
    """Compute mean and population std."""
    if not values:
        return {'mean': 0.0, 'std': 0.0}
    m = statistics.mean(values)
    s = statistics.pstdev(values) if len(values) > 1 else 0.0
    return {'mean': round(m, 6), 'std': round(s, 6)}


def compute_summary(data: dict, strategies: List[ComparationStrategy]) -> dict:
    """Compute mean/std of P, R, F1 across folds per strategy."""
    summary = {}
    for strategy in strategies:
        key = strategy.value
        precisions, recalls, f1s = [], [], []
        for fold in data.get('folds', []):
            ev = fold.get('evaluation') or {}
            if key in ev:
                m = ev[key].get('metrics', {})
                precisions.append(m.get('precision', 0.0))
                recalls.append(m.get('recall', 0.0))
                f1s.append(m.get('f1_score', 0.0))
        summary[key] = {
            'precision': _mean_std(precisions),
            'recall': _mean_std(recalls),
            'f1_score': _mean_std(f1s),
        }
    return summary


def compare_model_unified(model, strategies, verbose):
    """Compare all unified CV files for a model."""
    if not model.kb_dir:
        print(f"  Warning: No kb_dir configured for {model.name}")
        return 0
    kb_path = Path(model.kb_dir)
    if not kb_path.exists():
        print(f"  Warning: kb_dir not found: {model.kb_dir}")
        return 0

    cv_files = find_cv_files(kb_path)
    if not cv_files:
        print(f"  Warning: No CV files found in {model.kb_dir}")
        return 0

    bias = BiasIO.load_from_json(model.bias)
    oracle = GroundTruthData.from_uvl(Path(model.oracle))
    comparator = KBComparator(oracle, bias)

    count = 0
    for cv_file in cv_files:
        print(f"  {cv_file.name}")
        with open(cv_file) as f:
            data = json.load(f)

        # Compare each fold
        for fold in data.get('folds', []):
            label = f"Fold {fold.get('fold_index', '?')}: "
            fold['evaluation'] = compare_entry(
                fold, comparator, bias, strategies, verbose, label)

        # Compare intersected KB
        ik = data.get('intersected_kb', {})
        if ik and ik.get('kb_constraints'):
            ik['evaluation'] = compare_entry(
                ik, comparator, bias, strategies, verbose, "Intersected: ")

        # Compute summary
        data['summary'] = compute_summary(data, strategies)
        if verbose:
            for key, vals in data['summary'].items():
                p, r, f1 = vals['precision'], vals['recall'], vals['f1_score']
                print(f"    Summary({key}): "
                      f"P={p['mean']:.4f}+/-{p['std']:.4f}, "
                      f"R={r['mean']:.4f}+/-{r['std']:.4f}, "
                      f"F1={f1['mean']:.4f}+/-{f1['std']:.4f}")

        # Write back (idempotent)
        with open(cv_file, 'w') as f:
            json.dump(data, f, indent=2)
        count += 1

    return count


def run_config_mode(config_path: str, verbose: bool, output_dir_override: str = None):
    """Run in config mode: batch compare unified CV files."""
    config = load_pipeline_config(config_path)
    models = parse_models(config)
    if not models:
        print("Error: No models specified in configuration")
        sys.exit(1)

    general = config.get('general', {})
    compare_config = config.get('compare', {})
    verbose = verbose or general.get('verbose', False)
    strategy_str = compare_config.get('strategy', 'all')
    strategies = get_strategies(strategy_str)

    print("=" * 60)
    print("KB Comparison (unified CV mode)")
    print("=" * 60)
    print(f"Config: {config_path}")
    print(f"Models: {len(models)}")
    print(f"Strategies: {[s.value for s in strategies]}")

    total = 0
    for model in models:
        print(f"\n--- {model.name} ---")
        total += compare_model_unified(model, strategies, verbose)

    print(f"\nDone. Compared {total} unified CV files across {len(models)} models.")


# ── CLI mode (legacy standalone KB files) ──────────────────────


def compare_kb(kb_path: Path, comparator: KBComparator,
               strategies: List[ComparationStrategy],
               output_dir: Path, verbose: bool) -> dict:
    """Compare a single standalone KB file against ground truth."""
    result_data = ConGenResultData.from_json(kb_path)

    eval_result = {}
    for strategy in strategies:
        com_result = comparator.compare(result_data, strategy)
        eval_result[strategy.value] = com_result.to_dict()
        if verbose:
            m = com_result.metrics
            print(f"  {strategy.value}: P={m.precision:.4f}, R={m.recall:.4f}, F1={m.f1_score:.4f}")

    eval_file = output_dir / f"{kb_path.stem}_eval.json"
    eval_data = {
        'source_kb': str(kb_path),
        'n_kb': result_data.n_kb,
        'evaluation': eval_result,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(eval_file, 'w') as f:
        json.dump(eval_data, f, indent=2)

    return eval_result


def run_cli_mode(args):
    """Run in CLI mode: single model comparison (standalone KB files)."""
    kb_path = Path(args.kb)
    if not kb_path.exists():
        print(f"Error: KB path not found: {args.kb}")
        sys.exit(1)

    kb_files = find_kb_files(kb_path)
    if not kb_files:
        print(f"Error: No KB files found at: {args.kb}")
        sys.exit(1)

    bias = BiasIO.load_from_json(args.bias)
    oracle = GroundTruthData.from_uvl(Path(args.oracle))
    comparator = KBComparator(oracle, bias)
    strategies = get_strategies(args.strategy)

    output_dir = Path(args.output_dir) if args.output_dir else (
        kb_path if kb_path.is_dir() else kb_path.parent
    )

    print("=" * 60)
    print("KB Comparison (CLI mode)")
    print("=" * 60)
    print(f"KB files: {len(kb_files)}")
    print(f"Strategies: {[s.value for s in strategies]}")
    print(f"Output: {output_dir}")

    for kb_file in kb_files:
        print(f"\n--- {kb_file.name} ---")
        compare_kb(kb_file, comparator, strategies, output_dir, args.verbose)

    print(f"\nDone. Eval files saved to {output_dir}")


# ── Main ───────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Compare learned KB(s) against ground truth FM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    # Config mode (unified CV files)
    python -m apps.run_compare apps/conf/run_compare_config.toml -v

    # CLI mode (standalone KB files)
    python -m apps.run_compare --kb data/results/model_kb.json --bias path --oracle path
        """
    )
    parser.add_argument('config', nargs='?', default=None,
                        help='Path to TOML config file (config mode)')
    parser.add_argument('--kb', help='KB file or directory (CLI mode)')
    parser.add_argument('--bias', help='Path to bias JSON file (CLI mode)')
    parser.add_argument('--oracle', help='Path to feature model .uvl (CLI mode)')
    parser.add_argument('--strategy', default='all',
                        choices=['all', 'description', 'clause', 'semantic'],
                        help='Comparison strategy (default: all)')
    parser.add_argument('-o', '--output-dir', help='Output directory override')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.config and args.config.endswith('.toml'):
        if not Path(args.config).exists():
            print(f"Error: Config not found: {args.config}")
            sys.exit(1)
        run_config_mode(args.config, args.verbose, args.output_dir)
    elif args.kb:
        if not args.bias or not args.oracle:
            print("Error: CLI mode requires --kb, --bias, and --oracle")
            sys.exit(1)
        run_cli_mode(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
