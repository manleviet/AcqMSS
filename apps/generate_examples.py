#!/usr/bin/env python
"""
Generate test case examples from feature models.

Sampling methods (from AcqMSS paper):
- Random Sampling (RS): n, 2n, 3n, m examples (n = number of features, m = 2-COV count)
- 2-wise Coverage (2-COV): each pair of features covered
- Feature Frequency (FF): each feature appears True/False in E+/E-

Usage:
    python -m apps.generate_examples apps/conf/generate_examples_config.toml
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from conacq.oracle import FeatureModelOracle
from conacq.examples import (
    BalancedRandomSamplingGenerator,
    ControlledRandomSamplingGenerator,
    FeatureFrequencyGenerator,
    TwoCoverageGenerator,
    ExampleIO,
    ExampleSet,
)


def load_config(config_path: str) -> Dict[str, Any]:
    """Load TOML configuration file."""
    with open(config_path, 'rb') as f:
        return tomllib.load(f)


# Strategy -> example count function(n_features, m_value)
STRATEGY_COUNTS = {
    'rs_1n': lambda n, m: n,
    'rs_2n': lambda n, m: 2 * n,
    'rs_3n': lambda n, m: 3 * n,
    'rs_m': lambda n, m: m,
    '2cov': lambda n, m: None,
    'ff': lambda n, m: 10 * n,
    'balanced': lambda n, m: 2 * n,
}


def get_example_count_for_strategy(strategy: str, n_features: int, m_value: Optional[int] = None) -> Optional[int]:
    """
    Get number of examples based on strategy and feature count.

    Paper strategies: rs_1n=n, rs_2n=2n, rs_3n=3n, rs_m=m (2-COV count),
    2cov=coverage-based (None), ff=10n, balanced=2n.
    """
    if strategy not in STRATEGY_COUNTS:
        raise ValueError(f"Unknown strategy: {strategy}")
    return STRATEGY_COUNTS[strategy](n_features, m_value)


def generate_examples_for_strategy(
        oracle: FeatureModelOracle,
        strategy: str,
        n_examples: Optional[int],
        n_features: int,
        seed: int,
        valid_configs: int = None
) -> ExampleSet:
    """
    Generate examples using specified strategy.

    Args:
        oracle: Feature model oracle
        strategy: Strategy name (rs_1n, rs_2n, rs_3n, rs_m, 2cov, ff, balanced)
        n_examples: Pre-computed example count (None for coverage-based)
        n_features: Number of features
        seed: Random seed
        valid_configs: Pre-computed valid configurations count (for E+/E- distribution)

    Returns:
        Generated ExampleSet
    """
    if strategy in ('rs_1n', 'rs_2n', 'rs_3n', 'rs_m'):
        gen = ControlledRandomSamplingGenerator(oracle)
        examples = gen.generate(total=n_examples, valid_configs=valid_configs, seed=seed)
        examples.metadata['target_total'] = n_examples
    elif strategy == '2cov':
        gen = TwoCoverageGenerator(oracle)
        examples = gen.generate(seed=seed)
    elif strategy == 'ff':
        gen = FeatureFrequencyGenerator(oracle)
        examples = gen.generate(max_examples=n_examples, seed=seed)
        examples.metadata['max_examples'] = n_examples
    elif strategy == 'balanced':
        gen = BalancedRandomSamplingGenerator(oracle)
        n_each = n_features
        examples = gen.generate(n_positive=n_each, n_negative=n_each, seed=seed)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    examples.metadata['strategy'] = strategy
    return examples


def process_model(
        model_config: Dict[str, Any],
        default_strategies: List[str],
        output_dir: Path,
        seed: int,
        verbose: bool
) -> bool:
    """
    Process a single feature model.

    Args:
        model_config: Model configuration dict from TOML
        default_strategies: Default strategies to use
        output_dir: Output directory
        seed: Random seed
        verbose: Verbose output

    Returns:
        True if successful
    """
    fm_path = model_config['path']

    if not Path(fm_path).exists():
        print(f"Error: Feature model not found: {fm_path}")
        return False

    model_name = Path(fm_path).stem

    try:
        # Load feature model
        if verbose:
            print(f"\nLoading: {fm_path}")

        oracle = FeatureModelOracle(fm_path)
        n_features = len(oracle.get_variables())

        # Use pre-computed values from config if available
        valid_configs = model_config.get('valid_configs')
        m_value = model_config.get('m')

        # Determine strategies
        strategies = model_config.get('strategies') or default_strategies

        if verbose:
            print(f"  Features: {n_features}")
            if valid_configs:
                print(f"  Valid configs: {valid_configs}")
            print(f"  Strategies: {strategies}")

        # Compute m value (2-COV count) if rs_m strategy is used and not provided
        if 'rs_m' in strategies and m_value is None:
            gen = TwoCoverageGenerator(oracle)
            two_cov_examples = gen.generate(seed=seed)
            m_value = len(two_cov_examples)
            if verbose:
                print(f"  m value (2-COV count): {m_value} (computed)")
        elif m_value is not None and verbose:
            print(f"  m value (2-COV count): {m_value} (from config)")

        # Generate examples for each strategy
        for strategy in strategies:
            n_examples = get_example_count_for_strategy(strategy, n_features, m_value)

            if verbose:
                if n_examples is not None:
                    print(f"  {strategy} (total={n_examples})...", end=" ")
                else:
                    print(f"  {strategy} (coverage-based)...", end=" ")

            examples = generate_examples_for_strategy(
                oracle=oracle,
                strategy=strategy,
                n_examples=n_examples,
                n_features=n_features,
                seed=seed,
                valid_configs=valid_configs
            )

            # Add model info to metadata
            examples.metadata['model'] = model_name
            examples.metadata['fm_path'] = fm_path
            examples.metadata['n_features'] = n_features

            # Save to file
            output_file = output_dir / f"{model_name}_{strategy}.json"
            ExampleIO.save_json(examples, output_file)

            if verbose:
                stats = examples.statistics()
                print(f"E+={stats['n_positive']}, E-={stats['n_negative']} -> {output_file.name}")

        return True

    except Exception as e:
        print(f"Error processing {fm_path}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate test case examples from feature models (AcqMSS paper)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sampling Strategies (from paper):
    rs_1n     - Random Sampling with n examples (n = #features)
    rs_2n     - Random Sampling with 2n examples
    rs_3n     - Random Sampling with 3n examples
    rs_m      - Random Sampling with m examples (m = 2-COV count)
    2cov      - 2-wise Coverage (pairwise, using allpairspy)
    ff        - Feature Frequency (coverage-based)
    balanced  - Balanced RS (equal E+/E-, not in paper)

Example:
    PYTHONPATH=. python apps/generate_examples.py apps/conf/generate_examples_config.toml
        """
    )

    parser.add_argument(
        'config',
        help='Path to TOML configuration file'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output (overrides config)'
    )
    parser.add_argument(
        '-o', '--output-dir',
        help='Output directory (overrides config)'
    )

    args = parser.parse_args()

    # Load configuration
    if not Path(args.config).exists():
        print(f"Error: Configuration file not found: {args.config}")
        sys.exit(1)

    config = load_config(args.config)

    # Parse general settings
    general = config.get('general', {})
    seed = general.get('seed', 42)
    output_dir = Path(args.output_dir or general.get('output_dir', 'data/examples'))
    verbose = args.verbose or general.get('verbose', False)
    default_strategies = general.get('strategies', ['rs_1n', 'rs_2n', 'rs_3n', 'ff'])

    # Parse models
    models = config.get('models', [])

    if not models:
        print("Error: No models specified in configuration")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Example Generation (AcqMSS Paper Sampling)")
    print("=" * 60)
    print(f"Config: {args.config}")
    print(f"Output: {output_dir}")
    print(f"Seed: {seed}")
    print(f"Strategies: {default_strategies}")
    print(f"Models: {len(models)}")

    # Process each model
    success_count = 0
    for model in models:
        if process_model(
                model_config=model,
                default_strategies=default_strategies,
                output_dir=output_dir,
                seed=seed,
                verbose=verbose
        ):
            success_count += 1

    # Summary
    print()
    print("=" * 60)
    print(f"Completed: {success_count}/{len(models)} models")
    print(f"Output directory: {output_dir}")
    print("=" * 60)

    if success_count < len(models):
        sys.exit(1)


if __name__ == '__main__':
    main()
