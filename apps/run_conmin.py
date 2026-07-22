#!/usr/bin/env python
"""
Run ConMin constraint acquisition — just for testing

No evaluation, no CV, no enrichment. Use run_cv.py for CV
and run_compare.py for evaluation.

Usage:
    python -m apps.run_conmin apps/conf/run_conmin_config.toml
    python -m apps.run_conmin apps/conf/run_conmin_config.toml --non-incremental --k 2
"""

import argparse
import logging
import sys
from pathlib import Path

from conacq.runners import ConMinRunner
from conacq.examples import ExampleIO
from conacq.eval.report import save_kb_result
from conacq.config import ModelConfig, load_pipeline_config, parse_models
from apps._harness import build_parser, setup_logging
from apps.run_congen import extract_sampling_type

logger = logging.getLogger(__name__)


def process_model(model_config: ModelConfig, output_dir: Path,
                  use_incremental: bool = True,
                  solver_name: str = 'glucose4',
                  k: int = 1) -> bool:
    """Process a single model with ConMin via ConMinRunner.

    Args:
        model_config: Model configuration
        output_dir: Directory to save results
        use_incremental: Use incremental solver mode
        solver_name: SAT solver name
        k: support⁺ threshold (Algorithm 1 line 6)

    Returns:
        True if successful, False otherwise
    """
    runner = None
    try:
        model_name = model_config.name
        sampling_type = extract_sampling_type(model_config.examples)

        logger.debug("Processing: %s", model_name)
        logger.debug("  FM: %s", model_config.oracle)
        logger.debug("  Bias: %s", model_config.bias)
        logger.debug("  Examples: %s", model_config.examples)
        logger.debug("  Mode: %s",
                     'incremental' if use_incremental else 'non-incremental')
        logger.debug("  k: %d", k)

        # Load examples
        examples = ExampleIO.load_json(model_config.examples)
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]

        # Run ConMin via runner
        runner = ConMinRunner(model_config.bias, model_config.oracle,
                              solver_name, use_incremental, k=k)
        result = runner.run(pos, neg)

        logger.debug("  Bias constraints: %d", result.n_bias)
        logger.debug("  E+: %d, E-: %d", len(pos), len(neg))
        logger.debug("  MSS size: %d", result.n_mss)
        logger.debug("  Acquired KB: %d constraints (fallbacks: %d, |U|: %d)",
                     result.n_kb, len(result.fallback_clauses), result.n_uncoverable)
        if result.kb_constraints:
            logger.debug("  Constraints:")
            for c in result.kb_constraints[:10]:
                logger.debug("    - %s", c)
            if len(result.kb_constraints) > 10:
                logger.debug("    ... and %d more", len(result.kb_constraints) - 10)

        # Save result in the standard KB format (compatible with
        # ConGenResultData.from_json / run_compare / extract_results); the ConMin
        # 5-part decomposition rides under `metadata.conmin` (non-breaking) for P4d.
        output_file = output_dir / f"{model_name}_{sampling_type}_kb.json"
        save_kb_result(
            kb_constraints=result.kb_constraints,
            redundant_constraints=result.redundant_constraints,
            n_bias=result.n_bias,
            n_mss=result.n_mss,
            n_kb=result.n_kb,
            output_path=output_file,
            bg_clauses=result.bg_clauses,
            metadata={
                'algorithm': 'conmin',
                'k': k,
                'conmin': {
                    'kb_clauses': result.kb_clauses,
                    'fallback_clauses': result.fallback_clauses,
                    'slices': {
                        'mss_ids': result.mss_ids,
                        'cover_ids': result.cover_ids,
                        'kb_assumption_ids': result.kb_assumption_ids,
                    },
                    'cover': {
                        'n_components': result.n_components,
                        'largest_component': result.largest_component,
                        'n_greedy_fallback': result.n_greedy_fallback,
                        'n_uncoverable': result.n_uncoverable,
                    },
                },
            },
        )

        logger.debug("  Saved: %s", output_file)

        return True

    except Exception:
        logger.exception("Error processing %s", model_config.oracle)
        return False

    finally:
        if runner is not None:
            runner.cleanup()


def main():
    parser = build_parser(
        "Run ConMin constraint acquisition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        verbose_help="Verbose output (overrides config)",
        epilog="""
Example:
    python -m apps.run_conmin apps/conf/run_conmin_config.toml -v
    python -m apps.run_conmin apps/conf/run_conmin_config.toml -v --non-incremental --k 2
        """
    )
    parser.add_argument('-o', '--output-dir', help='Output directory (overrides config)')
    parser.add_argument('--non-incremental', action='store_true',
                        help='Use non-incremental solver mode')
    parser.add_argument('--solver', default='glucose4',
                        help='SAT solver name (default: glucose4)')
    parser.add_argument('--k', type=int, default=None,
                        help='support+ threshold for the S set (overrides config; '
                             'default from [conmin] k, else 1)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()

    if not Path(args.config).exists():
        logger.error("Config not found: %s", args.config)
        sys.exit(1)

    config = load_pipeline_config(args.config)

    # Parse settings
    general = config.get('general', {})
    setup_logging(verbose=args.verbose or general.get('verbose', False),
                  debug=args.debug)
    output_dir = Path(args.output_dir or general.get('output_dir', 'data/results'))
    # k: --k overrides the [conmin] k config block (mirror run_cv), default 1.
    k = args.k if args.k is not None else config.get('conmin', {}).get('k', 1)

    models = parse_models(config)

    if not models:
        logger.error("No models specified in configuration")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    use_incremental = not args.non_incremental
    mode_str = "incremental" if use_incremental else "non-incremental"

    logger.info("=" * 60)
    logger.info("ConMin Constraint Acquisition")
    logger.info("=" * 60)
    logger.info("Config: %s", args.config)
    logger.info("Output: %s", output_dir)
    logger.info("Models: %d", len(models))
    logger.info("Mode: %s", mode_str)
    logger.info("Solver: %s", args.solver)
    logger.info("k: %d", k)

    success_count = 0
    for model in models:
        if process_model(model, output_dir,
                         use_incremental=use_incremental,
                         solver_name=args.solver, k=k):
            success_count += 1

    logger.info("=" * 60)
    logger.info("Completed: %d/%d models", success_count, len(models))
    logger.info("=" * 60)

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
