---
title: Add fair active-QuAcq eval condition (oracle mode)
description: >-
  Add a 5th ConMin-eval condition (QuAcq-active) that runs QuAcq in
  oracle/automated mode, self-generating membership queries to the FM oracle,
  with max_queries + wall-clock rails; keep the crippled example-only QuAcq row
  alongside it. GATED: validate the premise on a mid-size KB before any timed
  sweep.
status: completed
priority: P2
branch: feat/conmin
tags:
  - conmin
  - eval
  - quacq
  - oracle
blockedBy: []
blocks: []
created: '2026-07-24T16:47:02.092Z'
createdBy: 'ck:plan'
source: skill
redTeam: '2026-07-24 — 15 findings (4C/7H/4M), all applied'
---

# Add fair active-QuAcq eval condition (oracle mode)

## Overview

The ConMin comparison eval currently runs QuAcq as a **crippled passive baseline**:
`_eval_quacq_fold` (`conacq/eval/conmin_cv_evaluator.py:226`) builds
`QuAcqRunner(bias, fm, solver, use_incremental=…)` (default `query_mode='example_only'`)
and calls `runner.run(tr_pos, tr_neg)`, so QuAcq only consumes the fixed fold examples and
never queries the oracle → near-empty theory (0.4–1.4 constraints, sem-F1 0.01–0.07). A
reviewer calls that a strawman.

This plan **adds** a fair active condition `condition='QuAcq-active'` that runs the runner's
already-existing oracle path (`run(mode='automated')` → `_run_oracle_mode`, using
`QueryProvider` + `DiscriminatingGenerator` + the FM oracle). The existing example-only rows
stay as `condition='QuAcq'` — **both columns side by side**. Additive: A / C / C∪S / ConMin
acquisition paths are not touched (their numbers stay value-identical).

> **⚠ Red-team gate (C-1): the premise is contested by our own paper.** `paper/evaluation.tex:318`
> shows the *example-first* mode already does SAT-based query generation (the same
> `generate_from_sat`/`DiscriminatingGenerator` path this plan uses) and still caps at
> semantic-F1 **≤ 0.105** (`:374-378`), attributed to a **structural** cause — one-at-a-time
> learning + the `Reduce` KB-compression step (`quacq.py:249-255`), *not* query starvation
> (`:387,:438`). So oracle-mode may **not** clear the strawman band. **Do not commit the timed
> 5-KB sweep until Phase 4's go/no-go smoke (REAL-FM-7 + one mid-size KB, untimed) confirms a
> material sem-F1 uplift over the paper's example-first numbers.** If it doesn't, QuAcq-active
> is an *informational* row (a documented fairness caveat), not a "fixed strawman."

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Timeout Rail](./phase-01-timeout-rail.md) — net-new wall-clock guard + deterministic `max_queries` cap in `QuAcq.learn` / `QuAcqRunner` | Completed |
| 2 | [QuAcq-Active Condition](./phase-02-quacq-active-condition.md) — oracle-mode learn (learn-once-per-KB) + scoring + provenance + non-converged handling | Completed |
| 3 | [Config & CLI Wiring](./phase-03-config-cli-wiring.md) — per-KB learn hook, provenance in JSON, `--merge` additive-column tolerance | Completed |
| 4 | [Test Smoke & Report](./phase-04-test-smoke-report.md) — **go/no-go gate**, suite green, non-destructive smoke, feasibility, report to CW Impl | Completed |

## Locked decisions (from prompt + CW Impl mid-turn confirmation)

- **Keep BOTH.** `QuAcq` (example-only) rows unchanged; add `QuAcq-active` (oracle) as a 5th
  condition. Same output dir `data/results_conmin/` (never `data/results/interactive/`).
- **Oracle path.** `QuAcqRunner(..., query_mode='automated', max_queries=…, timeout_s=…)` →
  `runner.run(mode='automated')`. Verify `QueryProvider` + `DiscriminatingGenerator` exercised.
- **Rails.** `max_queries` (primary, **deterministic**) **and** a wall-clock `timeout_s≈400 s`
  (safety net only — see C-4). Record `convergence_reason ∈ {empty_bias, no_query, max_queries,
  timeout}`.
- **`stage1_batch_checks` blank** for QuAcq-active; cost = `oracle_queries` + `runtime_ms`/`total_ms`.
- **CC builds + smoke-tests only** (untimed → safe now). **Viet-Man runs the timed sweep** on
  the quiet Apple M1 Pro (8-core, 16 GB), after busybox, not in parallel.

