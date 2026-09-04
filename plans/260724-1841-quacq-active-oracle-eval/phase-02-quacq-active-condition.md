---
phase: 2
title: QuAcq-Active Condition
status: completed
effort: M
priority: P1
dependencies:
  - 1
---

# Phase 2: QuAcq-Active Condition

## Overview

Add `condition='QuAcq-active'` to the ConMin CV evaluator: run QuAcq in oracle/automated
mode (self-generated queries against the FM oracle) and emit one scored row per fold using
the **same scorer/vocabulary/root handling** and the **same test fold** as every other
condition. Purely additive — `_eval_conmin_fold` (A/C/C∪S) and `_eval_quacq_fold`
(example-only) are left untouched.

## Requirements

- Functional: for each (KB, example-set), produce QuAcq-active rows scored on each fold's
  `te_pos/te_neg`, carrying `condition='QuAcq-active'`, `oracle_queries=<n_queries>`,
  `convergence_reason=<reason>`, `stage1_batch_checks=None`, and the standard scorer columns
  (`sem_p/r/f1`, `accuracy`, `tp/tn/fp/fn`, `n_kb`, sizes, `runtime_ms`/`total_ms`, memory).
- Functional: the existing `QuAcq` (example-only) row is still emitted, unchanged.
- Non-functional: A/C/C∪S/QuAcq rows **value-identical** to before — they gain one additive
  blank `convergence_reason` column + provenance columns, so *value*-identical, **NOT**
  byte-identical [H-1/A-2]. `--merge` stays clean only via union-and-blank-fill tolerance for
  the additive columns [H-5] (the 24–26 committed pre-column JSONs otherwise trip its
  schema-mismatch warning).

## Architecture

### Oracle-mode learn is fold- and example-independent → learn ONCE PER KB (committed, H-6)

`_run_oracle_mode` builds `QueryProvider` **without a pool** (`quacq_runner.py:250`) and
`learn(mode='oracle')` calls `generate_from_sat(...)` (`quacq.py:167`) which never reads
`tr_pos/tr_neg`; `_eval_quacq_fold` passes `shuffle_seed=None`. So the learned theory is a
function of `(bias, FM)` only. **[H-6] `model.bias`/`model.oracle` are per-KB** (`run_conmin_eval.py:143`,
identical across the 6 example-sets), so the theory is byte-identical for **all 3 folds AND all
6 example-sets of a KB**. Therefore learn **once per KB in the apps layer** (Phase 3), and pass
the single `QuAcqRunResult` into every `evaluate_kb_example(...)` call for that KB. This is the
committed structure — it avoids the 6×-redundant recompute the per-(KB,es) hoist would incur
(≤6×400 s wasted on busybox). `evaluate_kb_example` therefore *receives* `active_res` (or
`None` when `run_quacq_active=False`); it does **not** build the runner itself.

> **[C-4] Determinism caveat under timeout:** "byte-identical across es/folds" holds only when
> the learn ran to a deterministic stop (`empty_bias`/`no_query`/`max_queries`). A wall-clock
> `timeout` truncates at a machine-load-dependent point → the single per-KB theory is still one
> object (so reuse is valid within one run), but it is **not reproducible across runs**; such a
> KB is reported non-converged (H-3), not as a clean number. Provenance (`max_queries`,
> `timeout_s`) is recorded so a timed row is traceable.
>
> Fallback (audit-simplicity only): per-fold clone of `_eval_quacq_fold`. Same numbers, 18×
> redundant compute per KB — rejected as default; kept only as an escape hatch.

### Scoring helper

Reuse the existing `_score_row` / `_sizes` / `_cost` as the example-only QuAcq row does
(`conmin_cv_evaluator.py:238-243`), only changing:
- `condition` → `'QuAcq-active'`
- score against the **test** fold (`te_pos/te_neg`) — same scorer/vocab as all conditions
- `oracle_queries=res.n_queries`, `stage1_batch_checks=None`
- attach `convergence_reason` + **provenance** `max_queries`/`timeout_s` (C-4)

```python
def _score_quacq_active_row(res, meta, comparator, ground_truth, variables,
                            te_pos, te_neg, root_clauses,
                            max_queries, timeout_s) -> dict:
    runtime_ms = (res.metrics.values.get('runtime_ms', res.runtime_ms)
                  if res.metrics else res.runtime_ms)
    return _score_row(
        meta, 'n/a', 'QuAcq-active', None, res.kb_constraints, res.kb_clauses, (),
        comparator, ground_truth, variables, te_pos, te_neg, root_clauses, res.n_bias,
        _sizes(0, 0, 0, res.n_kb, 0, 0, 0, 0),
        _cost(runtime_ms, 0.0, 0.0, 0, 0, 0, 0, 0, res.memory_peak_mb,
              oracle_queries=res.n_queries or 0, stage1_batch_checks=None,
              convergence_reason=res.convergence_reason,
              qa_max_queries=max_queries, qa_timeout_s=timeout_s))   # provenance, C-4
```

