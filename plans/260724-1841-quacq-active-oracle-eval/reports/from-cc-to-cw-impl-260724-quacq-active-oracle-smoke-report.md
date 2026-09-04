# CC → CW Impl — QuAcq-active oracle-mode: build + untimed gate report

Plan `plans/260724-1841-quacq-active-oracle-eval/` · branch `feat/conmin` · machine Apple M1 Pro
(8-core, 16 GB). Scope built: **Phase 1–3 + untimed Phase-4 gate** (no timed sweep). Decisions
locked: learn-once-per-KB (H-6), uniform `convergence_reason` column + `--merge` tolerance (H-5).

## Verdict: **NO-GO** — oracle-mode does not beat the strawman; it is WORSE (empirically confirms red-team C-1)

On **both** gate KBs the oracle-mode QuAcq learned **ZERO constraints** → `sem_f1 = 0.000`
everywhere, strictly below the example-only rows it was meant to fix — via **both rails**:
REAL-FM-7 exhausted `max_queries=5000` (KB=0); fqa hit the `timeout=400 s` at 2665 queries (KB=0).
The mechanism works (queries generated + oracle-answered); the algorithm just does not converge.
This matches the paper's own `example-first` (SAT-generating) result (`evaluation.tex:318,374-378,387`:
sem-F1 ≤ 0.105, **structural** cap from one-at-a-time learning + `Reduce`), only more extreme
(0.000, not 0.05). **Do NOT authorize the timed 5-KB sweep.**

## Exact invocation

```
QuAcqRunner(bias, fm, 'glucose4', query_mode='automated', max_queries=5000, timeout_s=400,
            use_incremental=True).run(mode='automated')
```
Plugged in via `_learn_quacq_active(...)` called **once per KB** in `run_conmin_eval.py`'s model
loop (H-6); the single `QuAcqRunResult` is scored on every fold's test set inside
`evaluate_kb_example`. Run untimed, output to `/tmp` (committed `data/results_conmin/` untouched).

## Gate numbers — REAL-FM-7 (14 feat, |B|=295), fold 0, per example-set

| set | example-only QuAcq sem_f1 | oracle QuAcq-active sem_f1 | paper example-first band |
|-----|--------------------------:|---------------------------:|--------------------------|
| 2cov  | 0.167 | **0.000** | 0.049–0.105 |
| ff    | 0.167 | **0.000** | |
| rs_1n | 0.000 | 0.000 | |
| rs_2n | 0.000 | 0.000 | |
| rs_3n | 0.087 | **0.000** | |
| rs_m  | 0.000 | 0.000 | |

QuAcq-active every set/fold: `n_kb=0`, `oracle_queries=5000`, `convergence_reason=max_queries`.
Example-only QuAcq: `n_kb` 0–1, `convergence_reason=pool_exhausted`. Pre-registered threshold
(sem_f1 ≥ 0.15 **and** ≥ 2× example-only, converged) → **FAIL** (0.000 on both counts, never converged).

**fqa (179 feat, |B|=459) — mid-size confirmation (18 rows each, means):** oracle QuAcq-active
sem_f1 = **0.000** (`n_kb=0`, `convergence_reason=timeout`, 2665 queries) vs example-only QuAcq
**0.0071** vs ConMin **C∪S 0.533** for context. Same NO-GO, via the timeout rail instead of
max_queries — oracle-mode is below even the crippled passive baseline and ~75× below ConMin.

## Mechanism + invariants verified (the build is correct even though the result is NO-GO)

- **QueryProvider + DiscriminatingGenerator + FMOracle exercised**: 5000 oracle queries generated
  and answered per KB (log: `Query N: answer=…, mode=oracle`). The oracle path runs end-to-end.
- **H-3 non-converged handling** (CV): QuAcq-active group shows `n_folds=3, n_ok_folds=0,
  n_nonconverged=3, n_maxq=3` and **no `sem_f1_mean` emitted** — a never-converged KB is reported
  as non-converged, never averaged in as 0.000. Passive QuAcq (`pool_exhausted`) stays in the mean.
- **Value-identical (additive change)**: A/C/C∪S deterministic columns = **0 diffs** with
  QuAcq-active ON vs OFF and vs the committed baseline. (The only non-timing diff is the
  example-only QuAcq's `oracle_queries`, which also differs baseline-vs-fresh → **pre-existing
  run-to-run nondeterminism in the passive QuAcq path, not from this change**.)
- **Provenance (C-4)**: every QuAcq-active row + JSON carries `qa_max_queries`/`qa_timeout_s`;
  `--merge` tolerates the additive columns (no false stale-schema warning against the 24–26
  committed pre-column JSONs) and warns on a provenance conflict. Unit-tested.
- **Suite green**: `PYTHONPATH=. pytest tests/ -q` → **570 passed, 1 skipped** (+10 new:
  timeout rail, aggregate H-3, merge H-5, `_cost` uniform schema).
- **Committed dir git-clean**: only `data/results_conmin/RUN.md` modified (intended, Phase 3);
  all smoke output under `/tmp`. ConGen/ConMin acquisition byte-identical.

## Feasibility (untimed observations — not a timed sweep)

| KB | #feat | \|B\| | QuAcq-active learn observed |
|---|---|---|---|
| REAL-FM-7 | 14 | 295 | fast (<1 min); 5000 q → **KB=0**, max_queries |
| fqa | 179 | 459 | one learn hit the **400 s timeout** at 2665 q → **KB=0**, reason=timeout (demonstrates the wall-clock rail; ConMin A/C/C∪S scoring for the 6 sets continues after) |
| busybox-1.18.0 | 854 | 6,635 | not run; extrapolated **hours** per single learn, and would hit `max_queries` with a tiny KB unless budget ≫ |B| — even then, structural cap ⇒ near-empty |

Worst-case iteration (M-1): a single negative-example iteration triggers a full FindScope
(double-recursion, O(|scope|·log|X|) SAT solves) + FindC — the 400 s wall-clock is a **floor** one
iteration can exceed on a big KB; `max_queries` is the only deterministic bound.

## Implications / recommendation

- **Keep both columns as informational** (per the prompt), but QuAcq-active is a *documented
  fairness caveat*, not a competitive active baseline: it self-generates queries yet learns
  nothing here. This is the paper's own `evaluation.tex` conclusion, reproduced.
- The **0-constraints-in-5000-queries** result is pre-existing oracle-path behaviour
  (`test_full_learning_small_limit` already tolerated `KB=0`), surfaced by finally running it in
  the eval — **not** introduced by this change. If CW Main wants QuAcq-active to actually compete,
  that requires investigating/fixing the oracle learning path itself (out of this plan's scope).

## Decisions for Viet-Man / CW Main (unchanged from plan; now evidence-backed)

1. Which becomes the paper's "QuAcq (active)" column — given NO-GO, recommend reporting it as an
   informational/threats-to-validity row (oracle-mode = 0.000, structural cap), keeping example-only.
2. Confirm sweep machine = Apple M1 Pro (8-core, 16 GB) — but **hold the timed sweep** pending (1).
3. **C-2/C-3 construct validity** (6 examples vs 5000 adaptive queries; oracle = grader) → CW Main.

## Unresolved questions

1. Does CW Main want the oracle learning path investigated (why KB=0 on both KBs?), or accept the
   NO-GO and report QuAcq-active as an informational/threats-to-validity row? The former is a
   separate effort (touches the pre-existing QuAcq oracle algorithm), not this plan's scope.
2. Timed sweep is **on hold** pending decision (1) — running it now would spend hours confirming
   `sem_f1=0.000` across 5 KBs. Recommend deciding (1) first.
