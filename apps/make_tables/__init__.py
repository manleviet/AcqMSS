"""make_tables — ConMin result CSVs -> paper tables (.md + .tex).

Package entry point: ``python -m apps.make_tables``. Built from CW Main's spec
(v1 + ADDENDUM v2 (data rules, wins) + v3 (LaTeX house style)). CW Main
independently audits every emitted cell, so correctness is the whole point:
every cell must trace to a CSV row by the fixed filter/aggregation rules.

Phase 1 (this module set): package scaffold, per-KB CSV loader with a torn-read
guard, per-KB STALE + empty-scope gates, and a PROVENANCE skeleton. Filters,
aggregation, metric tiers, table emission and the self-check anchors land in the
later phases.
"""
from __future__ import annotations

# The five evaluation KBs in fixed paper order (KB1..KB5): row labels + iteration order.
KBS = ("REAL-FM-7", "fqa", "arcade-game", "REAL-FM-4", "busybox-1.18.0")

# |C_tau|, the target-theory size per KB. NOT present in any result CSV (the runner never emits it),
# so it is carried here as a constant transcribed from the KB table in the paper
# (main_short.tex, Table `tab:eval-fms`: #features / |C_tau| / |B| / domain). Used only as a row
# label in eval-prf / app-prf-desc. If that table changes, change this with it — nothing downstream
# can catch the drift, because there is no CSV column to check it against.
KB_TARGET_SIZE = {"REAL-FM-7": 13, "fqa": 102, "arcade-game": 70,
                  "REAL-FM-4": 219, "busybox-1.18.0": 905}

# Only QuAcq conditions carry a convergence reason / the diagnostic counters, so the
# STALE + empty-scope gates apply to these; A/C/C-union-S rows are blank by design.
QUACQ_CONDITIONS = ("QuAcq", "QuAcq-active")

# afaa04b diagnostic counters — present ONLY on post-counter _long.csv rows. An absent
# column means a pre-counter (stale) row (v2 "Input freshness gate"), reported as ``--``.
COUNTER_COLS = (
    "quacq_bandaid_drops",
    "quacq_findc_unconfirmed",
    "quacq_empty_scope_appends",
    "quacq_prune_partial_pruned",
    "quacq_prune_complete_pruned",
)

# Natural key identifying one CV row across the per-KB CSVs (v1 "union by" tuple).
UNION_KEY = ("kb", "example_set", "fold", "condition", "negatives", "k")
