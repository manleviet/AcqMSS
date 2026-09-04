# T9b — UnifiedConGenResult: analysis (no code) → DỪNG, Cowork decides

**Date:** 2026-07-12 · **Branch:** feat/redesign-abc-v2 · **T9 committed:** 20cfae8
**Task type:** analysis only (Cowork: divergent schemas ⇒ merge is a design decision, do not choose).

## Step 1 — Do the two types describe the same schema?

| Field | `ConGenResultData` (READ, result_loader) | `ConGenRunResult` (WRITE, runner) |
|---|---|---|
| kb_constraints | ✓ | ✓ |
| redundant_constraints | ✓ | ✓ |
| n_bias | ✓ | ✓ |
| n_mss | ✓ | ✓ |
| n_kb | ✓ | ✓ |
| bg_clauses | ✓ | ✓ |
| metadata | ✓ (read-only) | — |
| kb_clauses (CNF) | — | ✓ (write-only) |
| runtime_ms / consistency_checks / memory_peak_mb | — | ✓ (write-only) |
| profiler_data | — | ✓ (write-only) |
| metrics (RunMetrics, live) | — | ✓ (write-only) |
| methods | from_json / from_dict / to_dict / kb_reduction_ratio | to_dict |

Overlap **6**, write-only **6**, read-only **1**. **They diverge.**

## Step 2 — Divergent ⇒ design decision (DỪNG)

`ConGenResultData` is a **read-projection**: only what `kb_comparator` /
`progressive_evaluation` need from a persisted file. It does *not* reconstruct
`kb_clauses`, `metrics`, `profiler_data`, or the perf scalars from JSON — the
comparator never uses them. `ConGenRunResult` is the full **write-product**: the
live CNF + `RunMetrics` object + profiler a run emits.

A merge forces a choice, neither free:
- **(A) carry all write fields** → `from_json` leaves kb_clauses/metrics/profiler
  empty → a half-populated object; reading `.metrics` on a *loaded* result is `None`
  (a silent footgun exactly where the comparator lives).
- **(B) drop write fields** → the runner loses kb_clauses/metrics → breaks
  `cross_validation` (reads `run_result.metrics` + `kb_clauses`).

The 6-field overlap is shared **domain vocabulary** (kb / n_bias / n_mss / n_kb /
redundant / bg), not evidence of one schema. This is the very read≠write wall that
made T9 byte-identical for free; merging couples the two sides back together.

## Step 3 — Buy vs lose (for Cowork's decision)
- **Buy:** kill the drift between two dataclasses that both name the 6 shared fields — a small, low-churn cost today.
- **Lose:** read/write separation; a half-populated-object footgun; blast radius 6+ files
  (kb_comparator, progressive_evaluation, run_compare, run_congen, runners/__init__, test 3 / test_evaluation).

**Claude's recommendation: do NOT merge.** The read/write wall is an asset, not debt.
Keep `ConGenResultData` (read projection) and `ConGenRunResult` (write product) distinct.

## Unresolved questions
1. Cowork's call: (a) keep them separate (drop T9b — recommended), (b) merge anyway
   with an explicit choice of A/B above, or (c) a third framing (e.g. a shared
   `@dataclass` mixin for only the 6 overlapping names, no behavior merge)?
