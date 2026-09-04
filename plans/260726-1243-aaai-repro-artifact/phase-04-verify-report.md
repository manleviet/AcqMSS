---
phase: 4
title: "Verify & Report"
status: pending
effort: "~1h"
priority: P1
dependencies: [1, 2, 3]
---

# Phase 4: Verify additive-only + reproduce script, compute desc dual-aggregation, report to CW Impl

## Overview
Prove the change is additive (no learner behaviour change), the suite is green, the reproduce script runs its guarded path, and deliver the desc dual-aggregation numbers (note b) + the empty-scope gate status to CW Impl.

## Requirements
- Read-only verification; **do NOT run the 5-KB sweep**; all scratch to `/tmp`.
- No committed `data/results_conmin/*.json` written.

## Verification steps

### V1 — Additive-only proof (guardrail: outputs byte-identical)
- `git diff --stat feat/conmin` shows ONLY additive files: `docs/eval-pipeline.md`, `README.md`, `pyproject.toml` (comment), `scripts/reproduce_paper.sh`, `scripts/diff_logical_cols.py`, `.gitignore`, `vendor/explanation-0.1.0-py3-none-any.whl`, `vendor/README.md`, `plans/…`. **Zero** behavioural `.py` under `conacq/` or `apps/`.
- State the proof as: byte-identical by construction — no learner/runner source edited. (No fragile diff against possibly-stale committed JSONs; RUN.md flags REAL-FM-7 JSONs as pre-fix schema.)
- Note: the vendored wheel is a build artifact of `explanation@v0.1.0`, not an AcqMSS learner change.

### V2 — Suite green
- `PYTHONPATH=. pytest tests/ -q` → green, count unchanged (no test touched).

