#!/usr/bin/env python3
"""
Test script for bias module.

This script demonstrates how to:
1. Load a simplified YAML configuration
2. Generate a constraint bias
3. Save the bias in different formats
4. Display statistics
"""

from conacq.bias import (
    BiasConfigLoader,
    BiasGenerator,
    BiasIO,
)


def main():
    print("=" * 60)
    print("Testing Bias Module")
    print("=" * 60)
    print()

    # Step 1: Load configuration
    print("Step 1: Loading configuration from YAML...")
    config_path = '../data/bias-config/survey_example.yaml'
    config = BiasConfigLoader.load(config_path)
    print(f"  Config name: {config.name}")
    print(f"  Features: {len(config.features)}")
    print(f"  Hierarchical candidates: {len(config.hierarchical_candidates)}")
    print()

    # Step 2: Validate configuration
    print("Step 2: Validating configuration...")
    validation = BiasConfigLoader.validate_config(config)
    if validation['valid']:
        print("  ✓ Configuration is valid")
    else:
        print("  ✗ Configuration has errors:")
        for error in validation['errors']:
            print(f"    - {error}")

    if validation['warnings']:
        print("  Warnings:")
        for warning in validation['warnings']:
            print(f"    - {warning}")
    print()

    # Step 3: Generate bias
    print("Step 3: Generating bias...")
    generator = BiasGenerator(config)
    bias = generator.generate_bias()
    print()

    # Step 4: Display statistics
    print("Step 4: Bias Statistics")
    print("-" * 60)
    stats = generator.get_statistics()
    print(f"Number of features: {stats['num_features']}")
    print(f"Hierarchical constraints: {stats['num_hierarchical']}")
    print(f"Cross-tree constraints: {stats['num_cross_tree']}")
    print(f"Total constraints: {stats['total']}")
    print()
    print("Breakdown by operator:")
    for op, count in sorted(stats['breakdown'].items()):
        print(f"  {op}: {count}")
    print()

    # Step 5: Display sample constraints
    print("Step 5: Sample Constraints (first 10)")
    print("-" * 60)
    for i, constraint in enumerate(bias.constraints[:10]):
        print(f"{i+1}. {constraint}")
        print(f"   Clauses: {constraint.clauses}")
    print(f"... and {len(bias.constraints) - 10} more constraints")
    print()

    # Step 6: Save bias to files
    print("Step 6: Saving bias to files...")

    # Save to JSON
    json_path = 'data/bias/survey_bias.json'
    BiasIO.save_to_json(bias, json_path)
    print(f"  ✓ Saved to JSON: {json_path}")

    # Save to CNF
    cnf_path = 'data/bias/survey_bias.cnf'
    BiasIO.save_to_cnf(bias, cnf_path)
    print(f"  ✓ Saved to CNF: {cnf_path}")

    # Save statistics
    stats_path = 'data/bias/survey_bias_stats.txt'
    BiasIO.save_statistics(bias, stats_path)
    print(f"  ✓ Saved statistics: {stats_path}")
    print()

    # Step 7: Test loading bias from JSON
    print("Step 7: Testing load from JSON...")
    loaded_bias = BiasIO.load_from_json(json_path)
    print(f"  ✓ Loaded {len(loaded_bias.constraints)} constraints")
    print(f"  ✓ Loaded {len(loaded_bias.features)} features")

    # Verify
    if len(loaded_bias.constraints) == len(bias.constraints):
        print("  ✓ Verification: constraint count matches")
    else:
        print("  ✗ Verification failed: constraint count mismatch")
    print()

    print("=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
