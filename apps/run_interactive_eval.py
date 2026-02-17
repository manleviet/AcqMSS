#!/usr/bin/env python
"""
Run interactive (QuAcq) constraint acquisition algorithm.

Usage:
    # Automated mode (Oracle answers using feature model)
    PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml

    # Interactive mode (human expert answers)
    PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml --interactive

    # With query limit
    PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml --max-queries 500
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from conacq.algorithms.interactive import (
    InteractiveLearner,
    InteractiveResult
)
from conacq.eval import (
    BiasData,
    load_folds,
    n_fold_cross_validation_interactive,
    generate_cv_report,
    save_cv_kb_files,
)
from conacq.examples import ExampleIO
from explanation.operations.algorithms.profiler import (
    use_global_profiler,
    ProfilerPreset
)


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    name: str
    oracle: str
    bias: str
    examples: str = None
    folds_path: str = None


def load_config(config_path: str) -> Dict[str, Any]:
    """Load TOML configuration file."""
    with open(config_path, 'rb') as f:
        return tomllib.load(f)


def parse_models(config: Dict) -> List[ModelConfig]:
    """Parse models list from config"""
    models_data = config.get('models', [])
    return [
        ModelConfig(
            name=m.get('name', Path(m['oracle']).stem),
            oracle=m['oracle'],
            bias=m['bias'],
            examples=m.get('examples'),
            folds_path=m.get('folds_path')
        )
        for m in models_data
    ]


def print_evaluation_results(model_name: str, evaluation: dict, verbose: bool = True) -> None:
    """Print evaluation results for both strategies.

    Args:
        model_name: Name of the model
        evaluation: Evaluation results dictionary with 'description' and 'clause' keys
        verbose: Enable verbose output
    """
    if not verbose:
        return

    print()
    print("=" * 60)
    print(f"Evaluation Results: {model_name}")
    print("=" * 60)

    # Description-based strategy
    desc = evaluation.get('description', {})
    desc_metrics = desc.get('metrics', {})
    print()
    print("--- Description-Based Strategy ---")
    print(f"  Accuracy:  {desc_metrics.get('accuracy', 0):.4f}")
    print(f"  Precision: {desc_metrics.get('precision', 0):.4f}")
    print(f"  Recall:    {desc_metrics.get('recall', 0):.4f}")
    print(f"  F1 Score:  {desc_metrics.get('f1_score', 0):.4f}")
    print(f"  TP: {desc_metrics.get('true_positives', 0)}  "
          f"FP: {desc_metrics.get('false_positives', 0)}  "
          f"FN: {desc_metrics.get('false_negatives', 0)}")

    # Clause-based strategy
    clause = evaluation.get('clause', {})
    clause_metrics = clause.get('metrics', {})
    print()
    print("--- Clause-Based Strategy ---")
    print(f"  Accuracy:  {clause_metrics.get('accuracy', 0):.4f}")
    print(f"  Precision: {clause_metrics.get('precision', 0):.4f}")
    print(f"  Recall:    {clause_metrics.get('recall', 0):.4f}")
    print(f"  F1 Score:  {clause_metrics.get('f1_score', 0):.4f}")
    print(f"  TP: {clause_metrics.get('true_positives', 0)}  "
          f"FP: {clause_metrics.get('false_positives', 0)}  "
          f"FN: {clause_metrics.get('false_negatives', 0)}  "
          f"TN: {clause_metrics.get('true_negatives', 0)}")


def process_model(model_config: ModelConfig, output_dir: Path,
                  max_queries: int, mode: str, verbose: bool,
                  solver_name: str = 'glucose4',
                  evaluate: bool = True,
                  interactive_config: Dict = None,
                  seed: int = None) -> InteractiveResult:
    """Process a single model with interactive learning.

    Args:
        model_config: Model configuration
        output_dir: Directory to save results
        max_queries: Maximum number of membership queries
        mode: 'automated' or 'interactive'
        verbose: Enable verbose output
        solver_name: SAT solver name
        evaluate: If True, evaluate the result against ground truth FM
        interactive_config: Interactive config section from TOML
        seed: Random seed for CV reproducibility

    Returns:
        InteractiveResult from learning
    """
    if interactive_config is None:
        interactive_config = {}
    try:
        model_name = model_config.name

        if verbose:
            print(f"\nProcessing: {model_name}")
            print(f"  FM: {model_config.oracle}")
            print(f"  Bias: {model_config.bias}")
            if model_config.examples:
                print(f"  Examples: {model_config.examples}")
            if model_config.folds_path:
                print(f"  Folds: {model_config.folds_path}")
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
                for c in result.kb_constraints[:10]:  # Show first 10
                    print(f"      - {c}")
                if len(result.kb_constraints) > 10:
                    print(f"      ... and {len(result.kb_constraints) - 10} more")

        # Evaluate the result
        if evaluate:
            try:
                evaluation = learner.evaluate(result)
                print_evaluation_results(model_name, evaluation, verbose)
            except Exception as eval_err:
                if verbose:
                    print(f"\n  Warning: Evaluation failed: {eval_err}")

        # Save result (including evaluation if available)
        output_file = output_dir / f"{model_name}_interactive_kb.json"
        result.save(str(output_file))

        if verbose:
            print(f"\n  Saved: {output_file}")

        # Cross-validation (if n_folds > 0 and examples provided)
        n_folds = interactive_config.get('n_folds', 0)
        if n_folds > 0 and model_config.examples:
            if verbose:
                print(f"\n  --- Cross-Validation ({n_folds} folds) ---")

            examples = ExampleIO.load_json(model_config.examples)
            bias = BiasData.from_json(Path(model_config.bias))

            # Load pre-generated folds (per-model)
            fold_data = None
            shuffle_bias = interactive_config.get('shuffle_bias', False)
            if model_config.folds_path:
                if Path(model_config.folds_path).exists():
                    fold_data = load_folds(model_config.folds_path)
                    n_folds = fold_data.n_folds
                    if verbose:
                        print(f"  Using pre-generated folds: {model_config.folds_path} ({n_folds} folds)")
                else:
                    print(f"  WARNING: folds_path not found: {model_config.folds_path}")

            query_mode = interactive_config.get('query_mode', 'example_only')

            cv_result = n_fold_cross_validation_interactive(
                positive_examples=[e.assignments for e in examples.positive],
                negative_examples=[e.assignments for e in examples.negative],
                n_folds=n_folds,
                bias_clauses={cid: c.clauses for cid, c in bias.constraints.items()},
                feature_ids=bias.features,
                fm_path=model_config.oracle,
                bias_path=model_config.bias,
                seed=seed,
                solver_name=solver_name,
                max_queries=max_queries,
                query_mode=query_mode,
                fold_data=fold_data,
                shuffle_bias=shuffle_bias
            )

            cv_output_file = output_dir / f"{model_name}_interactive_cv.json"
            cv_report = generate_cv_report(cv_result, cv_output_file)
            print(cv_report)

            saved_kbs = save_cv_kb_files(cv_result, output_dir, model_name, "interactive")
            if verbose:
                print(f"  Saved {len(saved_kbs['fold_kbs'])} fold KB files")

        return result

    except Exception as e:
        print(f"Error processing {model_config.oracle}: {e}")
        import traceback
        traceback.print_exc()
        return InteractiveResult(
            kb_constraints=[],
            n_queries=0,
            n_kb=0,
            convergence_reason=f'error: {str(e)}',
            runtime_ms=0
        )


def main():
    parser = argparse.ArgumentParser(
        description="Run interactive (QuAcq) constraint acquisition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    # Automated mode
    PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml -v

    # Interactive mode (human expert)
    PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml -v --interactive

    # With query limit
    PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml --max-queries 500
        """
    )
    parser.add_argument('config', help='Path to TOML configuration file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output (overrides config)')
    parser.add_argument('-o', '--output-dir', help='Output directory (overrides config)')
    parser.add_argument('--interactive', action='store_true',
                        help='Use interactive mode (human expert answers)')
    parser.add_argument('--max-queries', type=int, default=None,
                        help='Maximum number of queries (overrides config)')
    parser.add_argument('--solver', default='glucose4',
                        help='SAT solver name (default: glucose4)')
    parser.add_argument('--no-evaluate', action='store_true',
                        help='Skip evaluation against ground truth FM')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif args.verbose:
        logging.basicConfig(level=logging.INFO)

    if not Path(args.config).exists():
        print(f"Error: Config not found: {args.config}")
        sys.exit(1)

    config = load_config(args.config)

    # Parse settings
    general = config.get('general', {})
    interactive_config = config.get('interactive', {})

    output_dir = Path(args.output_dir or general.get('output_dir', 'data/results/interactive'))
    verbose = args.verbose or general.get('verbose', False)

    # Determine mode
    if args.interactive:
        mode = 'interactive'
    else:
        mode = interactive_config.get('mode', 'automated')

    # Determine max queries
    max_queries = args.max_queries or interactive_config.get('max_queries', 1000)

    # Seed
    seed = general.get('seed', 42)

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
    print(f"Evaluate: {not args.no_evaluate}")
    print(f"CV Folds: {interactive_config.get('n_folds', 0)}")
    print(f"Query mode: {interactive_config.get('query_mode', 'example_only')}")
    print(f"Shuffle bias: {interactive_config.get('shuffle_bias', False)}")

    results = []
    success_count = 0
    do_evaluate = not args.no_evaluate

    for model in models:
        result = process_model(
            model_config=model,
            output_dir=output_dir,
            max_queries=max_queries,
            mode=mode,
            verbose=verbose,
            solver_name=args.solver,
            evaluate=do_evaluate,
            interactive_config=interactive_config,
            seed=seed
        )
        results.append((model, result))
        if result.n_kb > 0 or result.convergence_reason in ['empty_bias', 'no_query']:
            success_count += 1

    profiler.stop()

    # Print summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"{'Model':<30} {'Queries':>8} {'KB':>5} {'Reason':<15}")
    print("-" * 60)

    for model, result in results:
        print(f"{model.name:<30} {result.n_queries:>8} {result.n_kb:>5} {result.convergence_reason:<15}")

    print("-" * 60)
    print(f"Completed: {success_count}/{len(models)} models")
    print("=" * 60)

    # Print Table 12 style comparison if evaluation was performed
    if do_evaluate:
        print()
        print("=" * 100)
        print("Table 12 Comparison (QuAcq Results)")
        print("=" * 100)
        header = (f"{'Model':<20} {'Algorithm':<10} {'#Queries':>10} {'|KB|':>6} "
                  f"{'Acc(Desc)':>10} {'Acc(Clause)':>12} {'Runtime':>12}")
        print(header)
        print("-" * 100)

        for model, result in results:
            model_name = model.name
            if result.evaluation:
                desc_acc = result.evaluation.get('description', {}).get('metrics', {}).get('accuracy', 0)
                clause_acc = result.evaluation.get('clause', {}).get('metrics', {}).get('accuracy', 0)
                print(f"{model_name:<20} {'QuAcq':<10} {result.n_queries:>10} {result.n_kb:>6} "
                      f"{desc_acc:>10.4f} {clause_acc:>12.4f} {result.runtime_ms:>10.2f}ms")
            else:
                print(f"{model_name:<20} {'QuAcq':<10} {result.n_queries:>10} {result.n_kb:>6} "
                      f"{'N/A':>10} {'N/A':>12} {result.runtime_ms:>10.2f}ms")

        print("=" * 100)

    if verbose:
        profiler.print_summary()

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
