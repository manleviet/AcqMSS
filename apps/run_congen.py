#!/usr/bin/env python
"""
Run CONGEN constraint acquisition algorithm.

Usage:
    PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml
    PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml --non-incremental
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

from acqmss.testcases import FeatureModelOracle, ExampleIO
from acqmss.bias import BiasIO
from acqmss.algorithms import (
    CONGEN,
    CONGENModel,
    IncrementalCONGENTaskPreparation,
    NonIncrementalCONGENTaskPreparation
)
from explanation.operations.algorithms.checker import (
    IncrementalPySATChecker,
    NonIncrementalPySATChecker
)
from explanation.operations.algorithms.profiler import get_global_profiler


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    path: str
    bias: str
    examples: str


def load_config(config_path: str) -> Dict[str, Any]:
    """Load TOML configuration file."""
    with open(config_path, 'rb') as f:
        return tomllib.load(f)


def parse_models(config: Dict) -> List[ModelConfig]:
    """Parse models list from config"""
    models_data = config.get('models', [])
    return [
        ModelConfig(
            path=m['path'],
            bias=m['bias'],
            examples=m['examples']
        )
        for m in models_data
    ]


def extract_sampling_type(examples_path: str) -> str:
    """Extract sampling type from examples file name.

    Examples:
        REAL-FM-7_rs_1n.json -> rs_1n
        REAL-FM-7_ff.json -> ff

    Args:
        examples_path: Path to examples file

    Returns:
        Sampling type string
    """
    examples_name = Path(examples_path).stem  # e.g., REAL-FM-7_rs_1n
    # Split by underscore and take everything after the first part (model name)
    parts = examples_name.split('_')
    if len(parts) > 1:
        return '_'.join(parts[1:])  # e.g., rs_1n or ff
    return 'unknown'


def process_model(model_config: ModelConfig, output_dir: Path,
                  seed: int, verbose: bool, is_incremental: bool = True,
                  solver_name: str = 'glucose4') -> bool:
    """Process a single model with CONGEN.

    Args:
        model_config: Model configuration
        output_dir: Directory to save results
        seed: Random seed (unused, for compatibility)
        verbose: Enable verbose output
        is_incremental: Use incremental solver mode
        solver_name: SAT solver name

    Returns:
        True if successful, False otherwise
    """
    checker = None
    try:
        # Load feature model for feature IDs
        oracle = FeatureModelOracle(model_config.path)
        model_name = Path(model_config.path).stem
        sampling_type = extract_sampling_type(model_config.examples)

        if verbose:
            print(f"\nProcessing: {model_name}")
            print(f"  FM: {model_config.path}")
            print(f"  Bias: {model_config.bias}")
            print(f"  Examples: {model_config.examples}")
            print(f"  Mode: {'incremental' if is_incremental else 'non-incremental'}")

        # Load bias and examples
        bias = BiasIO.load_from_json(model_config.bias)
        examples = ExampleIO.load_json(model_config.examples)

        if verbose:
            print(f"  Bias constraints: {len(bias.constraints)}")
            print(f"  E+: {len(examples.positive)}, E-: {len(examples.negative)}")

        # Convert bias to constraint dict
        bias_constraints = {}
        for c in bias.constraints:
            bias_constraints[c.id] = c.clauses

        # Convert examples to dict format
        positive_examples = [e.assignments for e in examples.positive]
        negative_examples = [e.assignments for e in examples.negative]

        # Extract root feature ID from oracle
        feature_ids = oracle.get_feature_ids()
        root_name = oracle.get_root_feature()
        root_feature_id = feature_ids.get(root_name)

        # Create CONGEN model
        congen_model = CONGENModel.from_bias_and_examples(
            bias_constraints=bias_constraints,
            positive_examples=positive_examples,
            negative_examples=negative_examples,
            feature_ids=feature_ids,
            root_feature_id=root_feature_id
        )

        # Prepare task based on mode
        profiler = get_global_profiler()

        if is_incremental:
            preparation = IncrementalCONGENTaskPreparation()
            output = preparation.prepare(congen_model)
            task = output.task

            # Create incremental checker with KB and assumptions
            checker = IncrementalPySATChecker(
                task.set_kb,
                task.assumptions,
                solver_name,
                profiler
            )
        else:
            preparation = NonIncrementalCONGENTaskPreparation()
            output = preparation.prepare(congen_model)
            task = output.task

            # NonIncrementalPySATChecker doesn't take KB - creates fresh solver per check
            checker = NonIncrementalPySATChecker(solver_name, profiler)

        # Run CONGEN
        congen = CONGEN(checker, profiler)
        result = congen.acquire(task)

        if verbose:
            print(f"  MSS size: {result.n_mss}")
            print(f"  Acquired KB: {result.n_kb} constraints")
            if result.kb_constraints:
                print(f"  Constraints:")
                for c in result.kb_constraints[:10]:  # Show first 10
                    print(f"    - {c}")
                if len(result.kb_constraints) > 10:
                    print(f"    ... and {len(result.kb_constraints) - 10} more")

        # Save result with sampling type in filename
        # Format: {model_name}_{sampling_type}_kb.json
        output_file = output_dir / f"{model_name}_{sampling_type}_kb.json"
        congen.save_result(str(output_file))

        if verbose:
            print(f"  Saved: {output_file}")

        return True

    except Exception as e:
        print(f"Error processing {model_config.path}: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if checker is not None:
            checker.cleanup()


def main():
    parser = argparse.ArgumentParser(
        description="Run CONGEN constraint acquisition",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v
    PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v --non-incremental
        """
    )
    parser.add_argument('config', help='Path to TOML configuration file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output (overrides config)')
    parser.add_argument('-o', '--output-dir', help='Output directory (overrides config)')
    parser.add_argument('--non-incremental', action='store_true',
                        help='Use non-incremental solver mode')
    parser.add_argument('--solver', default='glucose4',
                        help='SAT solver name (default: glucose4)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if not Path(args.config).exists():
        print(f"Error: Config not found: {args.config}")
        sys.exit(1)

    config = load_config(args.config)

    # Parse settings
    general = config.get('general', {})
    seed = general.get('seed', 42)
    output_dir = Path(args.output_dir or general.get('output_dir', 'data/results'))
    verbose = args.verbose or general.get('verbose', False)

    models = parse_models(config)

    if not models:
        print("Error: No models specified in configuration")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    is_incremental = not args.non_incremental
    mode_str = "incremental" if is_incremental else "non-incremental"

    print("=" * 60)
    print("CONGEN Constraint Acquisition")
    print("=" * 60)
    print(f"Config: {args.config}")
    print(f"Output: {output_dir}")
    print(f"Models: {len(models)}")
    print(f"Mode: {mode_str}")
    print(f"Solver: {args.solver}")

    success_count = 0
    for model in models:
        if process_model(model, output_dir, seed, verbose,
                         is_incremental=is_incremental, solver_name=args.solver):
            success_count += 1

    print()
    print("=" * 60)
    print(f"Completed: {success_count}/{len(models)} models")
    print("=" * 60)

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