> **[H-1] Structural metrics are fold-independent — do NOT present them as CV mean±std.**
> `score_named_kb` computes desc/clause/sem P/R/F1 and `exact_equiv` from `names`+comparator+
> ground_truth with **no test set** (`conmin_slice_scorer.py:53-64`). For a single per-KB
> theory those are identical across the 3 fold rows → `sem_f1_std ≡ 0.000` (`aggregate_cv:317`).
> Reporting "0.50 ± 0.000" next to per-fold-trained conditions reads as a faked CV. Fix at the
> **report/aggregate layer** (Phase 4 + `aggregate_cv`): emit QuAcq-active structural metrics as
> a single value flagged fold-independent; only accuracy/tp/tn/fp/fn/specificity legitimately
> vary by fold. (The plan's earlier claim "sem-metrics vary only with the test set" was wrong.)
>
> **[C-3] Reporting preference (→ CW Main):** semantic-F1 (structural) is the fair headline;
> `accuracy`/tp/tn/fp/fn are graded on examples labeled by the same FM QuAcq-active queried, so
> caveat them as not held-out. Keep the columns (schema parity) but flag them in the report.

### `convergence_reason` + provenance columns — uniform, WITH `--merge` tolerance (H-5)

Add `convergence_reason: str = ''`, `qa_max_queries=None`, `qa_timeout_s=None` to **`_cost(...)`**
(all defaulted) so they land on **every** scored row (A/C/C∪S/QuAcq get `''`/`None`,
QuAcq-active gets real values). These strings/`None`s are **not** in `_AGG_COLS`, so
`aggregate_cv` skips them (verified: it only iterates `_AGG_COLS`, `:313`) — no numeric
aggregation, no crash.

> **[H-5] The "one schema → no `--merge` warning" claim was FALSE — this is the fix.**
> `_merge_per_kb` globs **all** `*_eval.json` (`run_conmin_eval.py:56`), including the **24–26
> already-committed Jul-23 JSONs that have none of these columns**. Adding columns to fresh rows
> makes `schemas = {tuple(sorted(r.keys()))}` (`:68`) have `len > 1` → the "re-run affected KB(s)"
> warning fires and the consolidated CSV is ragged. **Required fix (Phase 3):** make
> `_merge_per_kb` **union the column set across all rows and blank-fill missing keys** before the
> schema comparison, so a purely-additive column delta is tolerated (not warned). Then a subset
> re-run (only REAL-FM-7) merges cleanly against the untouched committed KBs. Do **not** claim a
> subset sweep is warning-free without this tolerance. (Alternative, heavier: backfill all
> committed JSONs with the blank columns in the same change.)

### Wiring — `evaluate_kb_example` RECEIVES the per-KB result (H-6)

The learn happens **once per KB in the apps layer** (Phase 3), so `evaluate_kb_example` takes a
new param `active_res: QuAcqRunResult | None` (plus `qa_max_queries`, `qa_timeout_s` for
provenance) and does **not** build a runner itself:

1. Inside the fold loop, after the existing `_eval_quacq_fold(...)` append, add:
   ```python
   if active_res is not None:
       rows.append(_score_quacq_active_row(
           active_res, meta, comparator, ground_truth, variables,
           te_pos, te_neg, root_clauses, qa_max_queries, qa_timeout_s))
   ```
2. `_learn_quacq_active(bias_path, fm_path, solver_name, use_incremental, max_queries, timeout_s)`
   lives in this module but is **called from `run_conmin_eval.py`** (Phase 3, once per model).
   **[H-7] cleanup MUST be in `finally`:**
   ```python
   def _learn_quacq_active(bias_path, fm_path, solver_name, use_incremental,
                           max_queries, timeout_s):
       runner = QuAcqRunner(bias_path, fm_path, solver_name, query_mode='automated',
                            max_queries=max_queries, timeout_s=timeout_s,
                            use_incremental=use_incremental)
       try:
           return runner.run(mode='automated')          # QuAcqRunResult
       finally:
           runner.cleanup()                              # runs on raise/timeout too
   ```
   On exception the apps layer catches it and passes a marker (see Phase 3) so
   `evaluate_kb_example` emits a per-fold `error` row (mirroring `_eval_quacq_fold`'s
   `:229-232`, `condition='QuAcq-active'`) — counted by `aggregate_cv`'s `n_failed`.

### [H-3] Non-converged rows must not be averaged as converged

A `convergence_reason ∈ {timeout, max_queries}` row is a **scored partial KB**, not an `error`,
so `aggregate_cv`'s `ok = [r for r in grp if 'error' not in r and 'gate_tripped' not in r]`
(`conmin_cv_evaluator.py:308`) counts it as a good fold and folds its (low) sem-F1 into the mean
invisibly. Fix `aggregate_cv`: for QuAcq-active groups, **count `n_timeout`/`n_maxq` per group**
AND exclude non-converged rows from the metric mean the way `error`/`gate_tripped` rows are
excluded. A partial-KB number must never be published as a converged score.

### [M-2] Record example-only QuAcq's real `convergence_reason` too

The existing `_eval_quacq_fold` discards `res.convergence_reason` (`:234` has it in hand). Pass
`convergence_reason=res.convergence_reason` into its `_cost(...)` as well, so the example-only
row records its actual stop (`pool_exhausted`) — the direct evidence for *why* it is crippled,
which the report needs. One-line change; the example-only path stays otherwise untouched.

## Related Code Files

- Modify: `conacq/eval/conmin_cv_evaluator.py`
  - add `_learn_quacq_active(...)` (called by Phase 3) + `_score_quacq_active_row(...)` helpers
  - add `convergence_reason=''`, `qa_max_queries=None`, `qa_timeout_s=None` params to `_cost(...)`;
    include them in the returned dict (provenance, C-4)
  - `evaluate_kb_example`: add params `active_res`, `qa_max_queries`, `qa_timeout_s`; score
    `active_res` inside the fold loop (H-6 — it does NOT build the runner)
  - `aggregate_cv`: count `n_timeout`/`n_maxq` per group + exclude non-converged QuAcq-active
    rows from the metric mean (H-3)
  - `_eval_quacq_fold`: pass `convergence_reason=res.convergence_reason` into its `_cost(...)`
    (M-2) — the ONLY change to the example-only path (value-identical otherwise)
  - update the module docstring: "four comparison conditions" → "five" + the QuAcq-active line
- Modify (Phase 1): `conacq/runners/quacq_runner.py` (`timeout_s`)
- Do **not** modify: `_eval_conmin_fold`, `KBComparator`, `conmin_slice_scorer`,
  `score_named_kb`, the ConMin acquisition path.

## Implementation Steps

1. Add `convergence_reason=''`, `qa_max_queries=None`, `qa_timeout_s=None` to `_cost` + return
   dict (all callers pass by keyword — verified safe, conmin_cv_evaluator.py:253-255).
2. Add `_learn_quacq_active` with `try/finally: runner.cleanup()` (H-7).
3. Add `_score_quacq_active_row` (test fold, `oracle_queries`, `convergence_reason`, provenance).
4. `evaluate_kb_example`: add `active_res`/`qa_max_queries`/`qa_timeout_s` params; score
   `active_res` per fold (skip if `None`); apps layer supplies it once per KB (Phase 3, H-6).
5. `_eval_quacq_fold`: add `convergence_reason=res.convergence_reason` to its `_cost` (M-2).
6. `aggregate_cv`: add `n_timeout`/`n_maxq` counts + exclude non-converged QuAcq-active rows
   from the metric mean (H-3).
7. Report/aggregate: mark QuAcq-active structural metrics fold-independent (single value, not
   mean±0.000) (H-1).
8. Update module docstring (five conditions).

## Success Criteria

- [ ] REAL-FM-7 run emits rows with `condition ∈ {A, C, C∪S, QuAcq, QuAcq-active}`.
- [ ] **Gate (Phase 4):** QuAcq-active `sem_f1` materially > example-only AND clears the paper's
      example-first band (≤0.105) on REAL-FM-7 **and** a mid-size KB, `oracle_queries` reflects
      the active budget, `convergence_reason` recorded.
- [ ] `convergence_reason` + provenance populated on QuAcq-active; blank/`None` on the other four.
- [ ] A/C/C∪S/QuAcq **values** identical to a pre-change run (diff `REAL-FM-7_long.csv` filtered
      to those conditions, **dropping the additive columns** — value-identical, not byte).
- [ ] `--merge` runs against the committed KBs + a fresh REAL-FM-7 with **no** re-sweep warning
      (union/blank-fill tolerance in place, H-5).
- [ ] A non-converged QuAcq-active fold is counted (`n_timeout`/`n_maxq`) and excluded from the
      mean (H-3), not silently averaged.

## Risk Assessment

- **[M-3] "No shared mutable state" was inaccurate.** `profiler_session` swaps a **module-global**
  `gprofiler` with no restore (`profiling/registry.py:84-90`); both the runner (`quacq_runner.py:158`)
  and each ConMin fold (`conmin_cv_evaluator.py:118`) open their own session and pass the profiler
  explicitly, which is what actually protects ConMin's counters — a property to state, not assume.
  (RNG is isolated — `query_provider.py:57-60` — refuted as a risk.) Learning **once per KB in the
  apps layer** (H-6) also means the runner's `FMOracle` is built and **released before**
  `evaluate_kb_example` opens its own — avoiding the 2× live 854-var solver peak on busybox.
- **[H-7] Cleanup on the raise/timeout path**: `_learn_quacq_active` uses `try/finally:
  runner.cleanup()` so the runner's `FMOracle` PySAT solver is released even when `run()` raises;
  without it, ×(KB×6 es) leaks FDs/native memory late in the sweep.
- **[H-1] std=0 is real, not "honest CV"**: structural metrics are fold-independent → report as a
  single value; do not present `sem_f1 ± 0.000` alongside per-fold-trained conditions.
- **[H-3] Timeout ≠ error but ≠ converged**: a `timeout`/`max_queries` row is a scored partial KB;
  it must be counted and excluded from the mean, never folded in as a good fold.
