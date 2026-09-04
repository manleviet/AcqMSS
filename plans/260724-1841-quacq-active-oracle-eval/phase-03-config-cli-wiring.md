---
phase: 3
title: Config & CLI Wiring
status: completed
effort: S
priority: P2
dependencies:
  - 2
---

# Phase 3: Config & CLI Wiring

## Overview

Thread the QuAcq-active budget/timeout/toggle from `apps/conf_conmin/run_conmin_eval_config.toml`
and CLI overrides down through `apps/run_conmin_eval.py` into `evaluate_kb_example`. No new
entry point is built — the `--kb` runner already exists (`run_conmin_eval.py:86`); this phase
just wires the new condition's knobs and gives Viet-Man a busybox-tuning override.

## Requirements

- Functional: `max_queries` (default 5000) and `timeout_s` (default 400.0) for QuAcq-active
  come from `[evaluation]` config with CLI override; a toggle can disable the condition.
- Non-functional: defaults reproduce the recommended sweep without any CLI flags; existing
  invocations in `data/results_conmin/RUN.md` keep working; `--merge` path untouched.

## Architecture

- **[H-6] Learn once per KB in the apps layer.** In `main()`'s `for model in models:` loop,
  *before* the `for es in example_sets:` loop, call `_learn_quacq_active(model.bias, model.oracle,
  …, max_queries=<per-KB>, timeout_s=…)` **once** and reuse the result across all example-sets
  of that KB (the theory is per-`(bias, FM)`). Catch its exception here → pass a marker so
  `evaluate_kb_example` emits per-fold `error` rows. This replaces per-(KB,es) re-learning
  (6× waste) — the runner's oracle is also released before `evaluate_kb_example` opens its own
  (M-3, avoids the 2× solver peak).
- **Config keys** (`[evaluation]` in the TOML):
  ```toml
  quacq_active = true                 # emit the QuAcq-active condition
  quacq_active_max_queries = 5000     # DEFAULT query budget (per-KB override below)
  quacq_active_timeout_s = 400        # wall-clock SAFETY NET only (C-4 — not the reproducible rail)
  # [H-4] Per-KB budget: 5000 is < busybox |B|=6635, and the counter is shared with
  # FindScope/FindC, so effective constraints learned ≪ budget. Size big KBs so max_queries
  # (deterministic) fires before the timeout, or accept a non-converged row.
  quacq_active_max_queries_per_kb = { "busybox-1.18.0" = 20000 }
  ```
- **CLI overrides** (argparse, `run_conmin_eval.py:main`):
  - `--no-quacq-active` (store_false → `run_quacq_active`) — A/C/C∪S/QuAcq-only pass.
  - `--quacq-active-timeout SECONDS`, `--quacq-active-max-queries N` — dial a specific KB run.
- **Precedence**: CLI > per-KB config map > `[evaluation]` default > hardcoded (matches
  `--k`/`--negatives` resolution at `run_conmin_eval.py:112-114`).
- **[C-4] Provenance**: write `quacq_active_max_queries` + `quacq_active_timeout_s` into each
  `{kb}_{es}_eval.json` (alongside `seed`, `run_conmin_eval.py:147-151`), and stamp them as
  `qa_max_queries`/`qa_timeout_s` columns on every QuAcq-active row (Phase 2). `--merge` **refuses
  to blend** QuAcq-active rows with differing provenance (warn + skip, not silent concat).
- **[H-5] `--merge` additive-column tolerance**: before the `schemas = {…}` check
  (`run_conmin_eval.py:68`), **union all row keys and blank-fill missing ones**, so the 24–26
  committed pre-column JSONs merge cleanly with fresh rows instead of tripping the "re-run
  affected KB(s)" warning. Keep a real warning only for *value*-level provenance conflicts (C-4).

## Related Code Files

- Modify: `apps/run_conmin_eval.py`
  - add argparse options (`--no-quacq-active`, `--quacq-active-timeout`, `--quacq-active-max-queries`)
    alongside existing ones (`:85-95`); resolve CLI > per-KB config map > `[evaluation]` >
    default (near `:112-114`)
  - **[H-6]** in `for model in models:` (`:133`), before the `for es …` loop (`:136`), call
    `_learn_quacq_active(model.bias, model.oracle, …)` **once** (guarded by `run_quacq_active`);
    catch its exception → marker. Pass `active_res`/`qa_max_queries`/`qa_timeout_s` into the
    `evaluate_kb_example(...)` call (`:143-145`)
  - **[C-4]** add `quacq_active_max_queries`/`quacq_active_timeout_s` to the `write_json_atomic`
    provenance dict (`:147-151`)
  - **[H-5]** in `_merge_per_kb` (`:46-76`): union row keys + blank-fill before the `schemas`
    check (`:68`); replace the schema-count warning with a provenance-conflict check (skip+warn
    only when QuAcq-active rows disagree on `qa_max_queries`/`qa_timeout_s`)
  - log the resolved QuAcq-active budget/timeout in the run banner (`:126-128`)
- Modify: `apps/conf_conmin/run_conmin_eval_config.toml` — add the `[evaluation]` keys + per-KB map
- Modify: `data/results_conmin/RUN.md` — 5 conditions; `convergence_reason` + provenance columns;
  busybox per-KB budget recipe; **correct** the "subset pass is safe" note (C-4): a subset pass is
  safe only when the **same `max_queries`/`timeout_s`** is used for a KB across passes, and only
  after the `--merge` tolerance is in place

## Implementation Steps

1. Add config keys (`[evaluation]` + per-KB map) to the TOML.
2. Add argparse options; resolve CLI > per-KB map > config > default.
3. **[H-6]** hoist the per-KB `_learn_quacq_active` call; thread `active_res` + provenance into
   `evaluate_kb_example`; banner-log the settings.
4. **[C-4]** record `max_queries`/`timeout_s` in the JSON provenance.
5. **[H-5]** make `_merge_per_kb` union/blank-fill tolerant; add the provenance-conflict guard.
6. Update `RUN.md` (5 conditions, provenance, per-KB budget, corrected subset-pass caveat).

## Success Criteria

- [ ] `python -m apps.run_conmin_eval CFG --kb REAL-FM-7 -v` learns QuAcq-active **once** for the
      KB (one learn log, not 6) and emits its rows with provenance visible in the banner.
- [ ] `--no-quacq-active` reproduces the 4-condition output (QuAcq-active absent; A/C/C∪S/QuAcq
      values identical).
- [ ] `--quacq-active-max-queries 200` on busybox produces `convergence_reason='max_queries'`
      (deterministic) rows and returns quickly.
- [ ] `--merge` over the committed KBs + a fresh REAL-FM-7 gives **no** re-sweep warning
      (tolerance) but **does** warn if two QuAcq-active rows disagree on provenance.

## Risk Assessment

- **Default-on cost**: QuAcq-active adds one per-KB learn (not per-(KB,es), H-6). `--no-quacq-active`
  is the escape hatch. Feasibility in Phase 4.
- **Merge-tolerance regression**: union/blank-fill must not mask a *genuine* stale-schema (e.g. a
  dropped metric column). Scope the tolerance to *additive* keys; keep a warning if a previously
  present column disappears.
- **RUN.md drift**: currently says "four conditions" — update here, not later.
- **Config parsing**: `[evaluation]` via `load_pipeline_config` returns a plain dict; unknown keys
  tolerated (old configs fall back to defaults). Confirm the per-KB TOML table parses.
