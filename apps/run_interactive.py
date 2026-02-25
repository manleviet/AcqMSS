#!/usr/bin/env python
"""
Run interactive (QuAcq) constraint acquisition — pure learning only.

No evaluation, no CV, no enrichment. Use run_cv.py for CV
and run_compare.py for evaluation.

Usage:
    python -m apps.run_interactive apps/conf/run_interactive_config.toml -v
    python -m apps.run_interactive apps/conf/run_interactive_config.toml --interactive
"""

import argparse
import logging
import sys
from pathlib import Path

from conacq.algorithms.interactive import InteractiveLearner
from conacq.eval.config import load_pipeline_config, parse_models
from conacq.eval.report import save_kb_result
from explanation.operations.algorithms.profiler import (
    use_global_profiler,
    ProfilerPreset
)


def process_model(model_config, output_dir: Path, max_queries: int,
                  mode: str, verbose: bool, solver_name: str = 'glucose4'):
    """Process a single model with interactive learning.

    Returns:
        InteractiveResult from learning, or None on error
    """
    try:
        model_name = model_config.name

        if verbose:
            print(f"\nProcessing: {model_name}")
            print(f"  FM: {model_config.oracle}")
            print(f"  Bias: {model_config.bias}")
            print(f"  Mode: {mode}")
            print(f"  Max queries: {max_queries}")

        # Create learner
        learner = InteractiveLearner.from_files(
            fm_path=model_config.oracle,
            bias_path=model_config.bias,
            solver_name=solver_name,
            enable_profiling=True
        )

        if verbose:
            print(f"  Bias constraints: {len(learner.task.bias)}")
            print(f"  Features: {len(learner.task.feature_ids)}")
            print()
            print("  Starting interactive learning...")

        # Run learning
        result = learner.learn(mode=mode, max_queries=max_queries)

        if verbose:
            print(f"\n  Results:")
            print(f"    Queries asked: {result.n_queries}")
            print(f"    KB size: {result.n_kb}")
            print(f"    Convergence: {result.convergence_reason}")
            print(f"    Runtime: {result.runtime_ms:.2f} ms")
            if result.kb_constraints:
                print(f"    Constraints:")
                for c in result.kb_constraints[:10]:
                    print(f"      - {c}")
                if len(result.kb_constraints) > 10:
                    print(f"      ... and {len(result.kb_constraints) - 10} more")

        # Save KB result (unified format with bg_clauses)
        output_file = output_dir / f"{model_name}_interactive_kb.json"
        # bg_clauses from task background (root feature literal as unit clause)
        bg_clauses = [[lit] for lit in learner.task.background] if learner.task.background else []
        save_kb_result(
            kb_constraints=result.kb_constraints,
            redundant_constraints=getattr(result, 'redundant_constraints', []),
            n_bias=getattr(result, 'n_bias', 0),
            n_mss=0,
            n_kb=result.n_kb,
            output_path=output_file,
            bg_clauses=bg_clauses,
            metadata={'n_queries': result.n_queries,
                      'convergence_reason': result.convergence_reason,
                      'runtime_ms': result.runtime_ms}
        )

        if verbose:
            print(f"\n  Saved: {output_file}")

        return result

    except Exception as e:
        print(f"Error processing {model_config.oracle}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Run interactive (QuAcq) constraint acquisition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python -m apps.run_interactive apps/conf/run_interactive_config.toml -v
    python -m apps.run_interactive apps/conf/run_interactive_config.toml --interactive
        """
    )
    parser.add_argument('config', help='Path to TOML configuration file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-o', '--output-dir', help='Output directory (overrides config)')
    parser.add_argument('--interactive', action='store_true',
                        help='Use interactive mode (human expert answers)')
    parser.add_argument('--max-queries', type=int, default=None,
                        help='Maximum number of queries (overrides config)')
    parser.add_argument('--solver', default='glucose4', help='SAT solver name')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if not Path(args.config).exists():
        print(f"Error: Config not found: {args.config}")
        sys.exit(1)

    config = load_pipeline_config(args.config)

    # Parse settings
    general = config.get('general', {})
    interactive_config = config.get('interactive', {})

    output_dir = Path(args.output_dir or general.get('output_dir', 'data/results/interactive'))
    verbose = args.verbose or general.get('verbose', False)

    mode = 'interactive' if args.interactive else interactive_config.get('mode', 'automated')
    max_queries = args.max_queries or interactive_config.get('max_queries', 1000)

    models = parse_models(config)
    if not models:
        print("Error: No models specified in configuration")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup profiler
    profiler = use_global_profiler(ProfilerPreset.BENCHMARK)
    profiler.start()

    print("=" * 60)
    print("Interactive (QuAcq) Constraint Acquisition")
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

    profiler.stop()

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

    if verbose:
        profiler.print_summary()

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
