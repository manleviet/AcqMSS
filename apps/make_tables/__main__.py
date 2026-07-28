"""``python -m apps.make_tables`` — CLI entry (Phase 1: load + gates + provenance).

Phase 1 scope: parse the CLI, load per-KB CSVs (torn-read guarded), run the per-KB
STALE + empty-scope gates, write the PROVENANCE skeleton, and print a per-KB status
summary. Table emission (filters / aggregation / tiers / LaTeX) lands in later phases.

The default output dir is a THROWAWAY path — writing the canonical
``data/results_conmin/tables/`` requires ``--official`` (valid only post-sweep +
``--merge``), so a bare invocation never lands mid-sweep tables in the official spot.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from apps._harness import build_parser, setup_logging

from . import KBS, gates, loader, provenance, render, selfcheck, tables

logger = logging.getLogger(__name__)

_DEFAULT_RESULTS = "data/results_conmin"
_THROWAWAY_TABLES = "/tmp/make_tables_out"


def _build_cli():
    parser = build_parser(
        "Generate paper tables from ConMin result CSVs (.md + .tex).",
        config="none", verbose=True)
    parser.add_argument("--results-dir", default=_DEFAULT_RESULTS,
                        help=f"Dir holding the per-KB *_long.csv (default: {_DEFAULT_RESULTS})")
    parser.add_argument("--tables-dir", default=None,
                        help=f"Output dir for tables/PROVENANCE (default: {_THROWAWAY_TABLES}; "
                             "with --official -> <results-dir>/tables)")
    parser.add_argument("--official", action="store_true",
                        help="Write canonical <results-dir>/tables (post-sweep + --merge ONLY)")
    parser.add_argument("--kbs", nargs="*", default=list(KBS),
                        help="Subset of KBs to process (default: all five)")
    excl = parser.add_mutually_exclusive_group()
    excl.add_argument("--exclude-2cov", dest="exclude_2cov", action="store_true", default=True,
                      help="Exclude example_set=2cov from headline tables (default)")
    excl.add_argument("--no-exclude-2cov", dest="exclude_2cov", action="store_false",
                      help="Keep all samplings (do not exclude 2cov)")
    return parser


def _resolve_tables_dir(args) -> Path:
    if args.tables_dir:
        return Path(args.tables_dir)
    if args.official:
        return Path(args.results_dir) / "tables"
    return Path(_THROWAWAY_TABLES)


def main(argv=None) -> int:
    args = _build_cli().parse_args(argv)
    setup_logging(verbose=args.verbose)
    results_dir = Path(args.results_dir)
    tables_dir = _resolve_tables_dir(args)
    if args.official:
        logger.warning("--official: canonical tables are valid only AFTER the sweep completes + "
                       "--merge; mid-sweep tables are throwaway (v2 STALE gate).")

    loaded = loader.load_all(results_dir, args.kbs)

    # Per-KB gates: a stale/not-ready KB is forced to all '--'; the empty-scope gate
    # may retire the sweep-wide 'precision 1.000' claim.
    status: dict[str, str] = {}
    empty_scope_tripped = False
    for kb in args.kbs:
        rows = loaded[kb]
        if rows is None:
            status[kb] = "absent/not-ready -> --"
            continue
        if gates.is_stale(kb, rows):
            loaded[kb] = None
            status[kb] = "STALE -> --"
            continue
        status[kb] = f"fresh ({len(rows)} rows)"
        empty_scope_tripped |= gates.check_empty_scope(kb, gates.empty_scope_value(kb, rows))

    survivors = [kb for kb, rows in loaded.items() if rows]
    if not survivors:
        logger.error("no fresh KB survived the gates — nothing to tabulate")
        return 1
    if empty_scope_tripped:
        logger.error("empty-scope gate tripped — stop and report to CW Impl before tabulating")
        return 2

    tables_dir.mkdir(parents=True, exist_ok=True)

    # Self-check BEFORE emit — never leave a wrong/partial table set where a glob could consume it.
    checks_ok, skipped = selfcheck.run_all(loaded)
    if not checks_ok:
        (tables_dir / "SELFCHECK-FAILED.md").write_text(
            "# self-check FAILED — tables NOT emitted\n\n"
            "Anchor drift / broken cell on a loaded KB / short KB. See stderr for the offending "
            "anchor(s). The INPUT changed — do NOT re-fit the anchors.\n")
        logger.error("self-check failed — tables NOT emitted")
        print(f"make_tables: SELF-CHECK FAILED — no tables emitted -> {tables_dir}")
        return 3

    # Emit every table as .tex (\input-ready float) + .md; a KB absent/stale -> '--' cells.
    grids = tables.build_all(loaded, exclude_2cov=args.exclude_2cov)
    for grid in grids:
        (tables_dir / f"{grid.label}.tex").write_text(render.latex(grid))
        (tables_dir / f"{grid.label}.md").write_text(render.markdown(grid))
    (tables_dir / "exact-equiv.md").write_text(tables.exact_equiv_md(loaded))
    provenance.write_skeleton(tables_dir / "PROVENANCE.md",
                              provenance.collect(results_dir, loaded),
                              table_labels=[g.label for g in grids],
                              exclude_2cov=args.exclude_2cov)
    logger.info("emitted %d tables (.tex + .md) + exact-equiv.md -> %s", len(grids), tables_dir)

    # Product on stdout (diagnostics went to stderr via logging).
    print("make_tables (load + gates + self-check + emit)")
    for kb in args.kbs:
        print(f"  {kb:16s} {status[kb]}")
    print(f"survivors: {', '.join(survivors)}  |  exclude_2cov={args.exclude_2cov}  "
          f"|  {len(grids)} tables -> {tables_dir}  |  anchors=OK  skipped={skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
