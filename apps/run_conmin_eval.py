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
    evaluate_kb_example, aggregate_cv, _learn_quacq_active, K_VALUES, NEG_MODES)
from conacq.config import load_pipeline_config, parse_models
from conacq.atomic_io import write_json_atomic
from apps._harness import build_parser, setup_logging

logger = logging.getLogger(__name__)

DEFAULT_EXAMPLE_SETS = ['2cov', 'ff', 'rs_1n', 'rs_2n', 'rs_3n', 'rs_m']

# --conditions CLI aliases → row condition labels. A subset recomputes only those conditions
# and surgically merges into the existing per-set JSON (reusing the expensive ConMin Stage-1).
_CONDITION_ALIASES = {'a': 'A', 'c': 'C', 'cus': 'C∪S', 'c∪s': 'C∪S',
                      'quacq': 'QuAcq', 'quacq-active': 'QuAcq-active'}


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
    # Failure-marker rows ({**meta, condition, k, flag}) are sparse BY DESIGN (B2/B3, plus
    # QuAcq/QuAcq-active learn errors) — they carry no metric columns and an 'error'/'gate_tripped'
    # flag. They must stay sparse: blank-filling their flag into healthy rows would make
    # aggregate_cv's presence-test classify every fold as failed (voiding all means), and their
    # missing metric columns are not a "stale schema". So partition, and only align SCORED rows.
    def _is_fail(r):
        return 'error' in r or 'gate_tripped' in r
    scored = [r for r in rows if not _is_fail(r)]
    fails = [r for r in rows if _is_fail(r)]

    # H-5: union + blank-fill SCORED rows so a purely-ADDITIVE column delta (the new
    # convergence_reason/qa_* columns absent from pre-fix committed JSONs) merges cleanly.
    # Warn ONLY if a NON-additive column is missing from some scored row (a genuine stale mix).
    ADDITIVE = {'convergence_reason', 'qa_max_queries', 'qa_timeout_s'}
    skeys = list(dict.fromkeys(k for r in scored for k in r.keys()))
    stale = sorted(k for k in skeys if k not in ADDITIVE
                   and any(k not in r for r in scored) and any(k in r for r in scored))
    if stale:
        logger.warning("--merge: %d non-additive column(s) %s missing from some rows — likely a "
                       "stale (pre-fix) schema mix. Re-run the affected KB(s) fully.",
                       len(stale), stale)
    # Blank-fill with None (not ''): aggregate_cv skips None for numeric _AGG_COLS; '' would slip
    # past its `is not None` filter and blow up statistics.mean. Failure rows are appended
    # UNCHANGED (sparse) so aggregate_cv still classifies them via the flag key presence.
    rows = [{k: r.get(k, None) for k in skeys} for r in scored] + fails

    # C-4: refuse to silently blend QuAcq-active rows that disagree on provenance (a KB re-run
    # under a different budget/timeout mixes two theories under one label). Warn per conflict.
    prov: dict = {}
    for r in scored:
        if r.get('condition') == 'QuAcq-active':
            prov.setdefault((r.get('kb'), r.get('example_set')), set()).add(
                (r.get('qa_max_queries'), r.get('qa_timeout_s')))
    conflicts = sorted(k for k, sigs in prov.items() if len(sigs) > 1)
    if conflicts:
        logger.warning("--merge: QuAcq-active provenance conflict in %d (kb,es) %s — mixed "
                       "max_queries/timeout_s across passes; re-run those KB(s) consistently.",
                       len(conflicts), conflicts)

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
    parser.add_argument('--no-quacq-active', action='store_true',
                        help='Skip the QuAcq-active (oracle-mode) condition')
    parser.add_argument('--quacq-active-timeout', type=float,
                        help='Wall-clock cap (s) for the QuAcq-active learn (overrides config)')
    parser.add_argument('--quacq-active-max-queries', type=int,
                        help='Query budget for the QuAcq-active learn (overrides config/per-KB)')
    parser.add_argument('--conditions', nargs='+', metavar='COND',
                        help='Recompute ONLY these conditions (a, c, cus, quacq, quacq-active; '
                             'comma- or space-separated). Surgically merges into the existing '
                             '{kb}_{es}_eval.json, preserving every other condition verbatim — '
                             'reuses the expensive ConMin Stage-1. Default: all conditions.')
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

    # QuAcq-active knobs: CLI > per-KB map (in the loop) > [evaluation] default > hardcoded.
    run_quacq_active = (not args.no_quacq_active) and ev.get('quacq_active', True)
    qa_timeout = (args.quacq_active_timeout if args.quacq_active_timeout is not None
                  else ev.get('quacq_active_timeout_s', 400.0))
    qa_maxq_default = (args.quacq_active_max_queries if args.quacq_active_max_queries is not None
                       else ev.get('quacq_active_max_queries', 5000))
    qa_maxq_per_kb = {} if args.quacq_active_max_queries is not None \
        else ev.get('quacq_active_max_queries_per_kb', {})
    quacq_query_mode = ev.get('quacq_query_mode', 'example_only')

    # --conditions: resolve to a label set (None ⇒ full run). A subset triggers surgical merge.
    selected_conditions = None
    if args.conditions:
        raw = [t.strip().lower() for item in args.conditions for t in item.split(',') if t.strip()]
        bad = sorted(t for t in raw if t not in _CONDITION_ALIASES)
        if bad:
            logger.error("Unknown --conditions %s; valid: %s", bad, sorted(_CONDITION_ALIASES))
            sys.exit(1)
        selected_conditions = {_CONDITION_ALIASES[t] for t in raw}

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
    logger.info("QuAcq-active=%s  max_queries=%s (per-KB=%s)  timeout_s=%s",
                run_quacq_active, qa_maxq_default, qa_maxq_per_kb or '{}', qa_timeout)
    logger.info("conditions=%s  quacq_query_mode=%s",
                sorted(selected_conditions) if selected_conditions else 'ALL', quacq_query_mode)
    logger.info("Output: %s", output_dir)
    logger.info("=" * 60)

    total = 0
    for model in models:
        kb = model.name
        kb_rows: list = []               # per-KB: staging-safe, never clobbers other KBs

        # QuAcq-active (H-6): learn ONCE per KB (oracle mode is fold/example-independent) and
        # reuse across every example-set. Done here, before the es-loop, so the runner's own
        # FMOracle is released before evaluate_kb_example opens its own (M-3, avoids a 2× live
        # 854-var solver peak on busybox). max_queries is the deterministic rail; timeout a
        # safety net (C-4) — size max_queries per KB so it fires first on big models (H-4).
        active_res, quacq_active_error = None, None
        qa_max_queries = qa_maxq_per_kb.get(kb, qa_maxq_default)
        # Only learn QuAcq-active when it is actually being computed (skip on a QuAcq-only recompute).
        learn_active = run_quacq_active and (selected_conditions is None
                                             or 'QuAcq-active' in selected_conditions)
        if learn_active:
            logger.info("QuAcq-active learn (once/KB): %s  max_queries=%s  timeout_s=%s",
                        kb, qa_max_queries, qa_timeout)
            try:
                active_res = _learn_quacq_active(
                    model.bias, model.oracle, 'glucose4', use_incremental,
                    qa_max_queries, qa_timeout)
                logger.info("  QuAcq-active %s -> KB=%d queries=%d reason=%s", kb,
                            active_res.n_kb, active_res.n_queries,
                            active_res.convergence_reason)
            except Exception as exc:  # a per-KB learn failure must not void the KB's rows
                logger.exception("QuAcq-active learn FAILED: %s", kb)
                quacq_active_error = str(exc)

        for es in example_sets:
            examples_path = f'data/examples/{kb}_{es}.json'
            folds_path = f'data/folds/{kb}_{es}_folds.json'
            if not (Path(examples_path).exists() and Path(folds_path).exists()):
                logger.warning("skip %s/%s (missing examples or folds)", kb, es)
                continue
            logger.info("--- %s / %s ---", kb, es)
            target = output_dir / f'{kb}_{es}_eval.json'
            # Subset recompute has nothing to reuse if the per-set JSON is absent → refuse (do
            # NOT write a partial JSON that --merge would treat as a complete set).
            if selected_conditions is not None and not target.exists():
                logger.error("--conditions needs an existing %s to reuse — run a FULL eval for "
                             "%s/%s first.", target, kb, es)
                sys.exit(1)
            rows = evaluate_kb_example(
                kb, es, model.oracle, model.bias, examples_path, folds_path,
                k_values=k_values, negatives=negatives, use_incremental=use_incremental,
                active_res=active_res, quacq_active_error=quacq_active_error,
                qa_max_queries=qa_max_queries, qa_timeout_s=qa_timeout,
                conditions=selected_conditions, quacq_query_mode=quacq_query_mode)
            if selected_conditions is None:
                merged_rows = rows
                payload = {
                    'kb': kb, 'example_set': es, 'seed': seed,
                    # C-4 provenance: which QuAcq-active budget/timeout produced these rows, so a
                    # timed row is traceable and --merge can refuse to blend mismatched passes.
                    'quacq_active_max_queries': qa_max_queries if run_quacq_active else None,
                    'quacq_active_timeout_s': qa_timeout if run_quacq_active else None,
                    'note': 'folds are pre-recorded (data/folds/); the acquired named KB is '
                            'bias-order dependent — CV-averaged, seed fixed (threat-to-validity)',
                    'rows': merged_rows, 'aggregated': aggregate_cv(merged_rows)}
            else:
                # Surgical merge: replace ONLY the selected conditions' rows; every other
                # condition's rows are preserved verbatim (byte-identical). Recompute aggregated.
                with open(target) as fh:
                    existing = json.load(fh)
                preserved = [r for r in existing.get('rows', [])
                             if r.get('condition') not in selected_conditions]
                merged_rows = preserved + rows
                payload = dict(existing)  # keep seed/note/provenance of non-recomputed conditions
                payload['rows'] = merged_rows
                payload['aggregated'] = aggregate_cv(merged_rows)
                if 'QuAcq-active' in selected_conditions:  # refresh provenance only if recomputed
                    payload['quacq_active_max_queries'] = qa_max_queries if run_quacq_active else None
                    payload['quacq_active_timeout_s'] = qa_timeout if run_quacq_active else None
            write_json_atomic(target, payload)
            kb_rows.extend(merged_rows)
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