## Committed decisions (were "recommended-with-alternative" — closed per red-team H-6, H-5, C-9)

1. **Learn-once-per-KB (H-6/C-6).** Oracle mode is example-independent and `model.bias`/`model.oracle`
   are per-KB (`run_conmin_eval.py:143`), so the theory is byte-identical across all 6 example-sets.
   → Learn **once per KB in the apps layer** (`run_conmin_eval.py` es-loop), pass the result into
   every `evaluate_kb_example(...)` call. Kills the 6×-redundant per-(KB,es) recompute. Per-fold
   clone is the audit-simplicity fallback only. (NB: under a timeout, "byte-identical across es"
   holds only if the same budget/timeout is used for the whole KB — enforced by provenance, C-4.)
2. **Uniform `convergence_reason` column + `--merge` tolerance (H-5).** Add it (default `''`) on
   every scored row via `_score_row`/`_cost` **and** make `_merge_per_kb` union-and-blank-fill
   columns before its schema check, so the **24–26 already-committed pre-column `*_eval.json`**
   don't trip the "re-run affected KB(s)" warning. Wording: existing rows are **value-identical
   plus one additive column**, *not* byte-identical (H-1/A-2) — corrected everywhere.

## Threats to validity — escalate to CW Main (paper-policy owner)

These are experiment-design calls, not mechanism bugs; the plan surfaces them, CW Main decides:

- **C-1 Premise:** paper's example-first already SAT-generates and caps ≤0.105 for a structural
  reason → oracle-mode may not beat the strawman. Reconcile in any paper text.
