# make_tables Generator — Build Complete

**Date**: 2026-07-26
**Component**: `apps/make_tables/`
**Status**: DONE (4/4 phases, committed `25363855`)

## What shipped

`apps/make_tables/` (11 modules) — reads `data/results_conmin/{KB}_long.csv` and emits every AAAI paper table (11 tables, `.md` + `.tex`) + `PROVENANCE.md`, per the CW-Main spec (vault `prompts/` v1+v2+v3). Committed scoped (19 files, 1621 insertions); the live sweep's `data/results_conmin/*` deliberately excluded.

## The 4-phase arc

1. **loader + gates** — per-KB CSV read with a torn-read mtime guard (safe while the sweep rewrites files); per-KB STALE + empty-scope gates.
2. **filters / aggregate / tiers** — exact strategy filters (`condition,negatives,k`), row-level exclude-2COV CV means, 3 metric tiers, convergence-aware daggering (non-converged = `aggregate_cv`'s `{timeout,max_queries}`, mirrored from `conmin_cv_evaluator.py`).
3. **render + tables** — 11 tables through a booktabs v3 LaTeX renderer (`\tabularnewline`, `\cmidrule` super-cols, `\multirow`, `$x^{\dagger}$`, `{,}` thousands, `\KB`/`\supp` macros) + a Markdown reading aid.
4. **self-check + tests** — 20 anchors (numeric, tol 5e-3, never string), 15 unit tests, PROVENANCE.

## Anchored to data, not to hope

- **20 self-check anchors reproduce** through the modules; drift → exit 3 (a drift means the *input* changed, never "re-fit the anchor").
- **pdflatex compile exit 0** against the real vault preamble (`Overleaf/AAAI/main_short.tex`, `\KB`/`\supp`), zero unresolved refs.
- **Full suite 606 pass.**

## Key decisions (CW-Main final layout)

- Main `eval-prf` = Semantic tier, 4 strategies (A/C/C∪S/QuAcq-active), **exactly 16 numeric cols (P/R/F1/$|\KB|$), NO accuracy** — keeps the feasibility argument intact. Appendix `app-prf-desc`/`app-prf-clause` mirror it; accuracy in `app-accuracy`, the 5th condition (QuAcq example-only) in `app-perset`.
- **Bold = per-row MAX, computed** — arcade desc bolds QuAcq-active (0.49), not ConMin (0.41). The "ConMin ~2.8× desc" claim was withdrawn: the winner is per-KB, no universal multiplier. No ratio column.
- budget/$|B|$ computed from `qa_max_queries/n_bias` (pre-empts "QuAcq under-budgeted").

## A clarification worth recording

`exact_equiv=1` alongside `sem-F1 0.842` (QuAcq-active, REAL-FM-7) first *looked* contradictory. It is not — by design (`conmin_slice_scorer.py:54-72`): `sem_*` is name-set P/R/F1 (BG excluded, root dropped); `exact_equiv` is logical equivalence of the *delivered theory* (slice ∪ ¬e⁻ fallbacks ∪ BG/root) via `SemanticEquivalenceChecker`. Logical equivalence with a different name-set is legitimate (RE7 A/C∪S: exact_equiv=1 at sem-F1 0.977). `exact-equiv.md` now carries a neutral note; QuAcq-active is learned once/KB, so its `exact_equiv=1` is **one** observation, not 18. Lesson: verify the metric's *definition* before calling a value an anomaly.

## Discipline under a live sweep

Never wrote `data/results_conmin/*.json` or `Overleaf/` (separate push-only clone); smoke output to throwaway `/tmp`; RE4/busybox QuAcq-active anchors held as `PENDING_QUACQ_ACTIVE` — finalize after tonight's re-run + `--merge`, then CW Main's independent cell audit.

## Next

Official `--official` run + RE4/busybox anchor capture after the overnight sweep + `--merge`. No blocking issues.
