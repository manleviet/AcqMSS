#!/usr/bin/env python
"""
Run ConGen cross-validation against Oracle FM.

Usage:
    PYTHONPATH=. python apps/run_congen_eval.py apps/conf/run_congen_eval_config.toml

Features:
- Run n-fold cross-validation with ConGen
- Calculate accuracy against test examples
- Support both incremental and non-incremental solver modes
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from conacq.eval import (
    n_fold_cross_validation,
    generate_cv_report,
    save_cv_kb_files,
    load_folds,
    Evaluator,
    EvaluationStrategy,
    CrossValidationResult,
)
from conacq.eval.result_loader import ConGenResultData
from conacq.examples import ExampleIO


@dataclass
class ModelConfig:
    """Configuration for a single model evaluation."""
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
    """Parse models list from config."""
    models_data = config.get('models', [])
    return [
        ModelConfig(
            name=m.get('name', 'unknown'),
            oracle=m['oracle'],
            bias=m['bias'],
            examples=m.get('examples'),
            folds_path=m.get('folds_path')
        )
        for m in models_data
    ]


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


def get_strategies(strategy_config: str) -> List[EvaluationStrategy]:
    """Parse strategy config into list of EvaluationStrategy."""
    if strategy_config == 'all':
        return [EvaluationStrategy.DESCRIPTION, EvaluationStrategy.CLAUSE]
    elif strategy_config == 'description':
        return [EvaluationStrategy.DESCRIPTION]
    elif strategy_config == 'clause':
        return [EvaluationStrategy.CLAUSE]
    return [EvaluationStrategy.DESCRIPTION]


def evaluate_cv_with_strategy(
        cv_result: CrossValidationResult,
        strategies: List[EvaluationStrategy],
        oracle_path: str,
        bias_path: str,
) -> Tuple[List[Dict], Dict]:
    """Evaluate fold KBs + intersected KB with strategies.

    Returns: (fold_evaluations, intersected_evaluation)
    Each fold_evaluation is a dict mapping strategy name -> EvaluationResult.to_dict().
    """
    evaluator = Evaluator.from_files(Path(oracle_path), Path(bias_path))

    fold_evaluations = []
    for fold in cv_result.fold_results:
        fold_eval = {}
        result_data = ConGenResultData(
            kb_constraints=fold.kb_constraints,
            redundant_constraints=fold.redundant_constraints,
            n_bias=fold.n_bias,
            n_mss=fold.n_mss,
            n_kb=fold.n_kb,
            bg_clauses=[]
        )
        for strategy in strategies:
            eval_result = evaluator.evaluate(result_data, strategy)
            fold_eval[strategy.value] = eval_result.to_dict()
        fold_evaluations.append(fold_eval)

    # Evaluate intersected KB
    intersected_eval = {}
    if cv_result.intersected_kb:
        first_fold = cv_result.fold_results[0]
        intersected_data = ConGenResultData(
            kb_constraints=cv_result.intersected_kb,
            redundant_constraints=[],
            n_bias=first_fold.n_bias,
            n_mss=0,
            n_kb=len(cv_result.intersected_kb),
            bg_clauses=[]
        )
        for strategy in strategies:
            eval_result = evaluator.evaluate(intersected_data, strategy)
            intersected_eval[strategy.value] = eval_result.to_dict()

    return fold_evaluations, intersected_eval


def evaluate_model(
        model_config: ModelConfig,
        eval_config: Dict,
        output_dir: Path,
        verbose: bool,
        strategies: List[EvaluationStrategy] = None,
) -> bool:
    """
    Evaluate a single model via cross-validation.

    Args:
        model_config: Model configuration
        eval_config: Evaluation settings
        output_dir: Output directory for results
        verbose: Enable verbose output
        strategies: Evaluation strategies for KB comparison against oracle

    Returns:
        True if successful, False otherwise
    """
    try:
        model_name = model_config.name
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
            print(f"  Solver modes: {['incremental' if m else 'non-incremental' for m in solver_modes]}")
            if model_config.examples:
                print(f"  Examples: {model_config.examples}")
            if model_config.folds_path:
                print(f"  Folds: {model_config.folds_path}")
            print(f"  Solver: {solver_name}, Seed: {seed}, Shuffle bias: {shuffle_bias}")

        # Load examples
        examples = None
        if model_config.examples:
            examples = ExampleIO.load_json(model_config.examples)
            if verbose:
                print(f"  E+: {len(examples.positive)}, E-: {len(examples.negative)}")

        # Run cross-validation
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
                    bias_path=model_config.bias,
                    fm_path=model_config.oracle,
                    seed=seed,
                    solver_name=solver_name,
                    use_incremental=is_incremental,
                    fold_data=fold_data,
                    shuffle_bias=shuffle_bias
                )

                # Generate CV report (print only, don't save yet)
                cv_report = generate_cv_report(cv_result)
                print(cv_report)

                # Serialize CV result and inject strategy evaluation
                cv_dict = cv_result.to_dict()

                if strategies:
                    fold_evals, intersected_eval = evaluate_cv_with_strategy(
                        cv_result, strategies, model_config.oracle, model_config.bias
                    )
                    # Inject per-fold strategy evaluation
                    for i, fold_eval in enumerate(fold_evals):
                        cv_dict['folds'][i]['strategy_evaluation'] = fold_eval
                    # Add intersected evaluation at top level
                    cv_dict['intersected_evaluation'] = intersected_eval

                    # Print summary
                    print("\n  Strategy Evaluation:")
                    for strategy in strategies:
                        sname = strategy.value
                        if intersected_eval.get(sname):
                            m = intersected_eval[sname]['metrics']
                            print(f"    {sname}: P={m['precision']:.4f}, R={m['recall']:.4f}, F1={m['f1_score']:.4f}")

                # Save CV JSON with eval data
                output_file = output_dir / f"{model_name}_cv_{mode_name}.json"
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w') as f:
                    json.dump(cv_dict, f, indent=2)

                # Save KB files (fold KBs + intersected KB)
                saved_kbs = save_cv_kb_files(cv_result, output_dir, model_name, mode_name)
                print(f"  Saved {len(saved_kbs['fold_kbs'])} fold KB files")
                print(f"  Intersected KB: {len(cv_result.intersected_kb)} constraints")
                print(f"  -> {saved_kbs['intersected_kb']}")

                # Save intersected KB evaluation separately
                if strategies and intersected_eval:
                    intersected_eval_file = output_dir / f"{model_name}_intersected_eval_{mode_name}.json"
                    intersected_eval_data = {
                        'model': model_name,
                        'mode': mode_name,
                        'strategies': [s.value for s in strategies],
                        'intersected_kb': cv_result.intersected_kb,
                        'evaluation': intersected_eval,
                    }
                    with open(intersected_eval_file, 'w') as f:
                        json.dump(intersected_eval_data, f, indent=2)
                    print(f"  Intersected eval: {intersected_eval_file}")

        print(f"\nResults saved to {output_dir}")
        return True

    except Exception as e:
        print(f"Error evaluating {model_config.name}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run ConGen cross-validation evaluation",
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

    solver_modes = get_solver_modes(eval_config.get('solver_mode', 'all'))
    strategies = get_strategies(eval_config.get('strategy', 'all'))

    print("=" * 60)
    print("ConGen Evaluation")
    print("=" * 60)
    print(f"Config: {args.config}")
    print(f"Output: {output_dir}")
    print(f"Models: {len(models)}")
    print(f"Solver modes: {['incremental' if m else 'non-incremental' for m in solver_modes]}")
    print(f"Solver: {eval_config.get('solver_name', 'glucose4')}")
    print(f"CV Folds: {eval_config.get('n_folds', 0)}")
    print(f"Seed: {eval_config.get('seed', 42)}")
    print(f"Shuffle bias: {eval_config.get('shuffle_bias', False)}")
    print(f"Strategies: {[s.value for s in strategies]}")

    # Evaluate each model
    success_count = 0
    for model in models:
        if evaluate_model(model, eval_config, output_dir, verbose, strategies):
            success_count += 1

    print()
    print("=" * 60)
    print(f"Completed: {success_count}/{len(models)} models")
    print("=" * 60)

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
