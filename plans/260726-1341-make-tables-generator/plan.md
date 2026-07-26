---
title: make_tables.py — ConMin CSVs → paper tables (.md + .tex)
description: >-
  Build apps/make_tables — reads data/results_conmin per-KB _long.csv, emits 10
  paper tables (.md+.tex) + PROVENANCE.md per CW-Main spec v1+v2+v3. Critical
  path: AAAI Evaluation section blocked on it.
status: completed
priority: P1
branch: feat/conmin
tags:
  - conmin
  - aaai
  - tables
  - make-tables
  - eval
  - latex
blockedBy: []
blocks:
  - 260726-1243-aaai-repro-artifact
created: '2026-07-26T11:37:58.028Z'
createdBy: 'ck:plan'
source: skill
---

# make_tables.py — ConMin CSVs → paper tables (.md + .tex)

## Overview
Build `apps/make_tables` — one authoritative, deterministic, re-runnable script that reads `data/results_conmin/{KB}_long.csv` and emits **every paper table** (main + appendix) as `.md` (reading) + `.tex` (`\input`-ready) into `data/results_conmin/tables/`, plus `PROVENANCE.md`. **No paper number is ever hand-typed**; every cell traces to the CSV by a fixed rule. **My deliverable** — CW Main *authors the spec* and *independently audits* the output (re-derives sample cells); I *implement*. **Critical path**: the AAAI Evaluation section (due **2026-07-28**) is blocked on these tables.

**Additive**: new app + tests only; no learner/runner change (A/C/C∪S/ConMin/QuAcq paths + `data/results/interactive/` untouched).

## Spec authority chain (in Viet-Man's vault, NOT the repo)
`/Users/manleviet/Library/Mobile Documents/iCloud~md~obsidian/Documents/Everything/Cowork/AcqMSS/prompts/`
1. `Table-generator spec (CSV to md+latex).md` — **v1** (base: I/O, filters, 9 tables, rounding, self-checks).
2. `Table-generator spec ADDENDUM v2 (post-fix, post-counters).md` — **v2 WINS over v1** (3 tiers G1, convergence-aware G2, `app-quacq-diag` G3, re-anchored self-checks G4, STALE INPUT gate).
3. `Table-generator ADDENDUM v3 (LaTeX house style, CW Impl).md` — **v3** (how the `.tex` must look; formatting only, does not override v2 data rules).
Also read: `CC prompt - make_tables.py + reproducibility artifact (SUBMISSION).md` (entry), `CW Impl - briefing…` (flow). `CC prompt - Build make_tables.py NOW…` is **SUPERSEDED — ignore**.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Scaffold + IO + stale gate](./phase-01-scaffold-io-stale-gate.md) | Completed |
| 2 | [Filters + aggregation + tiers](./phase-02-filters-aggregation-tiers.md) | Completed |
| 3 | [Emit 10 tables + LaTeX style](./phase-03-emit-10-tables-latex-style.md) | Completed |
| 4 | [Self-checks + anchors + tests](./phase-04-self-checks-anchors-tests.md) | Completed |

Order 1→2→3→4 (each builds on the prior). Build + unit-test now; final tables regenerate after Viet-Man's sweep + `--merge`.