### V3 — Reproduce script smoke (guarded path, light)
- `bash -n scripts/reproduce_paper.sh` + `bash -n scripts/diff_logical_cols.py`-equivalent import check (syntax).
- **Refuse-guard**: `bash scripts/reproduce_paper.sh data/results_conmin` exits non-zero and writes nothing (Red Team #5).
- Run env-check block + `python -m apps.run_conmin_eval $CFG --kb REAL-FM-7 --example-sets rs_1n -o /tmp/repro_check` (light) → pipeline executes.
- `--merge -o /tmp/repro_check` produces `conmin_eval_{long,cv}.csv` there. (Code already confirms merge honors `-o`: run_conmin_eval.py:158 read, :114-115 write — this smoke just double-checks end-to-end.)
- make_tables guard **skips** cleanly (module absent today) AND degrades on non-zero invocation (Red Team #6).
- Resume: a second identical run skips the completed KB (Red Team #7).
- Diff step warns-and-skips when `data/results_conmin/reference/conmin_eval_cv.csv` is absent (Red Team #2).

### V4 — desc dual-aggregation (note b, read-only) — GATED on the fresh post-sweep CSVs
**Blocker (Red Team #4):** the CURRENT `conmin_eval_{cv,long}.csv` are untracked + stale + carry only 4 conditions (**no QuAcq-active**); QuAcq-active per-KB JSONs exist today only for REAL-FM-7 + fqa (arcade/REAL-FM-4/busybox = 0). So V4 is **not** computable against current artifacts. Run it against **Viet-Man's fresh post-`afaa04b` full-sweep** merged CSVs (5 conditions, all KBs).

Then compute `desc` (description-strategy) P/R/F1 for ConMin **C∪S** and **QuAcq-active** under BOTH aggregations — **pinning the `k` and `negatives` selectors** the paper table uses (Red Team #7: `desc_f1` for C∪S/rs_1n swings 0.699@k=1 → 0.297@k=5, so an unpinned "rs_1n desc" is ambiguous):
  - **rs_1n alone** at the paper's `(k, negatives)` — the source of CW-Impl's headline (C∪S 0.699 vs QuAcq-active 0.240; that pair is REAL-FM-7/rs_1n/k=1).
  - **mean excluding 2COV** across KBs at the same `(k, negatives)`, honoring `aggregate_cv` convergence exclusion (drop non-converged QuAcq-active folds; busybox QuAcq-active likely `--`).
- Report both pairs **with the selector named** so the paper headline cites the SAME aggregation as its table. Where QuAcq-active is absent/non-converged for a KB, report `--` honestly (no fabrication). Anchor: v2's KB₁ sem-F1 0.85 shows the semantic side stable; this closes the untested-desc gap.
- Read-only (pandas/csv); no writes to committed data. Columns confirmed present: `desc_p/desc_r/desc_f1` (long), `desc_{p,r,f1}_{mean,std}` (cv); rows keyed by `(kb, example_set, negatives, condition, k)`.

### V5 — empty-scope precision gate (CW-Impl note)
- Check `quacq_empty_scope_appends` on REAL-FM-4 + busybox rows.
- **Known state (research):** the current (untracked) merged CSV predates the diag counters (`afaa04b`); the counter column is **absent** (`--`, not `0`) → the gate **cannot** be evaluated from the current artifacts.
- Report: gate is evaluable only against Viet-Man's fresh **post-`afaa04b`** sweep. If non-zero there on REAL-FM-4/busybox, the sweep-wide "precision 1.000" claim is off the table → escalate to CW Impl. Flag as an open item, do not block this doc/script plan.

## Report to CW Impl (deliverable)
Write `plans/reports/from-planner-to-cw-impl-260726-repro-artifact-report.md` with:
1. Doc diff summary (Phase 1 section added; Phase 2 pin lines).
2. Pinned `explanation`: **wheel** `vendor/explanation-0.1.0-py3-none-any.whl` (sha256) built from `v0.1.0`/`9d63a63…`; **verification method** (`pip show` + `rev-list v0.1.0 == rev-parse HEAD`); **flag**: repo is PRIVATE → wheel is the external-reviewer path (git+SHA is maintainer-only). Confirm fresh-venv install works without repo access.
3. `reproduce_paper.sh` usage (`bash scripts/reproduce_paper.sh [OUT_DIR]`) + refuse-guard / resume / completeness-assert / make_tables-degrade / logical-diff behaviour.
4. Suite status (pass count).
5. **desc dual-aggregation numbers** (rs_1n-alone@pinned-`(k,neg)` vs mean-exclude-2COV) for the C∪S/QuAcq-active desc pair — **from the fresh post-sweep CSVs** (state the `(k, negatives)` selector). If run before the sweep: report "pending fresh sweep — current CSVs lack QuAcq-active for 3/5 KBs".
6. empty-scope gate status (`quacq_empty_scope_appends` absent in current committed CSVs → evaluate on the fresh post-`afaa04b` sweep; if non-zero on REAL-FM-4/busybox, "precision 1.000" is off the table).
7. **Frozen-reference prerequisite**: `data/results_conmin/reference/conmin_eval_cv.csv` must be committed from the fresh sweep to enable the reproduction diff.
8. Commit SHA of the additive commit.

## Success Criteria
- [ ] `git diff --stat` confirms additive-only (only the additive files in V1; no behavioural `.py`).
- [ ] `pytest -q` green, unchanged count.
- [ ] Script smoke passes; refuse-guard + resume + make_tables-degrade + diff-skip verified; `-o` honored by eval + merge.
- [ ] Wheel installs in a fresh venv without private-repo access; version 0.1.0.
- [ ] desc numbers computed under both aggregations **with `(k,negatives)` selector named**, from the fresh post-sweep CSVs (or honestly reported "pending fresh sweep" / `--` where QuAcq-active absent).
- [ ] Report delivered to `plans/reports/`; commit SHA recorded.

## Risk Assessment
- Risk: V4/V5/diff all depend on Viet-Man's fresh post-sweep CSVs (current ones stale, 4-condition). Mitigation: gate those steps; deliver doc+script+wheel (Phases 1-3) independently; run V4/V5 + freeze the reference after the sweep.
- Risk: QuAcq-active absent for some KBs even post-sweep (busybox timeout → non-converged). Mitigation: report `--` per the convention; mean-exclude-2COV honors `aggregate_cv` convergence exclusion.
- Risk: `-o` merge behaviour. RESOLVED — code confirms merge honors `-o` (run_conmin_eval.py:158,114-115); V3 double-checks end-to-end.
