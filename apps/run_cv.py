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
from apps._harness import build_parser, setup_logging

from conacq.eval import (
    n_fold_cross_validation,
    n_fold_cross_validation_conmin,
    n_fold_cross_validation_interactive,
    generate_cv_report,
    generate_unified_cv_dict,
    load_folds,
)
from conacq.config import load_pipeline_config, parse_models
from conacq.examples import ExampleIO
from conacq.bias import BiasIO

logger = logging.getLogger(__name__)


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
    parser = build_parser(
        "Unified n-fold cross-validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python -m apps.run_cv apps/conf/run_cv_config.toml -v
        """
    )
    parser.add_argument('-o', '--output-dir', help='Output directory (overrides config)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if not Path(args.config).exists():
        logger.error("Config not found: %s", args.config)
        sys.exit(1)

    config = load_pipeline_config(args.config)

    # Parse settings
    general = config.get('general', {})
    # Log level from the -v flag OR the config's `verbose`, now that config is
    # loaded (diagnostics go to stderr; the CV report stays on stdout).
    setup_logging(verbose=args.verbose or general.get('verbose', False), debug=args.debug)
    eval_config = config.get('evaluation', {})
    seed = general.get('seed', 42)
    algorithm = eval_config.get('algorithm', 'congen')
    base_dir = Path(args.output_dir or general.get('output_dir', 'data/results'))
    output_dir = base_dir / algorithm
    n_folds = eval_config.get('n_folds', 5)
    solver_name = eval_config.get('solver_name', 'glucose4')
    solver_modes = get_solver_modes(eval_config.get('solver_mode', 'all'))
    shuffle_bias = eval_config.get('shuffle_bias', False)

    # Interactive-specific settings
    interactive_config = eval_config.get('interactive', {})
    max_queries = interactive_config.get('max_queries', 1000)
    query_mode = interactive_config.get('query_mode', 'example_only')

    # ConMin-specific settings
    conmin_config = eval_config.get('conmin', {})
    conmin_k = conmin_config.get('k', 1)

    models = parse_models(config)
    if not models:
        logger.error("No models specified in configuration")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("Cross-Validation (%s)", algorithm.upper())
    logger.info("=" * 60)
    logger.info("Config: %s", args.config)
    logger.info("Output: %s", output_dir)
    logger.info("Algorithm: %s", algorithm)
    logger.info("Models: %d", len(models))
    logger.info("Folds: %d", n_folds)
    logger.info("Solver modes: %s", ['inc' if m else 'non-inc' for m in solver_modes])
    logger.info("Solver: %s", solver_name)
    logger.info("Shuffle bias: %s", shuffle_bias)
    if algorithm == 'interactive':
        logger.info("Max queries: %s", max_queries)
        logger.info("Query mode: %s", query_mode)

    success_count = 0

    for model_config in models:
        logger.info("%s", "=" * 60)
        logger.info("Model: %s", model_config.name)
        logger.info("%s", "=" * 60)

        try:
            # Load examples
            if not model_config.examples:
                logger.warning("No examples for %s, skipping", model_config.name)
                continue

            examples = ExampleIO.load_json(model_config.examples)
            pos = [e.assignments for e in examples.positive]
            neg = [e.assignments for e in examples.negative]

            logger.debug("  Oracle: %s", model_config.oracle)
            logger.debug("  Bias: %s", model_config.bias)
            logger.debug("  Examples: %s", model_config.examples)
            logger.debug("  E+: %d, E-: %d", len(pos), len(neg))

            # Load bias once per model (for description resolution and interactive)
            bias = BiasIO.load_from_json(model_config.bias)

            # Load pre-generated folds if available
            fold_data = None
            actual_n_folds = n_folds
            if model_config.folds_path and Path(model_config.folds_path).exists():
                fold_data = load_folds(model_config.folds_path)
                actual_n_folds = fold_data.n_folds
                logger.debug("  Folds: %s (%d folds)", model_config.folds_path, actual_n_folds)
            elif model_config.folds_path:
                logger.warning("folds_path not found: %s", model_config.folds_path)

            for is_incremental in solver_modes:
                mode_name = "incremental" if is_incremental else "non-incremental"
                logger.info("--- Mode: %s ---", mode_name.upper())

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
                elif algorithm == 'conmin':
                    cv_result = n_fold_cross_validation_conmin(
                        positive_examples=pos,
                        negative_examples=neg,
                        n_folds=actual_n_folds,
                        bias_path=model_config.bias,
                        fm_path=model_config.oracle,
                        seed=seed,
                        solver_name=solver_name,
                        use_incremental=is_incremental,
                        fold_data=fold_data,
                        shuffle_bias=shuffle_bias,
                        k=conmin_k
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
                    logger.error("Unknown algorithm: %s", algorithm)
                    continue

                # The CV report is this command's product — keep it on stdout.
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
                logger.info("  Unified CV: %s", cv_file)
                logger.info("  Intersected KB: %d constraints", len(cv_result.intersected_kb))

            success_count += 1

        except Exception:
            logger.exception("Error evaluating %s", model_config.name)

    logger.info("%s", "=" * 60)
    logger.info("Completed: %d/%d models", success_count, len(models))
    logger.info("%s", "=" * 60)

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