## Key spec rules digest (authoritative source = v1/v2/v3; this is a map)
- **Strategy→CSV filter (v1):** A=(A, n/a, blank); C=(C, raw, blank); ConMin C∪S=(C∪S, raw, k=1); QuAcq=(QuAcq, n/a, blank); QuAcq-active=(QuAcq-active, n/a, blank).
- **3 tiers (v2 G1), P & R separate:** Desc `desc_{p,r,f1}`, Clause `clause_{p,r,f1}`, Sem `sem_{p,r,f1}`. Never collapse; Desc strict (no alias tolerance). Order Desc→Clause→Sem.
- **Aggregation (v1):** row-level mean over matching rows (each fold equal weight), skip nan — NOT mean-of-per-sampling-means.
- **exclude-2COV** for headline tables (`eval-prf`, `eval-cost`, `app-ksweep`, `app-rawred`, `app-checks`, `app-accuracy`); **keep all 6 samplings** for per-sampling appendix (`app-confusion`, `app-perset`). Default `--exclude-2cov` on.
- **Convergence-aware (v2 G2; partition from CODE — red-team #2):** non-converged = **`aggregate_cv`'s `{timeout, max_queries}` only** (`conmin_cv_evaluator.py`); `pool_exhausted`/`no_query`/`''` stay in the mean. `†` only on `{timeout,max_queries}` cells; budget read from the row (`qa_max_queries`/`qa_timeout_s`), never hardcoded. QuAcq-active std=0 → single value, don't flag.
- **STALE INPUT gate (v2):** run FIRST; refuse silently if any QuAcq row has blank `convergence_reason` or counters absent.
- **Empty-scope gate (v2 G3):** print `quacq_empty_scope_appends` per KB; non-zero on REAL-FM-4/busybox → "precision 1.000" off the table → stop + report CW Impl.
- **Anchors (v2 G4; CW-Main RESOLVED 2026-07-26):** compare pre-round floats, tol `5e-3`; every anchor is the exclude-2COV CV-mean (the table cell). **ABORT-level, pin NOW**: A/C/C∪S all 4 KB (C∪S sem-F1 `0.847/0.782/0.637/0.776`; A `0.605/0.867/0.380/0.642`); QuAcq example-only all 4 KB (RE7 `0.133/0.006/0.012` — NOT the single-fold `1.000/0.045/0.087`, NOT rs_1n `0.667/0.030/0.058`); QuAcq-active RE7 sem `1.000/0.727/0.842` desc `0.250/0.231/0.240` |KB| `12` `272`q; QuAcq-active fqa (max_queries cap); **QuAcq-active arcade NOW pinnable** sem `1.000/0.292/0.452` desc-F1 `0.495` (daggered `max_queries`, 5000q — verified through the modules). **DO NOT pin yet**: QuAcq-active RE4 + busybox (both tonight → deterministic `max_queries`). desc headline = **0.682** (excl-2COV), not 0.699. **"ConMin 2.8× desc" claim WITHDRAWN — per-KB, no universal multiplier** (arcade QuAcq-active *wins* desc 0.495 vs C∪S 0.405); table bolding must compute per-row max, no ratio column. Never fix an anchor to match output; DELETE 0.667-era on sight. (See Phase 4 anchor table + Phase 3 content constraints.)
- **Rounding (v1):** rates/F1/P/R/acc/spec/exact → 2dp (trailing zeros); sizes |A|/|C|/|S|/|KB|/|U| → 1dp; checks → int `{,}`; runtime `total_ms`/1000 → 1dp; queries → 1dp.
- **LaTeX (v3):** `table[t]`/`table*[t]`, `\centering \small`, booktabs only (`\toprule/\midrule/\bottomrule`, no `\hline`/vrules), `\tabularnewline`, `\multicolumn`+`\cmidrule(lr)` super-cols, `\multirow` tier bands, `$x^{\dagger}$`, reuse macros (`\KB`,`\supp`,`\BG`,`\NE`,`\CS`), `\textsc{}` names, NO new packages / `threeparttable` / `\resizebox` / `siunitx`, complete float per table, caption+label after `tabular`.
- KB order fixed: `KB₁..KB₅` = REAL-FM-7, fqa, arcade-game, REAL-FM-4, busybox-1.18.0.

## Grounding (verified 2026-07-26)
- **All spec-referenced columns exist** in `REAL-FM-7_long.csv` (`sem_*`, `desc_*`, `clause_*`, `accuracy`, `specificity`, `exact_equiv`, `n_mss/n_cover/n_support/n_kb/n_uncoverable/n_bias`, `stage1_batch_checks`, `total_ms`, `oracle_queries`, `preprocessing_checks`, `tp/tn/fp/fn`, `checks_{gate,admpool,cover_rej,cover_qx,redundancy,total}`, `convergence_reason`, `qa_max_queries`, `qa_timeout_s`, `quacq_{bandaid_drops,findc_unconfirmed,empty_scope_appends,prune_partial_pruned,prune_complete_pruned}`). **Zero missing** → spec column map is trustworthy.
- **CORRECTED (red-team #13):** per-KB `_long.csv` = **61 cols** (all 5 conditions, fresh); merged `conmin_eval_long.csv` = **56 cols, 4-condition (stale)**. The delta = the **5 `quacq_*` counter columns** (merged is a strict subset lacking them + QuAcq-active + carrying blank `convergence_reason`) — THAT is why we **prefer per-KB**, not a col-count gap. (Earlier "235 cols" was a Bash-output-truncation misread.)
- Conditions present in `REAL-FM-7_long.csv`: A, C, C∪S, QuAcq, QuAcq-active. `convergence_reason` vocabulary = `{pool_exhausted (passive QuAcq, all KBs), no_query (QuAcq-active REAL-FM-7), max_queries (QuAcq-active fqa + arcade post-rerun), timeout (QuAcq-active REAL-FM-4, until tonight's rerun), '' (A/C/C∪S)}`.

## Guardrails
- **Additive**; do not alter A/C/C∪S/ConMin/QuAcq paths or `data/results/interactive/`. `PYTHONPATH=. pytest tests/ -q` green.
- **Concurrency (sweep running):** never write `data/results_conmin/*.json`; never run eval into the default output dir; smoke tables → `/tmp/...`. **Official** tables → `data/results_conmin/tables/` only after the sweep + `--merge` (mid-sweep tables are throwaway).
- **No fabricated numbers**; `--` derived from row-presence per cell (busybox's infeasible rs_2n/rs_3n/rs_m per-sampling cells stay `--`; but busybox **QuAcq-active gets a number tonight** — NOT a blanket `--`). Non-converged → `†`-marked value, not `--`.
- **Do NOT edit anything under `Overleaf/`** — read-only for macro defs during the compile-check.

## Dependencies
- **Blocks** `plans/260726-1243-aaai-repro-artifact/` Phase 3 (reproduce script chains into `make_tables`).
- **Data freshness:** builds + unit-tests NOW against fresh per-KB CSVs (REAL-FM-7/fqa/arcade-game fresh; REAL-FM-4 far along — one reviewer already saw it ~complete; busybox absent → `--`). Coverage is a **moving snapshot while the sweep runs** — the generator derives `--` from row-presence, NOT from any hardcoded coverage number (red-team #12). Final audited tables + metric-anchor capture regenerate after the full sweep + `--merge`.
- **Audit gate:** nothing reaches the paper until CW Main's independent cell-sample audit passes (CW Impl smoke-tests first).

## Acceptance criteria
- [ ] `python -m apps.make_tables` runs; emits all 10 tables (`.tex`+`.md`) + `exact-equiv.md` + `PROVENANCE.md` to `data/results_conmin/tables/`.
- [ ] STALE INPUT + empty-scope gates fire correctly; self-check anchors pass; row counts (18 all-6 / 15 exclude-2COV) correct.
- [ ] Convergence grouping + `†` marking correct; QuAcq-active std=0 not flagged; busybox `--`.
- [ ] LaTeX matches house style; ≥1 table compiles in /tmp with no `??`/missing-package.
- [ ] `tests/test_make_tables.py` green; full suite green; A/C/C∪S/ConMin outputs byte-identical.
- [ ] Report to CW Impl: anchors, row counts, file list, `--`/`†` cells, headline dual-aggregation (desc rs_1n vs exclude-2COV), commit SHA.

## Open questions
**RESOLVED by CW Main (2026-07-26, verified on refreshed CSV):**
1. ✅ **Passive-QuAcq anchor = exclude-2COV mean** `0.133/0.006/0.012` (RE7) — abort-level, deterministic (`pool_exhausted`). NOT `1.000/0.045/0.087` (single smoke fold, absent from CSV) or `0.667/0.030/0.058` (rs_1n alone). Never fix an anchor to match output.
2. ✅ **desc headline = 0.682 (exclude-2COV)**, not 0.699 (rs_1n). Principle: every quoted number uses the same aggregation as its table. (See Phase 4 anchor table.)

**For me / CW Impl (recommendations):**
3. **Package vs single file** — spec says `apps/make_tables.py`; Python ~200-line rule + 10 tables ⇒ recommend a package `apps/make_tables/` (`__main__.py` + modules). CLI `python -m apps.make_tables` unchanged. Confirm the file→package deviation is acceptable.
4. **`eval-prf` layout** — banded (KB×tier) vs three `eval-prf-{sem,desc,clause}` files. Recommend emit BOTH; numbers identical.
5. **`\input` path (red-team #11):** generator writes `data/results_conmin/tables/`; paper `\input`s from `paper/tables/`. Emit-relative vs copy-step — confirm the paper's include root.

## Red Team Review

### Session — 2026-07-26
**Findings:** 14 (14 accepted, 0 rejected) — 3 hostile reviewers (Spec-Fidelity Auditor, Numeric Re-derivation Auditor, Failure Mode Analyst), each re-deriving anchors from the real `_long.csv`. **Calibration:** the plan's core filter+aggregation is SOUND — ConMin sem-F1 0.8471→0.85, A 0.6048→0.60, all 6 QuAcq-active anchors reproduce EXACTLY; filter sentinels (`negatives∈{n/a,raw,reduced}`) correct; table inventory + exclude-2COV membership + STALE-gate scoping all match spec.
**Severity:** 2 Critical, 5 High, 5 Medium, 2 Low.

| # | Finding | Sev | Applied To |
|---|---------|-----|------------|
| 1 | Passive-QuAcq anchor `1.000/0.045/0.087` is a single fold, not the excl-2COV CV-mean (`≈0.13/0.01/0.01`) the generator emits; live sweep rewrites it → abort-on-miss false-aborts fresh data | Critical | Completed |
| 2 | Convergence vocabulary wrong (`pool_exhausted/no_query/max_queries/timeout`, no "converged"); non-converged = `aggregate_cv{timeout,max_queries}`; `†`+budget mis-specified | Critical | Completed |
| 3 | Anchor precision 3dp vs render 2dp → self-check undefined | High | Completed |
| 4 | desc headline 0.699 (rs_1n) ≠ eval-prf cell 0.68 (excl-2COV); no anchor | High | Completed |
| 5 | `_long.csv` written non-atomically (run_conmin_eval.py:44) → torn read of in-flight KB | High | P1 (mtime-snapshot + copy-then-parse loader) |
| 6 | Short row-count only warns → partial KB emits final-looking cells | High | P4 (block / force `--` on short) |
| 7 | STALE/empty-scope gates global-abort → one bad KB denies fresh KBs | High | P1 (per-KB gate) |
| 8 | 18/15 invalid for app-ksweep(60)/app-rawred(30); app-rawred "0 vs N" wrong | Medium | P3, P4 (per-table counts) |
| 9 | app-quacq-diag exclude-2COV vs all-6 unspecified → drops 2cov from fairness | Medium | P3 (all-6) |
| 10 | Default `--tables-dir`=production dir → bare invocation writes canonical mid-sweep | Medium | P1 (throwaway default + `--official`) |
| 11 | Compile-check macros only in vault; pdflatex IS present; `\input` path mismatch | Medium | P3, P4 (vault preamble, fail-not-lint) |
| 12 | REAL-FM-4 hardcoded "partial" already stale (~complete) | Medium | P1/P4 (derive `--` from rows) |
| 13 | Grounding "235 cols" false → 61 (Bash-truncation misread) | Low | plan §Grounding (61; delta=5 counters) |
| 14 | k-filter "treat blank as any" wrong | Low | P2 (`k==''` exact) |

### Whole-Plan Consistency Sweep
Re-read plan.md + all 4 phase files after applying. Reconciled: convergence partition unified to `aggregate_cv{timeout,max_queries}` across P2/P3/plan; anchor abort-tiering consistent (Stage-1+QuAcq-active abort / passive-QuAcq+desc warn) in P4 + plan §Anchors; "235 cols" purged (→61) in plan + P1; row-count expectations per-table in P3+P4; default `--tables-dir` throwaway in P1 matches the smoke-run note in P4; REAL-FM-4 "partial" removed from P1/P4. **Unresolved contradictions: none.** Remaining external items: CW-Main rulings (#1 anchor, #4 desc headline), the live sweep still rewriting passive-QuAcq numbers, and the `\input` include-root — all tracked as Open questions / Dependencies.
