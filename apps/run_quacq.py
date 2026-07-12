#!/usr/bin/env python
"""
Run QuAcq constraint acquisition — pure learning only.

No evaluation, no CV. Use run_cv.py for cross-validation
and run_evaluation.py for QuAcq->ConGen pipeline evaluation.

Usage:
    python -m apps.run_quacq apps/conf/run_quacq_config.toml -v
    python -m apps.run_quacq apps/conf/run_quacq_config.toml --interactive
"""

import argparse
import logging
import sys
from pathlib import Path

from conacq.runners import QuAcqRunner
from conacq.config import load_pipeline_config, parse_models
from apps._harness import build_parser, setup_logging
from conacq.eval.report import save_kb_result


def process_model(model_config, output_dir: Path, max_queries: int,
                  mode: str, verbose: bool, solver_name: str = 'glucose4'):
    """Process a single model with QuAcq learning.

    Supports all four modes:
    - 'automated': FM oracle answers queries automatically
    - 'interactive': human expert answers queries
    - 'example_only': learn purely from provided examples
    - 'example_first': use examples first, then oracle queries

    Returns:
        QuAcqRunResult from runner, or None on error
    """
    try:
        model_name = model_config.name

        # Create runner (loads bias internally)
        runner = QuAcqRunner(
            bias_path=model_config.bias,
            fm_path=model_config.oracle,
            solver_name=solver_name,
            max_queries=max_queries
        )

        if verbose:
            print(f"\nProcessing: {model_name}")
            print(f"  FM: {model_config.oracle}")
            print(f"  Bias: {model_config.bias}")
            print(f"  Mode: {mode}")
            print(f"  Max queries: {max_queries}")
            print(f"  Bias constraints: {len(runner.model.constraint_map)}")
            print(f"  Features: {len(runner.feature_ids)}")
            print()
            print("  Starting QuAcq learning...")

        # Mode dispatch: example modes require loading examples
        if mode in ('example_only', 'example_first'):
            if not model_config.examples:
                raise ValueError(
                    f"Mode '{mode}' requires 'examples' path in [[models]] config"
                )
            from conacq.examples import ExampleIO
            examples = ExampleIO.load_json(model_config.examples)
            pos = [e.assignments for e in examples.positive]
            neg = [e.assignments for e in examples.negative]
            run_result = runner.run(positive_examples=pos, negative_examples=neg, mode=mode)
        else:
            run_result = runner.run(mode=mode)

        if verbose:
            print(f"\n  Results:")
            print(f"    Queries asked: {run_result.n_queries}")
            print(f"    KB size: {run_result.n_kb}")
            print(f"    Convergence: {run_result.convergence_reason}")
            print(f"    Runtime: {run_result.runtime_ms:.2f} ms")
            if run_result.kb_constraints:
                print(f"    Constraints:")
                for c in run_result.kb_constraints[:10]:
                    print(f"      - {c}")
                if len(run_result.kb_constraints) > 10:
                    print(f"      ... and {len(run_result.kb_constraints) - 10} more")

        # Save KB result (unified format with bg_clauses)
        output_file = output_dir / f"{model_name}_quacq_kb.json"
        save_kb_result(
            kb_constraints=run_result.kb_constraints,
            redundant_constraints=[],
            n_bias=run_result.n_bias,
            n_mss=0,
            n_kb=run_result.n_kb,
            output_path=output_file,
            bg_clauses=run_result.bg_clauses,
            metadata={'n_queries': run_result.n_queries,
                      'convergence_reason': run_result.convergence_reason,
                      'runtime_ms': run_result.runtime_ms}
        )

        if verbose:
            print(f"\n  Saved: {output_file}")

        runner.cleanup()
        return run_result

    except Exception as e:
        print(f"Error processing {model_config.oracle}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = build_parser(
        "Run QuAcq constraint acquisition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python -m apps.run_quacq apps/conf/run_quacq_config.toml -v
    python -m apps.run_quacq apps/conf/run_quacq_config.toml --interactive

Modes: automated | interactive | example_only | example_first
        """
    )
    parser.add_argument('-o', '--output-dir', help='Output directory (overrides config)')
    parser.add_argument('--interactive', action='store_true',
                        help='Use interactive mode (human expert answers)')
    parser.add_argument('--max-queries', type=int, default=None,
                        help='Maximum number of queries (overrides config)')
    parser.add_argument('--solver', default='glucose4', help='SAT solver name')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    setup_logging(verbose=args.verbose, debug=args.debug)

    if not Path(args.config).exists():
        print(f"Error: Config not found: {args.config}")
        sys.exit(1)

    config = load_pipeline_config(args.config)

    # Parse settings from [quacq] section
    general = config.get('general', {})
    quacq_config = config.get('quacq', {})

    output_dir = Path(args.output_dir or general.get('output_dir', 'data/results/quacq'))
    verbose = args.verbose or general.get('verbose', False)

    mode = 'interactive' if args.interactive else quacq_config.get('mode', 'automated')
    max_queries = args.max_queries or quacq_config.get('max_queries', 1000)

    models = parse_models(config)
    if not models:
        print("Error: No models specified in configuration")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("QuAcq Constraint Acquisition")
    print("=" * 60)
    print(f"Config: {args.config}")
    print(f"Output: {output_dir}")
    print(f"Models: {len(models)}")
    print(f"Mode: {mode}")
    print(f"Max queries: {max_queries}")
    print(f"Solver: {args.solver}")

    results = []
    success_count = 0

    for model in models:
        result = process_model(model, output_dir, max_queries, mode,
                               verbose, args.solver)
        results.append((model, result))
        if result and (result.n_kb > 0 or result.convergence_reason in ['empty_bias', 'no_query']):
            success_count += 1

    # Print summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"{'Model':<30} {'Queries':>8} {'KB':>5} {'Reason':<15} {'Runtime':>10}")
    print("-" * 70)

    for model, result in results:
        if result:
            print(f"{model.name:<30} {result.n_queries:>8} {result.n_kb:>5} "
                  f"{result.convergence_reason:<15} {result.runtime_ms:>8.2f}ms")
        else:
            print(f"{model.name:<30} {'ERROR':>8}")

    print("-" * 70)
    print(f"Completed: {success_count}/{len(models)} models")
    print("=" * 60)

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
