#!/usr/bin/env python
"""
Generate shared cross-validation folds for fair CONGEN vs QuAcq comparison.

Usage:
    PYTHONPATH=. python apps/generate_cv_folds.py apps/conf/run_evaluation_config.toml
    PYTHONPATH=. python apps/generate_cv_folds.py apps/conf/run_evaluation_config.toml --n-folds 5 --seed 42
"""

import argparse
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from acqmss.testcases import ExampleIO
from acqmss.eval.fold_io import generate_folds, save_folds


def main():
    parser = argparse.ArgumentParser(
        description="Generate shared CV folds for evaluation"
    )
    parser.add_argument('config', help='Path to TOML configuration file')
    parser.add_argument('--n-folds', type=int, help='Override n_folds from config')
    parser.add_argument('--seed', type=int, help='Override seed from config')
    parser.add_argument('-o', '--output-dir', help='Output directory (default: data/folds)')

    args = parser.parse_args()

    if not Path(args.config).exists():
        print(f"Error: Config not found: {args.config}")
        sys.exit(1)

    with open(args.config, 'rb') as f:
        config = tomllib.load(f)

    general = config.get('general', {})
    eval_config = config.get('evaluation', {})
    seed = args.seed or general.get('seed', 42)
    n_folds = args.n_folds or eval_config.get('n_folds', 5)
    output_dir = Path(args.output_dir or 'data/folds')
    output_dir.mkdir(parents=True, exist_ok=True)

    models = config.get('models', [])
    if not models:
        print("Error: No models in config")
        sys.exit(1)

    for model in models:
        name = model.get('name', 'unknown')
        examples_path = model.get('examples')

        if not examples_path:
            print(f"  Skipping {name}: no examples path")
            continue

        if not Path(examples_path).exists():
            print(f"  Skipping {name}: examples file not found: {examples_path}")
            continue

        examples = ExampleIO.load_json(examples_path)
        n_pos = len(examples.positive)
        n_neg = len(examples.negative)

        fold_data = generate_folds(n_pos, n_neg, n_folds, seed)

        output_file = output_dir / f"{name}_folds.json"
        save_folds(fold_data, str(output_file))

        print(f"  {name}: {n_folds} folds (E+={n_pos}, E-={n_neg}) -> {output_file}")

    print("Done.")


if __name__ == '__main__':
    main()
