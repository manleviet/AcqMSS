---
phase: 1
title: "Doc ConMin Chain"
status: pending
effort: "~1.5h"
priority: P1
dependencies: []
---

# Phase 1: Document the ConMin/AAAI eval chain in eval-pipeline.md

## Overview
`docs/eval-pipeline.md` documents ONLY the old ConGen pipeline (`run_cv` → `run_compare` → `extract_results`) — zero mentions of `run_conmin_eval` or `make_tables`, i.e. the repo's reproducibility doc does not cover the paper being submitted. Add a new **ConMin comparison eval (AAAI)** section documenting the chain end-to-end. Additive: append a section; do not rewrite the ConGen sections.

## Requirements
- Functional: reproducer can run the ConMin chain from committed inputs using only this doc.
- Non-functional: no fabricated numbers; cross-links to `data/results_conmin/RUN.md` (runbook) and Phase-2 pin.

## Architecture / content to add
New top-level section `## ConMin Comparison Eval (AAAI submission)` after the existing Phase-3 section. Cover:

1. **Chain diagram** (committed inputs regenerate nothing):
   ```
   committed: data/fms/*.uvl · data/bias/*-bias.json · data/examples/* · data/folds/*
        │  (pre-recorded — DO NOT regenerate; seed=82 fixed)
        ├─ run_conmin_eval.py  --kb <KB> [--example-sets …] [--conditions …]   → {kb}_{es}_eval.json + {kb}_{long,cv}.csv
        ├─ run_conmin_eval.py  --merge                                          → conmin_eval_long.csv + conmin_eval_cv.csv
        └─ make_tables.py       (CW Main deliverable; spec v1+v2)               → md + latex tables
   ```
2. **5 conditions**: A / C / C∪S / QuAcq (passive, example-only) / QuAcq-active (oracle-mode). One-line each; point to RUN.md for depth.
3. **Knobs table** (from `apps/conf_conmin/run_conmin_eval_config.toml`):

   | Knob | Where | Reported value | Meaning |
   |---|---|---|---|
   | `seed` | `[general]` | `82` | folds pre-recorded; seed only affects any live sampling, not the committed folds |
   | `solver_name` | `[general]` | `glucose4` | **solver of record**; feeds BOTH ConMin checker AND QuAcq oracle (no confound); another solver may shift `|KB|` by ±1 |
   | `quacq_active_max_queries` | `[evaluation]` | `5000` (busybox `20000`) | deterministic query rail |
   | `quacq_active_timeout_s` | `[evaluation]` | `400` | wall-clock safety net; a timeout → **non-converged**, report as such |
   | `quacq_query_mode` | `[evaluation]` | `example_only` | passive-QuAcq query source; `--conditions quacq` recomputes just this column |

4. **Determinism rule** (scope precisely — Red Team #8; do NOT over-claim): results deterministic **without** `PYTHONHASHSEED`, with these documented bounds:
   - QuAcq (both modes): hash-independent — FindScope iterates in canonical (sorted) order (`3654c2b`/`b40771c`); **verified** across fixed seeds + unset on REAL-FM-7/fqa/arcade-game/REAL-FM-4 (RUN.md:57-59) — busybox not separately verified.
   - A/C/C∪S/ConMin: hash-independent **by construction** (no dict-order-dependent output) — asserted, not empirically swept.
   - **Carve-out:** busybox QuAcq-active can hit the 400 s wall-clock net → truncated theory, reported `convergence_reason=timeout` / **non-converged** and **not hardware-reproducible** (config §22-29; RUN.md:15-20). Report that cell as `--`, never a number.
   No env pin needed for the hash-seed; the busybox-timeout non-determinism is orthogonal (wall-clock, not hashing).
5. **Pre-recorded rule**: folds (`data/folds/`) and examples (`data/examples/`) are committed and **must not be regenerated**; a reproducer runs eval directly on them.
6. **Aggregation convention** (mirror what `make_tables` consumes, per v2): `aggregate_cv` is convergence-aware — QuAcq-active folds whose `convergence_reason` ∈ {`timeout`,`max_queries`} are counted (`n_timeout`/`n_maxq`/`n_nonconverged`) and **excluded** from the mean; report them "did not converge", never as a clean number. Tables mark aggregation caveats with `†` (owned by make_tables/v2). State the reported cross-KB aggregation = **mean excluding 2COV**.
7. **QuAcq threats-to-validity** (1–2 lines, cross-link RUN.md): solver-conditional (name the solver), order-dependent-by-design (one canonical sorted order → `oracle_queries` reproducible).
8. **Solver caveat**: glucose4 is the reported solver; canonical REAL-FM-7 figure = KB=10, oracle_queries=342, `no_query`.
9. Cross-link the Phase-2 explanation pin ("environment: see README / pin below").

## Related Code Files
- Modify: `docs/eval-pipeline.md` (append section; keep under `docs.maxLoc=800` — current ~378 lines, budget fine)
- Read-only source: `apps/conf_conmin/run_conmin_eval_config.toml`, `apps/run_conmin_eval.py`, `data/results_conmin/RUN.md`

## Implementation Steps
1. Append `## ConMin Comparison Eval (AAAI submission)` after existing content.
2. Add chain diagram, 5-condition list, knobs table, determinism + pre-recorded rules, aggregation convention, threats, solver caveat.
3. Reference `make_tables.py` as CW Main's deliverable (do not describe its internals — v1+v2 own that).
4. Add a "Committed artifacts" mini-table: which `.uvl`/bias/examples/folds/eval-JSON/CSV are tracked so a reproducer knows nothing is missing.
5. Cross-link RUN.md (operational runbook) vs this doc (reproducibility reference) — state the division so they don't drift.

## Success Criteria
- [ ] Section renders; `run_conmin_eval` + `make_tables` + `--merge` all appear.
- [ ] All 5 knobs documented with reported values matching the committed TOML.
- [ ] "deterministic without PYTHONHASHSEED" present **and scoped** (QuAcq verified 4 KBs / ConMin by-construction / busybox-timeout carve-out); "folds/examples pre-recorded — do not regenerate"; glucose4 caveat all present.
- [ ] No fabricated result numbers; only config-sourced/canonical values (KB=10/342) with solver named.
- [ ] Doc stays < `docs.maxLoc` (800 lines).

## Risk Assessment
- Risk: drift vs RUN.md. Mitigation: this doc = reference (what/why + knobs), RUN.md = runbook (how to stage/nohup); cross-link, don't duplicate.
- Risk: describing make_tables internals that v1+v2 own. Mitigation: reference only; state it's CW Main's, spec lives in prompts/.
