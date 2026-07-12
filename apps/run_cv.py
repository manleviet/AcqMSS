#!/usr/bin/env python
"""
Unified n-fold cross-validation for ConGen and Interactive algorithms.

Runs CV, saves fold KBs + intersected KB. No comparison/enrichment
(use run_compare.py for that).

Usage:
    python -m apps.run_cv apps/conf/run_cv_config.toml -v
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List

from conacq.atomic_io import write_json_atomic

from conacq.eval import (
    n_fold_cross_validation,
    n_fold_cross_validation_interactive,
    generate_cv_report,
    generate_unified_cv_dict,
    load_folds,
)
from conacq.config import load_pipeline_config, parse_models
from conacq.examples import ExampleIO
from conacq.bias import BiasIO


def get_solver_modes(mode_config: str) -> List[bool]:
    """Get list of solver modes (is_incremental values)."""
    if mode_config == 'all':
        return [True, False]
    elif mode_config == 'incremental':
        return [True]
    elif mode_config == 'non-incremental':
        return [False]
    return [True]


def main():
    parser = argparse.ArgumentParser(
        description="Unified n-fold cross-validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python -m apps.run_cv apps/conf/run_cv_config.toml -v
        """
    )
    parser.add_argument('config', help='Path to TOML configuration file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-o', '--output-dir', help='Output directory (overrides config)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

    if not Path(args.config).exists():
        print(f"Error: Config not found: {args.config}")
        sys.exit(1)

    config = load_pipeline_config(args.config)

    # Parse settings
    general = config.get('general', {})
    eval_config = config.get('evaluation', {})
    seed = general.get('seed', 42)
    algorithm = eval_config.get('algorithm', 'congen')
    base_dir = Path(args.output_dir or general.get('output_dir', 'data/results'))
    output_dir = base_dir / algorithm
    verbose = args.verbose or general.get('verbose', False)
    n_folds = eval_config.get('n_folds', 5)
    solver_name = eval_config.get('solver_name', 'glucose4')
    solver_modes = get_solver_modes(eval_config.get('solver_mode', 'all'))
    shuffle_bias = eval_config.get('shuffle_bias', False)

    # Interactive-specific settings
    interactive_config = eval_config.get('interactive', {})
    max_queries = interactive_config.get('max_queries', 1000)
    query_mode = interactive_config.get('query_mode', 'example_only')

    models = parse_models(config)
    if not models:
        print("Error: No models specified in configuration")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"Cross-Validation ({algorithm.upper()})")
    print("=" * 60)
    print(f"Config: {args.config}")
    print(f"Output: {output_dir}")
    print(f"Algorithm: {algorithm}")
    print(f"Models: {len(models)}")
    print(f"Folds: {n_folds}")
    print(f"Solver modes: {['inc' if m else 'non-inc' for m in solver_modes]}")
    print(f"Solver: {solver_name}")
    print(f"Shuffle bias: {shuffle_bias}")
    if algorithm == 'interactive':
        print(f"Max queries: {max_queries}")
        print(f"Query mode: {query_mode}")

    success_count = 0

    for model_config in models:
        print(f"\n{'=' * 60}")
        print(f"Model: {model_config.name}")
        print(f"{'=' * 60}")

        try:
            # Load examples
            if not model_config.examples:
                print(f"  WARNING: No examples for {model_config.name}, skipping")
                continue

            examples = ExampleIO.load_json(model_config.examples)
            pos = [e.assignments for e in examples.positive]
            neg = [e.assignments for e in examples.negative]

            if verbose:
                print(f"  Oracle: {model_config.oracle}")
                print(f"  Bias: {model_config.bias}")
                print(f"  Examples: {model_config.examples}")
                print(f"  E+: {len(pos)}, E-: {len(neg)}")

            # Load bias once per model (for description resolution and interactive)
            bias = BiasIO.load_from_json(model_config.bias)

            # Load pre-generated folds if available
            fold_data = None
            actual_n_folds = n_folds
            if model_config.folds_path and Path(model_config.folds_path).exists():
                fold_data = load_folds(model_config.folds_path)
                actual_n_folds = fold_data.n_folds
                if verbose:
                    print(f"  Folds: {model_config.folds_path} ({actual_n_folds} folds)")
            elif model_config.folds_path:
                print(f"  WARNING: folds_path not found: {model_config.folds_path}")

            for is_incremental in solver_modes:
                mode_name = "incremental" if is_incremental else "non-incremental"
                print(f"\n--- Mode: {mode_name.upper()} ---")

                if algorithm == 'congen':
                    cv_result = n_fold_cross_validation(
                        positive_examples=pos,
                        negative_examples=neg,
                        n_folds=actual_n_folds,
                        bias_path=model_config.bias,
                        fm_path=model_config.oracle,
                        seed=seed,
                        solver_name=solver_name,
                        use_incremental=is_incremental,
                        fold_data=fold_data,
                        shuffle_bias=shuffle_bias
                    )
                elif algorithm == 'interactive':
                    cv_result = n_fold_cross_validation_interactive(
                        positive_examples=pos,
                        negative_examples=neg,
                        n_folds=actual_n_folds,
                        fm_path=model_config.oracle,
                        bias_path=model_config.bias,
                        seed=seed,
                        solver_name=solver_name,
                        max_queries=max_queries,
                        query_mode=query_mode,
                        use_incremental=is_incremental,
                        fold_data=fold_data,
                        shuffle_bias=shuffle_bias
                    )
                else:
                    print(f"  ERROR: Unknown algorithm: {algorithm}")
                    continue

                # Print CV report
                cv_report = generate_cv_report(cv_result)
                print(cv_report)

                # Save unified CV JSON (with descriptions and eval placeholders)
                unified = generate_unified_cv_dict(cv_result, bias)
                # Include query_mode in filename for interactive to avoid overwrites
                if algorithm == 'interactive':
                    cv_file = output_dir / f"{model_config.name}_cv_{mode_name}_{query_mode}.json"
                else:
                    cv_file = output_dir / f"{model_config.name}_cv_{mode_name}.json"
                write_json_atomic(cv_file, unified)
                print(f"  Unified CV: {cv_file}")
                print(f"  Intersected KB: {len(cv_result.intersected_kb)} constraints")

            success_count += 1

        except Exception as e:
            print(f"Error evaluating {model_config.name}: {e}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"Completed: {success_count}/{len(models)} models")
    print("=" * 60)

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
