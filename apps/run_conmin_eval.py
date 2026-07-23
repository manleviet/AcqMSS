#!/usr/bin/env python
"""
Run the ConMin comparison-condition CV evaluation (P4d).

Four conditions (A / C / C∪S / QuAcq) × KB × example-set × k × negatives(raw|reduced),
3-fold CV over the RECORDED folds (data/folds/ — the same splits ConGen/QuAcq use, not
regenerated). Emits per-(KB,ex) JSON + two consolidated CSVs (long/tidy + CV mean±std)
to data/results_conmin/. Exports numbers only — does NOT decide eval-metric policy.

Usage:
    python -m apps.run_conmin_eval apps/conf_conmin/run_conmin_eval_config.toml -v
    python -m apps.run_conmin_eval apps/conf_conmin/run_conmin_eval_config.toml \
        --example-sets rs_1n --k 1 2 -v
"""
import argparse
import csv
import json
import logging
import sys
from pathlib import Path

from conacq.eval.conmin_cv_evaluator import (
    evaluate_kb_example, aggregate_cv, K_VALUES, NEG_MODES)
from conacq.config import load_pipeline_config, parse_models
from conacq.atomic_io import write_json_atomic
from apps._harness import build_parser, setup_logging

logger = logging.getLogger(__name__)

DEFAULT_EXAMPLE_SETS = ['2cov', 'ff', 'rs_1n', 'rs_2n', 'rs_3n', 'rs_m']


def _write_csv(rows: list, path: Path) -> None:
    """Write long/tidy rows to CSV (union of keys, stable first-seen order)."""
    if not rows:
        logger.warning("no rows for %s", path)
        return
    cols = list(dict.fromkeys(k for r in rows for k in r.keys()))
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("wrote %d rows -> %s", len(rows), path)


def _merge_per_kb(output_dir: Path) -> None:
    """Consolidate the per-(KB,example-set) JSONs into conmin_eval_{long,cv}.csv.

    Reads ``{kb}_{es}_eval.json['rows']`` — the ATOMIC unit, written once per
    example-set and never clobbered. This is deliberately NOT the per-KB CSVs: a KB
    re-run with a DISJOINT --example-sets subset overwrites its {kb}_long.csv (mode 'w')
    and would drop the earlier subset, whereas each example-set keeps its own JSON. So
    every example-set that ever ran survives the merge, however the sweep was staged.
    (The per-KB CSVs remain for convenient per-KB inspection.)
    """
    files = sorted(output_dir.glob('*_eval.json'))
    if not files:
        logger.warning("--merge: NO *_eval.json in %s — did the sweep run? Any existing "
                       "conmin_eval_*.csv is left UNCHANGED and may be STALE.", output_dir)
        return
    rows: list = []
    for f in files:
        with open(f) as fh:
            rows.extend(json.load(fh).get('rows', []))
    if not rows:
        logger.warning("--merge: %d JSON file(s) but 0 rows", len(files))
        return
    schemas = {tuple(sorted(r.keys())) for r in rows}
    if len(schemas) > 1:
        logger.warning("--merge: rows have %d DIFFERENT column schemas — likely a mix of "
                       "stale (pre-fix) and fresh JSONs. Re-run the affected KB(s) fully.",
                       len(schemas))
    _write_csv(rows, output_dir / 'conmin_eval_long.csv')
    _write_csv(aggregate_cv(rows), output_dir / 'conmin_eval_cv.csv')
    logger.info("--merge: consolidated %d rows from %d example-set JSON(s)",
                len(rows), len(files))


def main():
    parser = build_parser(
        "Run ConMin comparison-condition CV evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example: python -m apps.run_conmin_eval "
               "apps/conf_conmin/run_conmin_eval_config.toml -v")
    parser.add_argument('-o', '--output-dir', help='Output dir (overrides config)')
    parser.add_argument('--kb', nargs='*', help='Subset of KB names to run (staging)')
    parser.add_argument('--merge', action='store_true',
                        help='Merge per-KB {kb}_{long,cv}.csv into conmin_eval_{long,cv}.csv '
                             '(run once after all KBs finish; no acquisition)')
    parser.add_argument('--example-sets', nargs='*', help='Subset of example-sets to run')
    parser.add_argument('--k', nargs='*', type=int, help='k-sweep values (overrides config)')
    parser.add_argument('--negatives', nargs='*', choices=['reduced', 'raw'],
                        help='Negative encodings to sweep (default both)')
    parser.add_argument('--non-incremental', action='store_true')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    if not Path(args.config).exists():
        logger.error("Config not found: %s", args.config)
        sys.exit(1)
    config = load_pipeline_config(args.config)
    general = config.get('general', {})
    setup_logging(verbose=args.verbose or general.get('verbose', False), debug=args.debug)

    ev = config.get('evaluation', {})
    output_dir = Path(args.output_dir or general.get('output_dir', 'data/results_conmin'))
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.merge:
        logger.info("Merging per-KB CSVs in %s", output_dir)
        _merge_per_kb(output_dir)
        return
    example_sets = args.example_sets or ev.get('example_sets', DEFAULT_EXAMPLE_SETS)
    k_values = tuple(args.k) if args.k else tuple(ev.get('k_values', K_VALUES))
    negatives = args.negatives or ev.get('negatives', list(NEG_MODES))
    use_incremental = not args.non_incremental
    seed = general.get('seed', 82)

    models = parse_models(config)
    if args.kb:
        models = [m for m in models if m.name in args.kb]
    if not models:
        logger.error("No models (KBs) in configuration")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("ConMin comparison-condition CV evaluation")
    logger.info("KBs=%d  example-sets=%s  k=%s  negatives=%s  seed=%d (folds pre-recorded)",
                len(models), example_sets, k_values, negatives, seed)
    logger.info("Output: %s", output_dir)
    logger.info("=" * 60)

    total = 0
    for model in models:
        kb = model.name
        kb_rows: list = []               # per-KB: staging-safe, never clobbers other KBs
        for es in example_sets:
            examples_path = f'data/examples/{kb}_{es}.json'
            folds_path = f'data/folds/{kb}_{es}_folds.json'
            if not (Path(examples_path).exists() and Path(folds_path).exists()):
                logger.warning("skip %s/%s (missing examples or folds)", kb, es)
                continue
            logger.info("--- %s / %s ---", kb, es)
            rows = evaluate_kb_example(
                kb, es, model.oracle, model.bias, examples_path, folds_path,
                k_values=k_values, negatives=negatives, use_incremental=use_incremental)
            kb_rows.extend(rows)
            write_json_atomic(output_dir / f'{kb}_{es}_eval.json', {
                'kb': kb, 'example_set': es, 'seed': seed,
                'note': 'folds are pre-recorded (data/folds/); the acquired named KB is '
                        'bias-order dependent — CV-averaged, seed fixed (threat-to-validity)',
                'rows': rows, 'aggregated': aggregate_cv(rows)})
        # Per-KB CSVs (NOT the shared conmin_eval_*.csv) so concurrent/sequential --kb
        # runs don't overwrite each other. Run `--merge` once at the end to consolidate.
        if kb_rows:
            _write_csv(kb_rows, output_dir / f'{kb}_long.csv')
            _write_csv(aggregate_cv(kb_rows), output_dir / f'{kb}_cv.csv')
        total += len(kb_rows)

    logger.info("Done: %d rows across %d KB(s). Per-KB CSVs written; "
                "run `--merge` to consolidate into conmin_eval_{long,cv}.csv.",
                total, len(models))


if __name__ == '__main__':
    main()
