#!/usr/bin/env python
"""
Evaluate CONGEN results against Oracle FM.

Usage:
    PYTHONPATH=. python apps/run_congen_eval.py apps/conf/run_congen_eval_config.toml

Features:
- Evaluate pre-computed CONGEN results (if result file provided)
- Run cross-validation with CONGEN (if n_folds > 0)
- Calculate accuracy against test examples
- Support both description-based and clause-based evaluation strategies
- Support both incremental and non-incremental solver modes
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

from acqmss.eval import (
    Evaluator,
    EvaluationStrategy,
    AccuracyCalculator,
    BiasData,
    CONGENResultData,
    n_fold_cross_validation,
    generate_evaluation_report,
    generate_accuracy_report,
    generate_cv_report,
    save_cv_kb_files,
    load_folds,
)
from acqmss.testcases import FeatureModelOracle, ExampleIO


@dataclass
class ModelConfig:
    """Configuration for a single model evaluation."""
    name: str
    oracle: str
    bias: str
    result: str = None  # TODO: necessary?
    examples: str = None
    folds_path: str = None


def load_config(config_path: str) -> Dict[str, Any]:
    """Load TOML configuration file."""
    with open(config_path, 'rb') as f:
        return tomllib.load(f)


def parse_models(config: Dict) -> List[ModelConfig]:
    """Parse models list from config."""
    models_data = config.get('models', [])
    return [
        ModelConfig(
            name=m.get('name', 'unknown'),
            oracle=m['oracle'],
            bias=m['bias'],
            result=m.get('result'),  # TODO: necessary?
            examples=m.get('examples'),
            folds_path=m.get('folds_path')
        )
        for m in models_data
    ]


def get_strategies(strategy_config: str) -> List[EvaluationStrategy]:
    """Get list of strategies to run."""
    if strategy_config == 'all':
        return [EvaluationStrategy.DESCRIPTION, EvaluationStrategy.CLAUSE]
    elif strategy_config == 'description':
        return [EvaluationStrategy.DESCRIPTION]
    elif strategy_config == 'clause':
        return [EvaluationStrategy.CLAUSE]
    else:
        return [EvaluationStrategy.DESCRIPTION]


def get_solver_modes(mode_config: str) -> List[bool]:
    """Get list of solver modes (is_incremental values)."""
    if mode_config == 'all':
        return [True, False]  # incremental, non-incremental
    elif mode_config == 'incremental':
        return [True]
    elif mode_config == 'non-incremental':
        return [False]
    else:
        return [True]


def evaluate_model(
        model_config: ModelConfig,
        eval_config: Dict,
        output_dir: Path,
        verbose: bool
) -> bool:
    """
    Evaluate a single model.

    Args:
        model_config: Model configuration
        eval_config: Evaluation settings
        output_dir: Output directory for results
        verbose: Enable verbose output

    Returns:
        True if successful, False otherwise
    """
    try:
        model_name = model_config.name
        strategies = get_strategies(eval_config.get('strategy', 'all'))
        solver_modes = get_solver_modes(eval_config.get('solver_mode', 'all'))
        n_folds = eval_config.get('n_folds', 0)
        solver_name = eval_config.get('solver_name', 'glucose4')
        seed = eval_config.get('seed', 42)
        shuffle_bias = eval_config.get('shuffle_bias', False)

        print(f"\n{'=' * 60}")
        print(f"Evaluating: {model_name}")
        print(f"{'=' * 60}")

        if verbose:
            print(f"  Oracle: {model_config.oracle}")
            print(f"  Bias: {model_config.bias}")
            print(f"  Strategies: {[s.value for s in strategies]}")
            print(f"  Solver modes: {['incremental' if m else 'non-incremental' for m in solver_modes]}")
            if model_config.result:
                print(f"  Result: {model_config.result}")
            if model_config.examples:
                print(f"  Examples: {model_config.examples}")
            if model_config.folds_path:
                print(f"  Folds: {model_config.folds_path}")
            print(f"  Solver: {solver_name}, Seed: {seed}, Shuffle bias: {shuffle_bias}")

        # Load bias data
        bias = BiasData.from_json(Path(model_config.bias))
        bias_clauses = {cid: c.clauses for cid, c in bias.constraints.items()}

        # Extract root feature for background knowledge
        oracle = FeatureModelOracle(model_config.oracle)
        root_name = oracle.get_root_feature()
        root_id = oracle.get_feature_ids().get(root_name)
        background_knowledge = [root_id] if root_id is not None else []

        # Load examples if provided
        examples = None
        if model_config.examples:
            examples = ExampleIO.load_json(model_config.examples)
            if verbose:
                print(f"  E+: {len(examples.positive)}, E-: {len(examples.negative)}")

        # ============================================================
        # Option 1: Evaluate pre-computed result (both strategies)
        # ============================================================
        if model_config.result:
            print("\n" + "=" * 50)
            print("Evaluating Pre-computed Result")
            print("=" * 50)

            # Create evaluator
            evaluator = Evaluator.from_files(
                Path(model_config.oracle),
                Path(model_config.bias)
            )

            # Load result
            result = CONGENResultData.from_json(Path(model_config.result))

            # Evaluate with each strategy
            for strategy in strategies:
                print(f"\n--- Strategy: {strategy.value.upper()} ---")

                eval_result = evaluator.evaluate(result, strategy=strategy)

                # Generate and print report
                output_file = output_dir / f"{model_name}_eval_{strategy.value}.json"
                report = generate_evaluation_report(eval_result, output_file)
                print(report)

            # Calculate accuracy if examples provided
            if examples:
                print("\n--- Accuracy Against Examples ---")

                # Build KB clauses from result
                kb_clauses = []
                for cid in result.kb_constraints:
                    if cid in bias_clauses:
                        kb_clauses.extend(bias_clauses[cid])

                with AccuracyCalculator(kb_clauses, solver_name) as calculator:
                    pos_assignments = [e.assignments for e in examples.positive]
                    neg_assignments = [e.assignments for e in examples.negative]
                    accuracy_result = calculator.calculate(
                        pos_assignments,
                        neg_assignments,
                        bias.features
                    )

                acc_report = generate_accuracy_report(
                    accuracy_result,
                    output_dir / f"{model_name}_accuracy.json"
                )
                print(acc_report)

        # ============================================================
        # Option 2: Run cross-validation (both modes)
        # ============================================================
        if n_folds > 0 and examples:
            print("\n" + "=" * 50)
            print(f"{n_folds}-Fold Cross-Validation")
            print("=" * 50)

            pos_assignments = [e.assignments for e in examples.positive]
            neg_assignments = [e.assignments for e in examples.negative]

            # Load pre-generated folds if path provided (per-model)
            fold_data = None
            if model_config.folds_path:
                if Path(model_config.folds_path).exists():
                    fold_data = load_folds(model_config.folds_path)
                    n_folds = fold_data.n_folds  # override n_folds from fold file
                    print(f"  Using pre-generated folds: {model_config.folds_path} ({n_folds} folds)")
                else:
                    print(f"  WARNING: folds_path not found: {model_config.folds_path}, using on-the-fly generation")

            for is_incremental in solver_modes:
                mode_name = "incremental" if is_incremental else "non-incremental"
                print(f"\n--- Mode: {mode_name.upper()} ---")

                cv_result = n_fold_cross_validation(
                    positive_examples=pos_assignments,
                    negative_examples=neg_assignments,
                    n_folds=n_folds,
                    bias_clauses=bias_clauses,
                    feature_ids=bias.features,
                    seed=seed,
                    solver_name=solver_name,
                    is_incremental=is_incremental,
                    fold_data=fold_data,
                    shuffle_bias=shuffle_bias,
                    background_knowledge=background_knowledge
                )

                output_file = output_dir / f"{model_name}_cv_{mode_name}.json"
                cv_report = generate_cv_report(cv_result, output_file)
                print(cv_report)

                # Save KB files (fold KBs + intersected KB)
                saved_kbs = save_cv_kb_files(cv_result, output_dir, model_name, mode_name)
                print(f"  Saved {len(saved_kbs['fold_kbs'])} fold KB files")
                print(f"  Intersected KB: {len(cv_result.intersected_kb)} constraints")
                print(f"  -> {saved_kbs['intersected_kb']}")

        print(f"\nResults saved to {output_dir}")
        return True

    except Exception as e:
        print(f"Error evaluating {model_config.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate CONGEN constraint acquisition results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    PYTHONPATH=. python apps/run_congen_eval.py apps/conf/run_congen_eval_config.toml
    PYTHONPATH=. python apps/run_congen_eval.py apps/conf/run_congen_eval_config.toml -v --debug
        """
    )
    parser.add_argument('config', help='Path to TOML configuration file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output')
    parser.add_argument('-o', '--output-dir', help='Output directory (overrides config)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )

    # Check config exists
    if not Path(args.config).exists():
        print(f"Error: Config not found: {args.config}")
        sys.exit(1)

    # Load configuration
    config = load_config(args.config)

    # Parse settings
    general = config.get('general', {})
    eval_config = config.get('evaluation', {})
    eval_config['seed'] = general.get('seed', 42)

    output_dir = Path(args.output_dir or general.get('output_dir', 'data/results'))
    verbose = args.verbose or general.get('verbose', False)

    models = parse_models(config)

    if not models:
        print("Error: No models specified in configuration")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get configured strategies and modes
    strategies = get_strategies(eval_config.get('strategy', 'all'))
    solver_modes = get_solver_modes(eval_config.get('solver_mode', 'all'))

    print("=" * 60)
    print("CONGEN Evaluation")
    print("=" * 60)
    print(f"Config: {args.config}")
    print(f"Output: {output_dir}")
    print(f"Models: {len(models)}")
    print(f"Strategies: {[s.value for s in strategies]}")
    print(f"Solver modes: {['incremental' if m else 'non-incremental' for m in solver_modes]}")
    print(f"Solver: {eval_config.get('solver_name', 'glucose4')}")
    print(f"CV Folds: {eval_config.get('n_folds', 0)}")
    print(f"Seed: {eval_config.get('seed', 42)}")
    print(f"Shuffle bias: {eval_config.get('shuffle_bias', False)}")

    # Evaluate each model
    success_count = 0
    for model in models:
        if evaluate_model(model, eval_config, output_dir, verbose):
            success_count += 1

    print()
    print("=" * 60)
    print(f"Completed: {success_count}/{len(models)} models")
    print("=" * 60)

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