- **C-2 Budget asymmetry:** ~6 fixed training examples (ConMin, 0 adaptive queries) vs a
  ≥5000 adaptive-query budget (QuAcq-active). Report on the **cost axis** (`oracle_queries` =
  "the scarce cost"); optionally add a budget-parity variant (queries ≈ #training examples).
- **C-3 Oracle = grader:** QuAcq-active adaptively queries `FMOracle(fm)`, then is scored against
  ground truth from the *same* FM. Not held-out generalization. Prefer reporting **semantic-F1
  only** (structural) and dropping the accuracy side-by-side; caveat explicitly.
- **Core tension (C-2 ↔ C-4/H-4):** a *fair active* baseline needs enough queries to converge
  **deterministically**, which *widens* the cost gap vs the passive learners. Picking the budget
  is the central decision.

## Acceptance criteria

- **Go/no-go gate first (C-1/H-2):** on REAL-FM-7 **and** one mid-size KB (fqa/arcade, untimed),
  oracle-mode sem-F1 is **materially higher** than example-only *and* clears the paper's
  example-first band (≤0.105) — with a concrete pre-registered threshold. Only then is the sweep
  authorized. `oracle_queries` and `convergence_reason` recorded.
- Output columns effectively unchanged (one additive `convergence_reason` + provenance columns);
  rows in `data/results_conmin/`; A/C/C∪S/QuAcq rows **value-identical**; ConGen/ConMin
  acquisition outputs byte-identical.
- Rails present so large KBs terminate; busybox reaches `empty_bias`/`no_query` (not
  `max_queries`/`timeout`) at the chosen budget, **or** is reported "did not converge" — never
  averaged into the CV mean as if converged (H-3).
- Provenance (`max_queries`, `timeout_s`) recorded per QuAcq-active row + JSON; `--merge` refuses
  to blend rows with differing provenance (C-4).
- QuAcq-active **structural** metrics (sem/desc/clause P/R/F1, exact_equiv) reported as a **single
  fold-independent value**, not a `mean±0.000` CV (H-1); only accuracy/tp/tn/fp/fn/specificity
  vary by fold.
- `PYTHONPATH=. pytest tests/ -q` green (incl. `test_quacq.py`, `test_conmin.py`, boundary/metrics).
- Report: exact invocation, gate numbers (example-only vs example-first-band vs oracle-mode:
  sem-F1, `oracle_queries`, `convergence_reason`), value-identical confirmation, per-KB feasibility.

## Dependencies

- Runs on `feat/conmin` (tip `b98d7c6`). No cross-plan blockers (`260721-conmin-impl/` is the
  parent; this is an additive follow-on).
- External: `../explanation` editable; `data/folds/`+`data/examples/`+`data/bias/`+`data/fms/` present.

## Red Team Review

### Session — 2026-07-24
**Findings:** 15 (15 accepted, 0 rejected) — all `file:line`-backed; dedup of 24 raw.
**Severity breakdown:** 4 Critical, 7 High, 4 Medium.
Full adjudication: `reports/from-code-reviewer-to-planner-red-team-adjudication-quacq-active-oracle-eval-report.md`

| # | Finding | Sev | Disp | Applied To |
|---|---------|-----|------|------------|
| C-1 | Premise contradicted by paper example-first (≤0.105, structural cap) | Critical | Accept | plan.md gate, Phase 4 go/no-go |
| C-2 | Budget asymmetry (~6 examples vs 5000 queries), no cost parity | Critical | Accept | plan.md Threats → CW Main |
| C-3 | Oracle QuAcq queries IS the grader (construct validity) | Critical | Accept | plan.md Threats → CW Main |
| C-4 | Timeout truncation → non-reproducible busybox; no provenance | Critical | Accept | Phase 1, 2, 3 |
| H-1 | Fake CV: sem-F1 std≡0; plan misstated which metrics vary | High | Accept | Phase 2, plan.md acceptance |
| H-2 | No empirical evidence; acceptance only on smallest KB | High | Accept | Phase 4 gate |
| H-3 | Timeout/max_queries partial rows averaged as converged | High | Accept | Phase 2 (aggregate_cv) |
| H-4 | max_queries=5000 < |B|=6635, shared counter → still crippled | High | Accept | Phase 1, 3 (per-KB budget) |
| H-5 | Uniform column vs 24–26 committed JSONs breaks `--merge` | High | Accept | Phase 2, 3 (merge tolerance) |
| H-6 | Per-(KB,es) hoist re-learns 6× per KB (wrong cut) | High | Accept | Phase 2, 3 (learn-once-per-KB) |
| H-7 | Cleanup-on-exception not pinned → leaked solvers | High | Accept | Phase 2 (try/finally step) |
| M-1 | "FindScope O(log|vars|)" false; soft ceiling understated | Medium | Accept | Phase 1, 4 |
| M-2 | Example-only convergence_reason blanked (loses diagnostic) | Medium | Accept | Phase 2 |
| M-3 | "No shared mutable state" inaccurate; 2 live oracles | Medium | Accept | Phase 2 |
| M-4 | Smoke overwrites committed baseline | Medium | Accept | Phase 4 (-o /tmp) |

### Whole-Plan Consistency Sweep — 2026-07-24 (zero unresolved contradictions)
Re-read `plan.md` + all 4 phase files after applying the 15 findings; grep-swept stale terms.
- **"byte-identical" reconciled**: now used *only* for (a) ConGen/ConMin **acquisition output**
  and (b) the QuAcq-active **theory** being identical across folds/es (both correct). All
  **eval-CSV-row** claims changed to **value-identical + additive columns** (H-1/A-2). Negations
  ("NOT byte-identical") verified correct.
- **Hoist wording purged**: no residual "6 learns" / "3× cheaper" / "per-(KB,es) recommended
  structure" / "per-fold re-learning" — replaced by committed **learn-once-per-KB** (H-6).
  `active_res` threading consistent: Phase 2 *receives*, Phase 3 *supplies* once per KB.
- **Corrected claims** carry their finding tags and appear only in corrected context:
  "FindScope O(log)" (M-1), "no shared mutable state" (M-3), "single-schema ⇒ no merge warning"
  (H-5), "sem-metrics vary with test set" (H-1). Old assertions removed, not merely appended.
- **"four conditions"** survives only as *instructions to update* the code docstring (Phase 2)
  and `RUN.md` (Phase 3) — not as stale plan claims.
- **Provenance naming** uniform (`qa_max_queries`/`qa_timeout_s` columns; `quacq_active_*` config);
  gate threshold cross-referenced across plan.md / Phase 2 / Phase 4; dependency chain 1→2→3→4 intact.

**Result:** no unresolved contradictions. NOTE — the plan is internally consistent, but it is
**gated, not green-lit**: the C-1 premise (paper's example-first caps ≤0.105 for a structural
reason) means Phase 4's go/no-go must pass on a mid-size KB before the timed sweep, and C-1/C-2/C-3
are paper-policy calls for CW Main. Implementation of Phases 1–3 + the untimed gate can proceed;
the timed 5-KB sweep cannot until the gate passes.
