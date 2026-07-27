# QuAcq-active band-aid drops — genuine/over-strong/redundant (G/S/R) split

Committed so the citation in `PROVENANCE.md` resolves in-repo. **Traceability only** — these values
remain NOT re-derivable from the committed `_long.csv`; re-measure per the procedure below.

Upstream origin: the Cowork vault findings note `ConMin - Evaluation findings (for writing).md`
(section A2, 2026-07-26). This committed file is the in-repo copy of record; the vault is a separate
repository that the AAAI reproducibility package does not ship.

## Values — genuine (G) of the total band-aid drops

| KB | genuine (G) | total drops | note |
|---|---|---|---|
| REAL-FM-7 | 1 | 10 | |
| fqa | 150 | 354 | |
| arcade-game | 35 | 56 | **STALE** — superseded by the fair-budget re-run (raw is now 326). Per-query rate 56/863 = 0.0649 vs 326/5000 = 0.0652 confirms a longer re-run, not a counter-semantics change. Not re-classified against the 326-drop run. |

- **Method:** offline G/S/R entailment classification (genuine recall lost / over-strong, correctly
  removed / redundant) — run by the reviewer, NOT emitted by the runner.
- **Date:** 2026-07-26. **Classification commit:** not recorded.

## Method provenance (NOT the source of these values)

The two committed fairness-measurement reports under `plans/`:

- `plans/reports/from-code-reviewer-to-cw-impl-260726-fairness-measurement-redteam.md`
- `plans/260724-1841-quacq-active-oracle-eval/reports/from-code-reviewer-to-cw-impl-260726-quacq-active-fairness-measurement.md`

are the **PRE-FIX probe**: 23 drops / 14 true on a superseded 342-query QuAcq-active run. That
14-true figure was later found to **overcount** (the current post-fix run is 272 queries,
`no_query`). Cite these reports for the classification **method only**, NOT for the values above.

## Re-measure procedure

The per-drop classification was never persisted, so these values are NOT re-derivable from the
committed `_long.csv` (unlike the 8/144 exact-equivalence figures). To re-measure: re-add the
env-gated `_FAIRNESS_PROBE` hook to `quacq.py`, re-run the oracle + example-only runs, then re-run
the G/S/R entailment classification per the two reports' method. There is no push-button script —
the probe hook is reverted, not committed.

## Upgrade path

When a real per-drop classification is produced, **replace this file** with
`genuine_classification.json` (per-drop G/S/R records) at the same path. At that point the values
become re-derivable from that committed artifact, and the "traceability only / not re-derivable"
caveat is **removed** from `_GENUINE_SPLIT` rather than documented — a replacement, not a rewrite.
