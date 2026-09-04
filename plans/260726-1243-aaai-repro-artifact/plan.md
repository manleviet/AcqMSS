---
title: "ConMin/AAAI reproducibility artifact (3 gaps)"
description: "Close 3 reproducibility gaps for the AAAI submission — document the ConMin eval chain, pin ../explanation, add a one-command reproduce entry point. Additive-only; no learner behaviour change."
status: pending
priority: P1
branch: "feat/conmin"
tags: [conmin, reproducibility, docs, aaai, eval-pipeline]
blockedBy: [260726-1341-make-tables-generator]
blocks: []
created: "2026-07-26T10:51:24.511Z"
createdBy: "ck:plan"
source: skill
---

# ConMin/AAAI reproducibility artifact (3 gaps)

## Overview

Close the 3 reproducibility gaps CW-Impl identified for the AAAI submission (due **2026-07-28**). **Additive only** — docs + one new shell script; **zero** learner/runner code change (A/C/C∪S/ConMin/ConGen/QuAcq outputs unchanged **by construction** — no `*.py` under `conacq/`/`apps/` is touched behaviourally).

> **CORRECTION (2026-07-26, CW-Impl):** `apps/make_tables.py` is **MY deliverable**, not out of scope. CW Main *authors* the spec (`prompts/…v1`+`v2`+`v3`, in Viet-Man's Obsidian vault, NOT the repo) and *independently audits* the output; **I implement it.** It is the **critical path** — the paper's Evaluation section is blocked on the tables — so it is built **first**, tracked in the sibling plan **`plans/260726-1341-make-tables-generator/`**. This repro plan's Phase 3 (reproduce script) chains into it.

**Not redone** (CW-Impl audit 2026-07-26, re-verified here): 4 data-prep scripts exist; every input for all 5 KBs committed (regenerates nothing); `seed=82` + `solver_name="glucose4"` pinned in `run_conmin_eval_config.toml`; hash-seed independent (`3654c2b`/`b40771c`); `data/results_conmin/RUN.md` tracked.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Doc ConMin Chain](./phase-01-doc-conmin-chain.md) | Pending |
| 2 | [Pin Explanation](./phase-02-pin-explanation.md) | Pending |
| 3 | [Reproduce Script](./phase-03-reproduce-script.md) | Pending |
| 4 | [Verify & Report](./phase-04-verify-report.md) | Pending |

Phases 1–3 have no ordering constraint among themselves (disjoint files); Phase 4 runs last (verifies + reports the union).

### Revised cook order (2026-07-26, CW-Impl directive)
1. **`make_tables` sibling plan FIRST** (critical path — Evaluation section blocked). See `plans/260726-1341-make-tables-generator/`.
2. **Cook repro Phase 1 (doc) + Phase 2 (wheel pin)** — the wheel pin feeds `ReproducibilityChecklist.tex` directly, so it's paper-facing.
3. **Defer repro Phase 3 (reproduce script) + Phase 4 (verify/report)** — Phase 3's real `make_tables` call lands once the sibling plan ships; Phase 4's V4/V5 gate on the fresh sweep anyway.

## Locked decisions (planning interview + red-team, 2026-07-26)

