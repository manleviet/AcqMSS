# Red-Team Adjudication — QuAcq-active oracle-mode eval condition

Plan: `plans/260724-1841-quacq-active-oracle-eval/` · Branch `feat/conmin` · 3 hostile reviewers
(Assumption Destroyer, Failure Mode Analyst, Scientific-Validity/Scope Critic) · 24 raw → 15 deduped.
Every finding carries `file:line` evidence → all pass the evidence filter. All 15 = **Accept**
(none evidence-free; none reversing a source-verified fact).

## Severity roll-up
4 Critical · 7 High · 4 Medium. All Accept.

## Verified SAFE (attacks that did NOT hold — recorded so they aren't re-raised)
- `convergence_reason` string is excluded from `_AGG_COLS` (conmin_cv_evaluator.py:283-292); `aggregate_cv`
  only iterates `_AGG_COLS` → no aggregation crash on the new column.
- `_cost` callers all pass `oracle_queries=/stage1_batch_checks=` by keyword (conmin_cv_evaluator.py:253-255)
  → appending a defaulted `convergence_reason` kwarg is signature-safe.
- Existing `QuAcqRunner(bias, fm, solver, use_incremental=…)` + `runner.run(tr_pos, tr_neg)` (…:223-226)
  unaffected by additive `timeout_s`/`deadline` defaults.
- Oracle-path `QuAcqRunResult` populates `n_queries/convergence_reason/kb_constraints/kb_clauses/n_bias/
  n_kb/memory_peak_mb/metrics/runtime_ms` (quacq_runner.py:217-234).
- RNG is isolated (`random.Random(seed)`, query_provider.py:57-60) — not a shared-stream risk.

---

## CRITICAL

### C-1 · Premise contradicted by the paper's own example-first (SAT-generating) results
**Reviewer:** Sci-Validity. **Evidence:** `paper/evaluation.tex:318` (example-first already does SAT
generation: "SAT solver searches for a configuration that satisfies KB∪BG but violates c_i" = the
`generate_from_sat`/`DiscriminatingGenerator` path, quacq.py:167), `:374-378` (sem-F1 only 0.049–0.105),
`:387,:438` (cap is **structural** — one-at-a-time learning + `Reduce` KB compression, quacq.py:249-255 —
not query starvation).
**Flaw:** Plan premise (plan.md:19-24) = "QuAcq is crippled only because it never queries the oracle."
The paper's own data says a SAT-query variant already exists and still caps ≤0.105 for a structural reason.
**Scenario:** busybox oracle-mode returns sem-F1 ≈ 0.05, acceptance "materially higher" fails, multi-hour
sweep wasted; or it returns high F1 and contradicts the paper's headline with no reconciliation.
**Disposition:** ACCEPT → add a **cheap go/no-go gate**: run REAL-FM-7 **and** one mid-size KB (fqa/arcade)
untimed, measure oracle-mode sem-F1 vs the paper's example-first band, BEFORE any sweep. Reconcile
oracle(`automated`) vs example-first(`generate()` pool-then-SAT) in the plan. Escalate to CW Main.

