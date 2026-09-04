# Code Red-Team Adjudication — QuAcq-active implementation (post-cook)

Target: the implemented diff on `feat/conmin` (Phase 1–3 + gate), 6 tracked files + 1 new test.
3 hostile reviewers (Correctness/Failure-Mode, Contract/Regression, Test-Adequacy). All findings
`file:line`-backed. **1 Critical reproduced end-to-end.**

## Disposition summary
| # | Finding | Sev | Disposition |
|---|---------|-----|-------------|
| C1 | `--merge` blank-fill voids the CV table when any failure row present | Critical | **FIXED** |
| H1 | Non-convergence exclusion QuAcq-active-only; passive QuAcq at `max_queries` averaged as converged | High | **FIXED** |
| R1-F2 | Stale-schema detector false-warns on sparse failure rows | Medium | **FIXED** (same change as C1) |
| R3-F1 | Mid-learn timeout (n_queries>0, partial KB) untested; tautological assertion | High | **FIXED** (test + assertion) |
| R3-F3/F5 | Real `evaluate_kb_example`/`_learn_quacq_active`/`_score_quacq_active_row` path never run by pytest | High | **FIXED** (integration test) |
| R3-F6 | `quacq_active_error` per-fold error-row path untested | Medium | **FIXED** (test) |
| R3-F7 | Disabled path (active_res=None → no rows) unasserted | Medium | **FIXED** (test) |
| R2-F2 | "value-identical" imprecise (passive QuAcq gained populated `convergence_reason`) | Medium | Documented (wording; verification was over shared cols — accurate) |
| R2-F3 | `test_aggregate_cv_counts_timeout_separately` uses a mix impossible for a single-learn group | Medium | Kept (valid pure-fn unit test; real path now covered by integration test) |
| R1-F5/R2-F5 | QuAcq-active fold-independent metrics/cost show `mean ± 0.000` in CV CSV | Low | Deferred (arithmetically correct; report H-1 note covers interpretation; NO-GO ⇒ informational) |
| R2-F4 | `ADDITIVE` allowlist in `_merge` duplicates `_cost`'s new keys (drift risk) | Low | Deferred (comment; only consumer) |
| R1-F3 | `timeout_s` silently ignored for example modes | Low | Deferred (latent; docstring already states it) |
| R3-F2 | Inner-loop soft-ceiling (FindScope overruns deadline) not directly tested | Medium | Partially covered (mid-learn test); inner-stub deferred |
| R3-F4 | No numeric golden locking A/C/C∪S value-identity | High | Deferred — see note |

## The Critical (reproduced, fixed)

`_merge_per_kb` blank-filled **all** union columns to `None`, including the sparse
`error`/`gate_tripped` flags from failure rows (B2/B3 + learn-error rows). `aggregate_cv`
classifies failures by **key presence** (`'error' in r`), so after blank-fill every row carried
`error=None` → every fold counted as errored → **`conmin_eval_cv.csv` emitted zero metric means
for A/C/C∪S/QuAcq**, silently, whenever any failure row existed (i.e. every real sweep).
Reproduced: 3 healthy A folds (sem_f1 0.4/0.5/0.6) → `n_ok_folds=0, sem_f1_mean=''`.

**Fix** (`apps/run_conmin_eval.py` `_merge_per_kb`, `conacq/eval/conmin_cv_evaluator.py`
`aggregate_cv`):
- Partition rows into scored vs failure-marker; align/blank-fill **scored rows only**; append
  failure rows **unchanged** (sparse) so `aggregate_cv`'s classification still works.
- Scope the stale-schema detector + provenance check to scored rows (kills R1-F2 false warning).
- Defense-in-depth: `aggregate_cv` now classifies failures by **truthiness**
  (`r.get('error') is not None`), immune to a stray `None` fill.

Verified end-to-end on the real REAL-FM-7 smoke JSONs: A/C/C∪S/QuAcq means preserved
(0.340/0.187/0.771/0.111), QuAcq-active correctly excluded (`n_nonconv=3, n_maxq=3`), no warnings.

## H1 (fixed)

Non-convergence exclusion was gated to `condition == 'QuAcq-active'`; passive QuAcq also uses the
`max_queries` rail (default 1000) and a truncated passive theory would be averaged as converged.
**Fix:** exclusion now keys on `convergence_reason in ('timeout','max_queries')` for **any**
condition; A/C/C∪S carry a blank reason so they are never touched; normal QuAcq convergences
(`pool_exhausted`/`empty_bias`/`no_query`) stay in the mean.

## Tests added (6): closing the gap that let C1 through

`tests/test_conmin_quacq_active.py`: `test_merge_with_failure_row_preserves_healthy_means` (C1
regression), `test_aggregate_cv_excludes_max_queries_for_any_condition` (H1),
`test_evaluate_kb_example_emits_quacq_active_uniform_schema` (real integration: QuAcq-active row
key-set == A row key-set + top-level `convergence_reason`), `..._disabled_emits_no_quacq_active`,
`..._learn_error_emits_per_fold_error_rows`. `tests/test_quacq.py`:
`test_timeout_mid_learn_preserves_partial_kb` (monkeypatched clock, n_queries>0) + fixed the
tautological `len(...)>=0` assertion.

**Suite: 576 passed, 1 skipped** (was 570+1). All fixes verified.

## Verified-clean (reviewers' refuted attacks — recorded)
- Empty-KB `Reduce` after past-deadline is safe; cross-module `time.monotonic()` shares one clock.
- Reused per-KB `QuAcqRunResult` is not mutated during scoring (`score_named_kb` copies inputs).
- All `QuAcqRunner(...)`/`.learn(...)`/`_cost(...)` call sites pass new params by keyword — no
  positional mis-bind; `n_failed` value unchanged for existing conditions; config inline table parses.

## Residual / recommendations (deferred, not blocking)
- **R3-F4 golden:** no numeric fixture locks A/C/C∪S identity. Per the "golden recorded from old
  code" rule, a meaningful golden must be frozen from PRE-change code — not recoverable post-hoc
  here; the additive change was verified by a live 0-diff comparison instead. Recommend a frozen
  golden before the next ConMin-touching change.
- **R1-F5/R2-F5:** if CW Main reports QuAcq-active in a mean±std table, suppress std for its
  fold-independent structural/cost columns (report layer), per the plan's H-1 note.

## Unresolved questions
1. Should the deferred `ADDITIVE`-constant single-sourcing (R2-F4) and example-mode `timeout_s`
   warning (R1-F3) be done now or left as documented low-risk?
2. Golden fixture for A/C/C∪S (R3-F4) — worth recording now (guards future edits only), or skip
   given QuAcq-active is heading to informational?