1. **make_tables gap** → reproduce script **guards AND wraps** the table step: runs only if `apps.make_tables` importable, and wraps the call in `|| skip-message` so a present-but-different CLI degrades instead of `set -e`-aborting after the sweep (red-team #6).
2. **Repro output** → default `OUT=data/results_conmin/repro/` (gitignored), overridable `$1`, with a **hard refuse-guard** rejecting any `OUT` that resolves to the canonical `data/results_conmin` (red-team #5). Reproduction proof = **logical-column diff vs a committed frozen reference** `data/results_conmin/reference/conmin_eval_cv.csv` (NOT a raw diff of the untracked/stale CSV, red-team #2).
3. **desc note (b)** → **in scope**, but gated on the **fresh post-sweep** CSVs (current ones lack QuAcq-active) and with the `(k, negatives)` selector pinned (red-team #4/#7). Read-only; reports both aggregations to CW Impl.
4. **explanation pin (red-team #1)** → repo is PRIVATE → primary reproducer install = **committed wheel** `vendor/explanation-0.1.0-py3-none-any.whl` (built from `v0.1.0`/`9d63a63…`); git+**SHA** is a maintainer-only secondary path.

## Acceptance criteria

- [ ] `docs/eval-pipeline.md` covers the ConMin/AAAI chain end-to-end (committed inputs → `run_conmin_eval --conditions …` → `--merge` → `make_tables`) incl. the 5 knobs, the "pre-recorded folds/examples — never regenerate" rule, "deterministic without `PYTHONHASHSEED`", and glucose4-as-reported-solver caveat.
- [ ] `../explanation` pinned as a committed wheel `vendor/explanation-0.1.0-py3-none-any.whl` (sha256 recorded) referenced from `README.md` **and** `docs/eval-pipeline.md`; installs in a fresh venv **without** private-repo access; pin verified against the **installed** package (not guessed).
- [ ] `scripts/reproduce_paper.sh` exists, is executable, chains env-check → 5-KB eval → `--merge` → (guarded) `make_tables`; carries hardware note + busybox caveat; clobber-safe default output.
- [ ] `PYTHONPATH=. pytest tests/ -q` green (unchanged count — no test touched).
- [ ] Additive-only proven: `git diff --stat` shows only docs, README, pyproject (comment), `scripts/reproduce_paper.sh` — no behavioural `.py` edit.
- [ ] Report to CW Impl: doc diff, pinned tag/SHA + verification method, script usage, suite status, desc dual-aggregation numbers, commit SHA.

## Dependencies

- **Sibling plan (my deliverable, critical path):** `apps/make_tables.py` — spec authored by CW Main (`prompts/…v1`+`v2`+`v3`, in Viet-Man's vault; CW Main *audits*, I *implement*). Tracked in `plans/260726-1341-make-tables-generator/`. Repro **Phase 3's** real (non-guarded) table step depends on it landing; Phase 3 keeps the guard-and-wrap so the script works in the interim. `prompts/` is NOT in the repo — it's at `/Users/manleviet/Library/Mobile Documents/iCloud~md~obsidian/Documents/Everything/Cowork/AcqMSS/prompts/`.
- **Sequencing (Viet-Man's fresh sweep):** Phase-4 V4 (desc dual-aggregation), V5 (empty-scope gate), and the reproduce-script diff reference all require the **fresh post-`afaa04b` full-sweep** merged CSVs (current ones are stale/4-condition). Phases 1–3 (doc + wheel + script) ship independently; V4/V5 + freezing `data/results_conmin/reference/conmin_eval_cv.csv` run after the sweep.
- **External decision:** publishing `manleviet/explanation` (there's a `plans/260719-2201-GH-0-publish-explanation-to-consumers/` in that repo). This plan does NOT block on it — it ships the wheel so reproduction works whether or not the repo goes public.
- **Related (soft):** `plans/260721-conmin-impl/` (parent) and completed `plans/260724-1841-quacq-active-oracle-eval/` (the QuAcq-active condition). No hard `blockedBy`/`blocks` edge — additive downstream documentation.

## Guardrails (apply to every phase)

- Additive only; **no behaviour change to any learner**. Bias files untouched.
- **Do NOT run the 5-KB sweep** (Viet-Man's quiet-machine run). All verification uses `-o /tmp/...` scratch; **never** write committed `data/results_conmin/*.json` or the default output dir.
- No fabricated numbers; missing cells are `--` (never `0`).

## Verified facts (research, 2026-07-26)

| Fact | Value | Source |
|---|---|---|
| explanation version | `0.1.0` | `pip show explanation` |
| explanation tag == HEAD | `v0.1.0` == `9d63a6382856bc513b49773e9b647951ba68075e` | `git -C ../explanation rev-list -n1 v0.1.0` == `rev-parse HEAD` |
| explanation remote | `https://github.com/manleviet/explanation.git` | `git -C ../explanation remote -v` |
| flamapy pin (in explanation) | `flamapy-{fw,fm,sat}==2.6.0.dev4` | `../explanation/pyproject.toml` |
| eval app | `apps/run_conmin_eval.py` (19.5K) | `ls apps/` |
| eval config | `apps/conf_conmin/run_conmin_eval_config.toml` | `find` |
| merge outputs | `conmin_eval_long.csv` + `conmin_eval_cv.csv` — **untracked + stale + 4-condition** (no QuAcq-active); regenerated by `--merge`, NOT a committed baseline | `git ls-files` (not tracked); merged-CSV condition list (red-team) |
| explanation repo visibility | **PRIVATE** → `git+https` install fails externally | `gh api repos/manleviet/explanation` → `private:true` |
| QuAcq-active coverage (sweep running, ~13:31) | REAL-FM-7 6/6, fqa 6/6, arcade-game 6/6, REAL-FM-4 **3/6 (running)**, busybox 0 | CW-Impl 2026-07-26 (line-75 12:43 snapshot superseded) |
| CLI flags | `-o/--output-dir --kb --merge --example-sets --k --negatives --no-quacq-active --quacq-active-timeout --quacq-active-max-queries --conditions --non-incremental --debug -v` | `apps/run_conmin_eval.py:126-147` |
| busybox committed sets | `2cov`, `ff`, `rs_1n` only (rs_2n/3n/m absent → infeasible) | `ls data/results_conmin/busybox*` |
| `make_tables.py` | **absent → MY deliverable to build** (sibling plan) | `find . -iname '*make_tables*'` |
| `prompts/` spec | in **vault**, not repo: `…/Cowork/AcqMSS/prompts/` (v1+v2+v3 read 2026-07-26) | added working dir |

## Red Team Review

### Session — 2026-07-26
**Findings:** 14 (14 accepted, 0 rejected) — from 20 raw across 3 hostile reviewers (Security Adversary, Failure Mode Analyst, Assumption Destroyer), deduped. All carried `file:line`/command evidence.
**Severity breakdown:** 3 Critical, 4 High, 7 Medium.

| # | Finding | Sev | Disposition | Applied To |
|---|---------|-----|-------------|------------|
| 1 | `manleviet/explanation` is PRIVATE → git+https install fails externally | Critical | Accept → **wheel** | P2, plan §Locked-4 |
| 2 | Reproduction baseline untracked+stale+incomplete; diff compares timing/memory cols | Critical | Accept | P3 (logical-diff vs frozen ref), P4 |
| 3 | `--merge` has no completeness guard → silent partial CSV | Critical | Accept | P3 (pre-merge manifest assert) |
| 4 | Phase-4 V4 unexecutable: QuAcq-active coverage gap + k/negatives unpinned | Critical→High | Accept | P4 V4 (gate on fresh sweep + pin selectors) |
| 5 | Clobber-safety false for non-default `$1` | High | Accept | P3 (refuse-guard) |
| 6 | make_tables guard hard-fails on CLI mismatch under `set -e` | High | Accept | P3 (wrap `\|\| skip`) |
| 7 | No resume; `set -e` aborts overnight run; "idempotent" false | High | Accept | P3 (skip-if-exists) |
| 8 | "Deterministic w/o PYTHONHASHSEED for all 5" over-broad; busybox timeout non-repro | High | Accept | P1 §4 (scope + carve-out) |
| 9 | Install pins mutable tag not SHA | Medium | Accept | P2 (SHA in command) |
| 10 | Env-check theater: no pin gate, flamapy unchecked, raw traceback | Medium | Accept | P3 (assertive check) |
| 11 | Foreground busybox, no nohup/detach → SIGHUP kills | Medium | Accept | P3 (nohup+tee, tmux note) |
| 12 | Script assumes CWD/PYTHONPATH/`python` | Medium | Accept | P3 (cd+PYTHONPATH+python3) |
| 13 | Default OUT in tracked, non-ignored space → git-add accident | Medium | Accept | P3 (.gitignore repro/) |
| 14 | P2 misattributes why explanation∉pyproject deps | Medium | Accept | P2 (corrected rationale) |

**Non-findings the reviewers cleared** (do not re-hedge): `--merge` honors `-o` (run_conmin_eval.py:158,114-115); the 5 knobs exist AND are consumed (:176-188); `KB=10/342` + glucose4 `±1` sourced not fabricated (RUN.md:60,65); all 5 KBs have git-tracked inputs; V5's empty-scope-absent premise correct; `$OUT` quoted everywhere (no injection).

### Whole-Plan Consistency Sweep
Re-read `plan.md` + all 4 phase files after applying findings. Reconciled:
- "committed CSVs" wording removed from Phase-4 V4 and plan §Verified-facts → now "untracked/stale/regenerated; frozen reference required".
- Pin form unified across plan §Locked-4, P2, P3 env-check, P4 report = **wheel** (git+SHA secondary); no residual `git+https…@v0.1.0` (tag-only) install string remains as the primary path.
- Determinism claim scoped consistently in P1 §4 + success criterion.
- `-o` "may be ignored" hedge removed from P3/P4 (code-confirmed).
- Additive-file list (V1) updated to include `vendor/*.whl`, `scripts/diff_logical_cols.py`, `.gitignore`.
**Unresolved contradictions:** none. Plan is internally consistent; remaining items are external sequencing (fresh sweep, make_tables landing, explanation-publish decision), tracked under Dependencies.