### C-2 · Apples-to-oranges budget: ~6 training examples vs a 5000 oracle-query budget
**Reviewer:** Sci-Validity. **Evidence:** `data/examples/REAL-FM-7_ff.json` (6 pos/3 neg → train ≈ 4+2),
ConMin makes zero adaptive queries (`oracle_queries=0` hardcoded conmin_cv_evaluator.py:178,191,205),
QuAcq-active budget 5000 (plan.md:48). Cost axis exists (`oracle_queries` = "the scarce cost", …:264).
**Flaw:** Table places raw sem-F1 side by side with no query-budget parity / cost caveat.
**Scenario:** Reviewer: "shows only that 800× more oracle interrogations wins — not a method comparison."
**Disposition:** ACCEPT → frame explicitly as **unequal-cost, cost-axis-reported**; optionally add a
budget-parity variant (cap queries ≈ #training examples). Methodology call → CW Main.

### C-3 · The oracle QuAcq-active interrogates IS the grader (construct validity)
**Reviewer:** Sci-Validity. **Evidence:** learn oracle = `FMOracle(fm_path)` (quacq_runner.py:248 →
base_runner.py:84), sem-F1 graded vs `GroundTruthData.from_uvl(fm_path)` (conmin_cv_evaluator.py:55),
accuracy vs test examples labeled by the same FM; ConMin uses only static `oracle_data` (…:120).
**Flaw:** QuAcq-active gets up to 5000 **adaptive** probes of the exact object it's scored against.
**Scenario:** Reviewer: "not held-out generalization; adaptive access to the ground-truth classifier."
**Disposition:** ACCEPT → document as explicit threat-to-validity; prefer reporting **semantic-F1 only**
(structural) and dropping the accuracy side-by-side, or hold scoring FM disjoint. Methodology → CW Main.

### C-4 · Timeout truncation makes busybox non-reproducible while the plan hoists it as "deterministic"; no provenance recorded
**Reviewer:** Failure-Mode. **Evidence:** determinism claim plan.md:67-76 / phase-02:32-41; truncation
`break` on `time.monotonic() >= deadline` (phase-01) → partial `learned_kb`; run JSON records `seed` but
NOT `max_queries`/`timeout_s` (run_conmin_eval.py:147-151); rows carry no budget/timeout column
(`_cost`, conmin_cv_evaluator.py:253-279). Machine-noise caveat plan.md:62-63.
**Flaw:** busybox is the only KB expected to time out → precisely there the theory = f(bias, FM, machine
load), not f(bias, FM); "subset pass is safe" is false; `--merge` blends different-budget theories under
one label.
**Scenario:** re-run → different partial KB → different sem-F1; `rs_1n@300s` + `rs_2n@400s` merged silently.
**Disposition:** ACCEPT → record `max_queries`+`timeout_s`+`convergence_reason` as **provenance columns**
in every QuAcq-active row & JSON; `--merge` refuses to blend differing provenance; prefer a **deterministic
`max_queries`-only cap** for busybox (or report it "did not converge") rather than wall-clock.

---

## HIGH

### H-1 · Fake CV: fold-independent learner ⇒ semantic-F1 std ≡ 0; plan misstates which metrics vary
**Reviewers:** Assumption + Sci-Validity. **Evidence:** `score_named_kb` computes desc/clause/sem P/R/F1
from names+comparator+ground_truth with **no test set** (conmin_slice_scorer.py:53-64); `sem_*` ARE in
`_AGG_COLS` (…:284-286); `stdev` over identical values = 0 (…:317). **My phase-02 risk note is factually
wrong**: it says "sem-metrics vary only with the test set" — they don't depend on the test set at all.
**Flaw:** reporting QuAcq-active as mean±std over 3 folds shows `sem_f1 = X ± 0.000` → reads as broken CV /
misreport next to per-fold-trained conditions (evaluation.tex:75 = mean±std protocol).
**Disposition:** ACCEPT → correct the claim; report QuAcq-active structural metrics as a **single value**
(not CV mean±std), clearly separated; only accuracy/tp/tn/fp/fn/specificity legitimately vary by fold.

### H-2 · No empirical evidence oracle-mode beats example-only; acceptance validated only on the smallest KB
**Reviewers:** Assumption + Sci-Validity. **Evidence:** oracle-mode tests assert only `convergence_reason ∈
{…}` and tolerate empty KB (`if result.kb_assumption_ids:` test_quacq.py:418); no `n_kb>0`/F1 assertion;
no oracle-mode result anywhere in `data/results_conmin/`. REAL-FM-7_ff test fold = 2 pos/1 neg (accuracy on
3 points is noise); "materially higher" has no threshold/test.
**Disposition:** ACCEPT (merges with C-1) → concrete sem-F1 threshold + go/no-go on ≥1 mid-size KB before
the busybox sweep.

### H-3 · Timeout/max_queries partial-KB rows are averaged into the CV mean as if converged — no failure flag
**Reviewer:** Failure-Mode. **Evidence:** `ok = [r for r in grp if 'error' not in r and 'gate_tripped' not
in r]` (conmin_cv_evaluator.py:308) — a `'timeout'`/`'max_queries'` row passes as ok; `n_failed` unaffected;
`convergence_reason` not in `_AGG_COLS` → invisible in `conmin_eval_cv.csv`.
**Scenario:** busybox partial-KB low sem-F1 published as the method's converged score.
**Disposition:** ACCEPT → `aggregate_cv` counts `n_timeout`/`n_maxq` per group AND/OR excludes non-converged
QuAcq-active rows from the mean like `error` rows.

### H-4 · max_queries=5000 < busybox |B|=6635, and is a SHARED counter drained by FindScope/FindC
**Reviewer:** Failure-Mode. **Evidence:** single `n_queries`/`record_query` shared by main+FindScope+FindC
(quacq.py:144-153); each learned constraint costs main-query + a full FindScope descent (~10–20 queries on
854 vars, findscope.py:64) + FindC; `record_query` no-ops past cap while `findscope.py:64` still solves
(cap isn't even a hard solver-load bound). |B|=6635 > 5000.
**Scenario:** busybox exhausts 5000 after a small fraction learned → `max_queries` + low F1 → still crippled
on the KB reviewers scrutinize.
**Disposition:** ACCEPT → size budget to model (`~c·|B|` or per-KB override) + acceptance gate "busybox
reaches `empty_bias`/`no_query`, not `max_queries`." NOTE the tension with C-2 (more queries widens the cost
asymmetry) — surface to CW Main.

### H-5 · "Uniform column ⇒ clean --merge" is false: 24–26 committed JSONs lack the column
**Reviewers:** Failure-Mode + Sci-Validity. **Evidence:** `--merge` globs ALL `*_eval.json`
(run_conmin_eval.py:56) incl. Jul-23 committed rows without `convergence_reason`; `schemas =
{tuple(sorted(r.keys()))}` (…:68) → `len>1` → "re-run affected KB(s)" warning (…:69-72). Column added at
`_cost` (…:253-279). Also fixes the "byte-identical" wording (it's value-identical + 1 additive column;
phase-04:78-79 already concedes dropping the column before diffing).
**Disposition:** ACCEPT → either make `_merge_per_kb` tolerant (union columns, blank-fill missing key before
schema compare), or backfill committed JSONs in the same change; update RUN.md so the warning isn't read as
"re-sweep." Correct "byte-identical" → "value-identical + 1 additive column" throughout.

### H-6 · Recommended per-(KB,es) hoist re-learns the identical theory 6× per KB (wrong cut)
**Reviewers:** Assumption + Sci-Validity. **Evidence:** theory = f(bias, FM); `model.bias`/`model.oracle`
are per-KB, passed identically for all 6 example-sets (run_conmin_eval.py:143, es-loop :136). Recommended
hoist runs once per `evaluate_kb_example` = 6 identical learns/KB (≤6×400 s busybox waste). Truly-minimal =
learn-once-per-KB (demoted to "further lever", plan.md:74-76).
**Disposition:** ACCEPT → make **learn-once-per-KB** (apps-layer cache across the es-loop) the committed
default, OR the per-fold clone if audit-simplicity is preferred; drop the 6×-redundant middle option. Also
closes the "punted decision #1" (Sci-Validity F-9).

### H-7 · Cleanup-on-exception only in prose, never pinned into steps → leaked persistent SAT solvers
**Reviewer:** Failure-Mode. **Evidence:** `run()`'s `finally` cleans only the checker
(quacq_runner.py:198-204); the oracle is released only by `runner.cleanup()` (base_runner.py:99-103,
oracle.py:163-167); phase-02 pseudocode (…:89-97,127) shows `cleanup()` on the happy path, `finally` only as
a risk-section aside; the "sentinel on exception" branch is exactly where a naive try/except skips cleanup.
**Scenario:** busybox `run()` raises → cleanup skipped → FMOracle PySAT solver leaks; ×(KB×6 es) → FD/mem
exhaustion late in the sweep.
**Disposition:** ACCEPT → specify `try: res = runner.run(...) finally: runner.cleanup()` (sentinel built
after finally) as a checkbox in Implementation Steps.

---

## MEDIUM

### M-1 · Soft-ceiling timeout understated — "FindScope is O(log|vars|)" is false
**Reviewers:** Assumption + Failure-Mode. **Evidence:** FindScope double-recurses (findscope.py:84-85,
`O(|S|·log|X|)`, oracle solve per node :64) + FindC O(k²) (findc.py:83-86,117-142); deadline checked only at
outer-loop top (quacq.py:159-163). One overrun = a whole FindScope+FindC, minutes on busybox — not "one
solve." **Disposition:** ACCEPT → fix wording; measure a worst-case single-iteration on a mid-size KB before
claiming 400 s is "generous"; feasibility "≤40 min busybox" is a floor not a cap.

### M-2 · Example-only QuAcq's real convergence_reason is silently blanked — discards the key diagnostic
**Reviewer:** Assumption. **Evidence:** example-only run yields `pool_exhausted`/`empty_bias`/`max_queries`
(quacq.py:186-190,245-247), available at conmin_cv_evaluator.py:227/234, currently unused; plan blanks it.
**Disposition:** ACCEPT → also pass `convergence_reason=res.convergence_reason` from `_eval_quacq_fold`
(1 line) so the "why crippled" (`pool_exhausted`) is recorded — strengthens the report.

### M-3 · "No shared mutable state" is inaccurate (global profiler singleton; two live oracles)
**Reviewer:** Failure-Mode. **Evidence:** `profiler_session` swaps a module-global `gprofiler` with no
restore (profiling/registry.py:84-90); both runner (quacq_runner.py:158) and each ConMin fold
(conmin_cv_evaluator.py:118) open sessions; evaluator's FMOracle (…:52) + runner's FMOracle (base_runner.py:84)
are live concurrently. (RNG concern refuted.) **Disposition:** ACCEPT → correct the claim; release the
runner's oracle before the fold loop to avoid the 2× solver peak on busybox (aligns with H-6 learn-once-per-KB).

### M-4 · Smoke command overwrites the committed baseline it must be diffed against
**Reviewer:** Failure-Mode. **Evidence:** first smoke cmd (phase-04:51) has no `-o`, QuAcq-active ON →
`write_json_atomic`/`_write_csv` overwrite committed REAL-FM-7 artifacts (run_conmin_eval.py:147,155); the
non-destructive `-o /tmp` pattern is only on the second command (phase-04:76). **Disposition:** ACCEPT →
route EVERY smoke command through `-o /tmp/qa_check_active`; diff read-only vs committed baseline; keep git
clean throughout.

---

## Cross-cutting conclusions
- **Biggest risk is not a mechanism bug — it's the premise (C-1).** Cheapest correct next move = a
  go/no-go smoke on REAL-FM-7 + one mid-size KB, reconciled against `paper/evaluation.tex` example-first
  numbers, BEFORE any timed sweep. If oracle-mode doesn't clear the paper's example-first band, the
  condition is informational-only (a fairness caveat), not a "fixed strawman."
- **Three fairness criticals (C-1/C-2/C-3) are paper-policy calls → CW Main**, per the plan's own
  "Note to Viet-Man". Don't silently resolve them in the plan.
- **Reproducibility (C-4) + budget (H-4) fixes fight the fairness axis (C-2):** a fair *active* baseline
  needs enough queries to converge deterministically, which widens the cost gap. That tension is the core
  decision to escalate.
- Mechanism fixes (H-3, H-5, H-6, H-7, M-2, M-3, M-4) + factual corrections (H-1, M-1) are unambiguous and
  should be folded into the plan regardless of the methodology outcome.

## Unresolved questions
1. What `max_queries` did the paper's example-first runs use? If already ≥1000, C-1 hardens.
2. Which paper table consumes `data/results_conmin/`? `paper/tables/*` appears generated from `data/results`
   (ConGen dir); confirm where the QuAcq-active column lands before assuming a mean±std table exists.
3. On busybox, does `max_queries` (5000) or `timeout` (400 s) fire first? Decides whether C-4 (nondeterminism)
   or H-4 (crippled-but-deterministic) governs — needs one measured mid-size run.
