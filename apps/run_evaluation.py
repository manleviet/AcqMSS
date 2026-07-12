#!/usr/bin/env python
"""
Run QuAcq -> ConGen evaluation pipeline.

Runs QuAcq (automated) to generate queries, then feeds progressive
subsets to ConGen and compares both KBs against ground truth.

Usage:
    python -m apps.run_evaluation apps/conf/run_evaluation_config.toml -v
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime

from conacq.atomic_io import write_json_atomic
from apps._harness import build_parser, setup_logging
from pathlib import Path

from conacq.runners import QuAcqRunner, ConGenRunner
from conacq.config import load_pipeline_config, parse_models
from conacq.eval.kb_comparator import KBComparator
from conacq.eval.progressive_evaluation import ProgressiveEvaluator
from conacq.oracle.ground_truth import GroundTruthData


def process_model(model_config, eval_config, quacq_config, congen_config,
                  output_dir: Path, verbose: bool):
    """Run full evaluation pipeline for a single model.

    Returns:
        dict with summary metrics, or None on error
    """
    model_name = model_config.name
    try:
        solver = quacq_config.get('solver_name', 'glucose4')
        max_queries = quacq_config.get('max_queries', 1000)
        shuffle_seed = quacq_config.get('shuffle_seed', None)
        checkpoints = eval_config.get('checkpoints', [10, 25, 50, 75, 100])

        if verbose:
            print(f"\n{'='*60}")
            print(f"Model: {model_name}")
            print(f"  FM: {model_config.oracle}")
            print(f"  Bias: {model_config.bias}")
            print(f"  Checkpoints: {checkpoints}")
            print(f"{'='*60}")

        # Step 1: Run QuAcq (automated)
        if verbose:
            print("\n  [1/3] Running QuAcq (automated)...")

        quacq_runner = QuAcqRunner(
            bias_path=model_config.bias,
            fm_path=model_config.oracle,
            solver_name=solver,
            max_queries=max_queries
        )

        quacq_start = time.perf_counter()
        quacq_result = quacq_runner.run(
            mode='automated', shuffle_seed=shuffle_seed)
        quacq_runtime = (time.perf_counter() - quacq_start) * 1000
        quacq_runner.cleanup()

        if verbose:
            print(f"    Queries: {quacq_result.n_queries}")
            print(f"    KB size: {quacq_result.n_kb}")
            print(f"    Convergence: {quacq_result.convergence_reason}")
            print(f"    Runtime: {quacq_runtime:.0f}ms")

        # Step 2: Build ConGen runner, comparator, ground truth
        if verbose:
            print("\n  [2/3] Setting up progressive evaluation...")

        congen_runner = ConGenRunner(
            bias_path=model_config.bias,
            fm_path=model_config.oracle,
            solver_name=congen_config.get('solver_name', solver),
            use_incremental=congen_config.get('use_incremental', True)
        )

        comparator = KBComparator.from_files(
            model_config.oracle, model_config.bias)
        ground_truth = GroundTruthData.from_uvl(model_config.oracle)

        evaluator = ProgressiveEvaluator(
            congen_runner=congen_runner,
            comparator=comparator,
            ground_truth=ground_truth,
            checkpoints=checkpoints
        )

        # Step 3: Run progressive evaluation
        if verbose:
            print("\n  [3/3] Running progressive ConGen evaluation...")

        prog_result = evaluator.evaluate(
            query_history=quacq_result.query_history,
            quacq_run_result=quacq_result
        )
        congen_runner.cleanup()

        if verbose:
            _print_checkpoint_table(prog_result)

        # Step 4: Build output dict and save JSON
        output = {
            'metadata': {
                'model': model_name,
                'fm_path': model_config.oracle,
                'bias_path': model_config.bias,
                'timestamp': datetime.now().isoformat(),
                'checkpoints_pct': checkpoints,
            },
            'quacq': {
                'n_queries': quacq_result.n_queries,
                'n_kb': quacq_result.n_kb,
                'convergence_reason': quacq_result.convergence_reason,
                'runtime_ms': quacq_runtime,
                'semantic_equivalent': (
                    prog_result.quacq_semantic.is_equivalent
                    if prog_result.quacq_semantic else None
                ),
            },
            'progressive': [
                {
                    'checkpoint_pct': cp.checkpoint_pct,
                    'n_queries': cp.n_queries,
                    'n_positive': cp.n_positive,
                    'n_negative': cp.n_negative,
                    'n_kb': cp.n_kb,
                    'congen_runtime_ms': cp.congen_runtime_ms,
                    'description_f1': (
                        cp.description_comparison.metrics.f1_score
                        if cp.description_comparison else None
                    ),
                    'clause_f1': (
                        cp.clause_comparison.metrics.f1_score
                        if cp.clause_comparison else None
                    ),
                    'semantic_equivalent': (
                        cp.semantic_result.is_equivalent
                        if cp.semantic_result else None
                    ),
                }
                for cp in prog_result.checkpoints
            ]
        }

        output_file = output_dir / f"{model_name}_evaluation.json"
        write_json_atomic(output_file, output)

        if verbose:
            print(f"\n  Saved: {output_file}")

        # Summary dict for batch table
        last_cp = prog_result.checkpoints[-1] if prog_result.checkpoints else None
        return {
            'model': model_name,
            'n_queries': quacq_result.n_queries,
            'quacq_kb': quacq_result.n_kb,
            'congen_kb_100': last_cp.n_kb if last_cp else 0,
            'semantic_eq': (prog_result.quacq_semantic.is_equivalent
                            if prog_result.quacq_semantic else False),
            'runtime_ms': quacq_runtime,
        }

    except Exception as e:
        print(f"Error processing {model_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def _print_checkpoint_table(prog_result):
    """Print checkpoint summary table."""
    print(f"\n  {'Pct':>5}  {'Queries':>7}  {'E+':>4}  {'E-':>4}  "
          f"{'KB':>4}  {'Desc-F1':>8}  {'Clause-F1':>10}  {'Sem-Eq':>6}")
    print(f"  {'-'*58}")
    for cp in prog_result.checkpoints:
        desc_f1 = (cp.description_comparison.metrics.f1_score
                   if cp.description_comparison else 0)
        clause_f1 = (cp.clause_comparison.metrics.f1_score
                     if cp.clause_comparison else 0)
        sem_eq = cp.semantic_result.is_equivalent if cp.semantic_result else False
        print(f"  {cp.checkpoint_pct:>4}%  {cp.n_queries:>7}  {cp.n_positive:>4}  "
              f"{cp.n_negative:>4}  {cp.n_kb:>4}  {desc_f1:>8.3f}  "
              f"{clause_f1:>10.3f}  {'Yes' if sem_eq else 'No':>6}")


def main():
    parser = build_parser(
        "Run QuAcq -> ConGen evaluation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        verbose_help=None,
        epilog="Example:\n  python -m apps.run_evaluation "
               "apps/conf/run_evaluation_config.toml -v"
    )
    parser.add_argument('-o', '--output-dir', help='Override output directory')
    parser.add_argument('--max-queries', type=int, help='Override max queries')
    parser.add_argument('--solver', default=None, help='Override SAT solver')
    parser.add_argument('--debug', action='store_true', help='Debug logging')

    args = parser.parse_args()

    setup_logging(verbose=args.verbose, debug=args.debug)

    if not Path(args.config).exists():
        print(f"Error: Config not found: {args.config}")
        sys.exit(1)

    config = load_pipeline_config(args.config)

    general = config.get('general', {})
    eval_config = config.get('evaluation', {})
    quacq_config = config.get('quacq', {})
    congen_config = config.get('congen', {})

    output_dir = Path(args.output_dir or general.get(
        'output_dir', 'data/results/evaluation'))
    verbose = args.verbose or general.get('verbose', False)

    if args.max_queries:
        quacq_config['max_queries'] = args.max_queries
    if args.solver:
        quacq_config['solver_name'] = args.solver
        congen_config['solver_name'] = args.solver

    models = parse_models(config)
    if not models:
        print("Error: No models in configuration")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"QuAcq -> ConGen Evaluation Pipeline")
        print(f"Models: {len(models)}")

    summaries = []
    for model_config in models:
        summary = process_model(
            model_config, eval_config, quacq_config, congen_config,
            output_dir, verbose)
        if summary:
            summaries.append(summary)

    # Print batch summary
    if verbose and summaries:
        print(f"\n{'='*70}")
        print("BATCH SUMMARY")
        print(f"{'Model':<20} {'Queries':>8} {'QuAcq-KB':>9} "
              f"{'ConGen-KB':>10} {'Sem-Eq':>7} {'Runtime':>10}")
        print(f"{'-'*70}")
        for s in summaries:
            print(f"{s['model']:<20} {s['n_queries']:>8} {s['quacq_kb']:>9} "
                  f"{s['congen_kb_100']:>10} "
                  f"{'Yes' if s['semantic_eq'] else 'No':>7} "
                  f"{s['runtime_ms']:>9.0f}ms")


if __name__ == '__main__':
    main()
