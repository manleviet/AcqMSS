---
phase: 2
title: Filters + aggregation + tiers
status: completed
effort: ~2.5h
priority: P1
dependencies:
  - 1
---

# Phase 2: Strategy filters, CV aggregation, 3 tiers, convergence-awareness

## Overview
The numeric core: given loaded rows, produce a clean per-(KB, strategy, metric) value with the exact filter, aggregation, tier, convergence, and rounding rules. Pure functions, heavily unit-tested (Phase 4). No LaTeX/MD yet.

## Strategy → CSV filter (v1, exact)
| paper column | `condition` | `negatives` | `k` |
|---|---|---|---|
| max. specific (A) | `A` | `n/a` | *(blank)* |
| min. cover (C) | `C` | `raw` | *(blank)* |
| ConMin (C∪S) | `C∪S` | `raw` | `1` |
| QuAcq (example-only) | `QuAcq` | `n/a` | *(blank)* |
| QuAcq-active | `QuAcq-active` | `n/a` | *(blank)* |
(Confirm actual sentinel spelling of "blank"/`n/a`/`raw` in the CSV during impl — grep distinct values per column; adapt the filter constants, do not hard-fail on a spelling difference.)

## Aggregation (v1 + v2 G2)
- **Row-level mean** over all rows matching the filter (+ exclude-2COV / all-6 per table), each fold equal, skip nan/empty. NOT mean-of-per-sampling-means.
- **exclude-2COV**: drop `example_set == '2cov'` for headline tables; keep all 6 for per-sampling appendix. Driven by the table's config, default on.
- **Convergence-aware (v2 G2) — partition from CODE, not assumption (red-team #2).** The authoritative converged/non-converged split lives in `conacq/eval/conmin_cv_evaluator.py::aggregate_cv` (~:391-396): **non-converged = exactly `{timeout, max_queries}`**; `{pool_exhausted, no_query, empty_bias, ''}` are treated as converged and **stay in the mean**. Reuse that partition; do not invent a `converged` literal (none exists in the data). Full observed vocabulary + who has it:
  - passive `QuAcq` → `pool_exhausted` on **all** KBs (crippled-but-converged baseline; **not** daggered).
  - `QuAcq-active` → REAL-FM-7 `no_query` (not daggered); fqa + arcade-game `max_queries` (daggered; arcade re-run w/ timeout 7200); REAL-FM-4 `timeout`→`max_queries` after tonight's re-run; busybox `max_queries` expected tonight (all daggered).
  - `A`/`C`/`C∪S` → blank `''` (non-QuAcq; ignore for convergence).
  Group by `convergence_reason` before averaging only to avoid blending a `{timeout,max_queries}` fold with a converged one.
- **All-non-converged cell** (folds all in `{timeout,max_queries}`): still reported as the value, **marked `†`** (Phase 3 `$x^{\dagger}$`); carry its `convergence_reason` + budget. **Read `qa_max_queries`/`qa_timeout_s` from the row** — they are blank for passive QuAcq and `5000`/`400` for QuAcq-active — never hardcode 5000. Never `--`, never unmarked.
- **QuAcq-active** learned once/KB, scored every fold ⇒ structural metrics constant (std=0). Emit single value; flag so the Phase-4 row-count check does not treat the duplication as an anomaly. (Passive QuAcq folds DO vary — see the anchor caveat in Phase 4.)

## Three tiers (v2 G1)
Every P/R/F1 producer returns all three, P and R separate:
`Desc` = `desc_{p,r,f1}`, `Clause` = `clause_{p,r,f1}`, `Sem` = `sem_{p,r,f1}`. Order Desc→Clause→Sem. Desc is strict (no alias tolerance — surface the raw column).

## Column → field map (v1 §"Column → CSV field"; all verified present)
prec/rec/F1 per tier (above); accuracy=`accuracy`; specificity=`specificity`; exact-equiv=`exact_equiv`; `|A|`=`n_mss`, `|C|`=`n_cover`, `|S|`=`n_support`, `|KB|`=`n_kb`, `|U|`=`n_uncoverable`, `|B|`=`n_bias`; checks=`stage1_batch_checks`; t(s)=`total_ms`/1000; queries=`oracle_queries`; confusion=`tp/tn/fp/fn`; per-phase=`checks_{gate,admpool,cover_rej,cover_qx,redundancy,total}`; preprocessing=`preprocessing_checks`.

## Rounding (v1) — return formatted strings at the edge, keep floats internally
rates/F1/P/R/acc/spec/exact → **2dp, trailing zeros** (`0.80`, `12` never for rates); sizes → **1dp** (`12.0`); checks → **int** (thousands `{,}` applied in LaTeX layer only); runtime → **1dp** seconds; queries → **1dp**. Missing → `--`.

## Related Code Files
- Create: `apps/make_tables/{filters.py,aggregate.py,tiers.py,formatting.py}`
- Read-only: v1 §Aggregation, v2 G1/G2

## Implementation Steps
1. `filters.select(rows, column_spec, exclude_2cov)` → matching rows.
2. `aggregate.cv_mean(rows, field, group_by_convergence=False)` → (value, convergence_reason, n, all_nonconverged, std).
3. `tiers.prf(rows, tier)` → the tier's P/R/F1 via cv_mean.
4. `formatting.fmt(value, kind)` → 2dp/1dp/int/`--`/`†` (marker added by caller with convergence info).
5. Keep every function pure (rows in, value out) for Phase-4 unit tests.

## Success Criteria
- [ ] Filters reproduce the 5 columns' exact (condition,negatives,k) selection.
- [ ] cv_mean = equal-fold row mean, nan-skipping; convergence grouping never blends converged+capped.
- [ ] All-non-converged cell returns value + non-converged flag (for `†`); QuAcq-active std=0 flagged as by-construction.
- [ ] 3 tiers returned separately; rounding matches v1 (trailing zeros).
- [ ] Matches the v2 ADD anchors on REAL-FM-7 (spot-check in impl before Phase 4 formalizes it).

## Risk Assessment
- Risk: sentinel spelling (`n/a` vs empty vs `NaN`) differs from spec. Mitigation: grep distinct per-column values first; make filter constants data-driven.
- Risk: `k` typing. `k` is a **string** column with values `{'','1','2','3','5'}` (red-team #14). *(blank)* means `k == ''` **exactly**, NOT "match any k" — filter `k==''` for A/C/QuAcq/QuAcq-active, `k=='1'` for ConMin. "any" would sweep k∈{1,2,3,5} into one cell (144 C∪S rows instead of 18). Do NOT implement "any".
