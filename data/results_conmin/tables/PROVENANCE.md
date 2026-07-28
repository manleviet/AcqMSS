# PROVENANCE — make_tables

- git SHA: `67946345455bbbbdb834b49229df90b0410269ac`
- aggregation: exclude-2COV=ON (headline tables); all available samplings (6 per KB; 3 on busybox-1.18.0) for app-quacq-diag, app-perset, app-confusion. Non-converged (`convergence_reason` in {timeout, max_queries}) excluded from the mean unless ALL folds are capped, then reported with a dagger.
- sources (per-KB `_long.csv`, authoritative; the merged CSV is a stale subset, unused):

  - `REAL-FM-7_long.csv` — mtime=2026-07-26T10:53:16.246282+00:00, n_rows=234, n_cols=61, n_samplings=6, status=loaded
  - `fqa_long.csv` — mtime=2026-07-26T10:59:13.524361+00:00, n_rows=234, n_cols=61, n_samplings=6, status=loaded
  - `arcade-game_long.csv` — mtime=2026-07-26T13:27:19.259601+00:00, n_rows=234, n_cols=61, n_samplings=6, status=loaded
  - `REAL-FM-4_long.csv` — mtime=2026-07-27T15:59:47.608662+00:00, n_rows=234, n_cols=61, n_samplings=6, status=loaded
  - `busybox-1.18.0_long.csv` — mtime=2026-07-27T10:57:12.211126+00:00, n_rows=117, n_cols=61, n_samplings=3, status=loaded

## Table variants

- **MAIN**: `eval-prf` (Semantic tier, A/C/C∪S/QuAcq-active — 16 numeric cols, NO accuracy). QuAcq example-only in `app-perset`; accuracy in `app-accuracy`.
- **APPENDIX (tier mirrors)**: `app-prf-desc`, `app-prf-clause` (same 4 strategies + aggregation + `†`/budget convention as the main table).
- appendix tables: `eval-cost`, `app-quacq-diag`, `app-perset`, `app-accuracy`, `app-confusion`, `app-checks`, `app-ksweep`, `app-rawred`.

## Audit trail

- **exact-equivalence** figures are DERIVED FROM the committed `_long.csv`, not negotiated: REAL-FM-7 ConMin attains it on **8/144 rows** but **0/48 configurations** (never across all folds of any config) — all eight attaining rows are **one fold** (RS-3n, fold 2, replicated over k in {1,2,3,5} x {raw, reduced}), which is the entire reason 8/144 is kept. A 1/18; C and QuAcq example-only 0; QuAcq-active is learned once/KB (one observation). Details in `exact-equiv.md`. `exact_equiv` (delivered theory incl. BG, via `SemanticEquivalenceChecker`) and `sem_*` (name-set only, `bg_clauses=[]`) measure different objects — the earlier 'inconsistent with sem-F1' note was a metric misread, removed.
- **genuine-drop split (G/S/R)** — QuAcq-active band-aid drops classified genuine (G) / over-strong (S) / redundant (R) by an OFFLINE entailment classification, NOT emitted by the runner. Genuine available on **$KB_1$ REAL-FM-7 (1 of 10)** and **$KB_2$ fqa (150 of 354)**; **raw only (superseded, not re-classified)** on **$KB_3$ arcade-game** (recorded 35 of 56, superseded by the fair-budget re-run — raw is now 326; per-query rate 56/863 = 0.0649 vs 326/5000 = 0.0652 confirms a longer re-run, not a counter-semantics change) and **$KB_4$ REAL-FM-4** (recorded 18 of 29 under a 400 s timeout, |KB|=15 — that run no longer exists; the current run is 196 drops at 5000 queries under a 20,000 s wall); **never measured** on **$KB_5$ busybox** (69 drops, no classification was ever run). Measured **2026-07-26**; the classification commit was not recorded. **In-repo source of record: `data/results_conmin/genuine_split.md`** — committed so this citation resolves in-repo (**traceability only**); its upstream origin is the Cowork vault findings note `ConMin - Evaluation findings (for writing).md` section A2, which the AAAI package does not ship. The two committed fairness-measurement reports under `plans/` (`from-code-reviewer-to-cw-impl-260726-fairness-measurement-redteam.md`, `from-code-reviewer-to-cw-impl-260726-quacq-active-fairness-measurement.md`) are the **PRE-FIX probe** (23 drops / 14 true on a superseded 342-query run — the 14-true figure was later found to overcount; the current post-fix run is 272 queries, `no_query`): cite them for the classification **method only**, NOT for these values. **These values remain NOT re-derivable from the committed `_long.csv`** (unlike the 8/144 exact-equivalence figures) — re-measure by re-adding the env-gated `_FAIRNESS_PROBE` hook to `quacq.py` and re-running the G/S/R entailment classification per those reports' method (no push-button script — the probe hook is reverted).
- **QuAcq-active anchoring**: REAL-FM-4 now lands on the **max_queries rail** (5000 queries under a 20,000 s wall, all six samplings uniform), so it **is** anchored (deterministic cells). busybox QuAcq-active is the **only un-anchored** KB — it ends on a wall-clock timeout (non-deterministic / non-reproducible), so its cells are reported (t(s) = timeout wall, queries = count reached) but carry no deterministic numeric anchor.

## `\input` contract (ruling 3 — NEVER write Overleaf/)

- The generator writes ONLY to `data/results_conmin/tables/`. `Overleaf/AAAI/` is a separate git clone that only Viet-Man pushes (`./sync.sh AAAI push`); an auto-written artifact there gets overwritten on pull and mixes sources — so it is NEVER touched here.
- The paper uses `\input{tables/<label>}`. Copy the files across at push time (run MANUALLY, not by this script):

  ```bash
  cp data/results_conmin/tables/*.tex Overleaf/AAAI/tables/   # then: ./sync.sh AAAI push
  ```
