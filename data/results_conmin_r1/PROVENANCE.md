# data/results_conmin_r1 — provenance

Derived for the AAAI-27 revision; the submitted numbers in data/results_conmin/ are unchanged.

Nothing in this directory replaces or edits `data/results_conmin/`, its `tables/`, its
`PROVENANCE.md`, the Overleaf sources or the shipped bundle. Every number here is produced by
the code in `apps/conmin_r1/` from the repository root.

## Code and inputs

| Item | Value |
|---|---|
| Code | tag `conmin-aaai-data` = commit `fd84762` (identical code to the submitted sweep), plus the uncommitted r1 changes listed below |
| r1 code | `apps/conmin_r1/` (new); `conacq/eval/kb_comparator.py` (additive field, see Correction 2); `tests/test_semantic_standard_precision.py` (new) |
| Seed | 82 (`apps/conf_conmin/run_conmin_eval_config.toml`) |
| Folds | pre-recorded `data/folds/{kb}_{es}_folds.json` (3-fold), examples `data/examples/{kb}_{es}.json` |
| Solver | glucose4 (ConMin checker, QuAcq oracle/runner, entailment checks) |
| KBs | REAL-FM-7, fqa, arcade-game, REAL-FM-4 measured; busybox-1.18.0 bounds only (re-runs deferred, `busybox_rerun.md`) |
| Samplings | ff, rs_1n, rs_2n, rs_3n, rs_m (Table 5 excludes 2cov) |
| Model counter | pysdd 1.0.6 (SDD compilation), exact big-integer count (`exact_sdd_model_counter.py`); installed env-only with `uv pip install pysdd` (uv.lock unchanged) |

## Corrections of the semantic tier (Table 5 / `eval-prf`)

Both are corrections of the **semantic tier only**. The description tier, the clause tier,
exact_equiv and accuracy are unchanged (exact_equiv and accuracy already score the delivered
theory including the root axiom; the description and clause tiers' TP is a set intersection).

1. **Root axiom omitted from the semantic premise.** `conacq/eval/conmin_slice_scorer.py:59`
   builds `ConGenResultData(..., bg_clauses=[])` for all three tiers; the semantic tier consumes it
   as the premise of KB ⊨ Cτ (`conacq/eval/kb_comparator.py:297-298` at fd84762,
   `semantic_equivalence.py:95`). Cτ (`ground_truth.clauses`) contains the root unit, so the root
   unit and every `child → root` clause counted as missed unless learned. `bg_clauses=[]` is
   correct for the clause tier (it unions bg into the compared set,
   `kb_comparator.py:211`) — the clause tier keeps bg = [] by design. Corrected contract:
   bg = root clauses (`FMOracle.oracle_data.get_root_clauses()`), the paper's definition of the
   tier (entailment under background knowledge).
2. **Precision formula mixes populations.** `kb_comparator.py:312-314` (at fd84762) sets
   TP = Cτ clauses entailed by the KB, FP = KB clauses not entailed by Cτ; `metrics.py:48-57`
   computes TP/(TP+FP) = TP_ct/(TP_ct+FP_kb). Standard precision over learned clauses is
   P_std = TP_kb/(TP_kb+FP_kb), TP_kb = n_kb_checked − |unentailed_kb|. Recall is correct.
   Added without changing any existing field: `SemanticStandardPrecision` +
   `ComparationResult.standard_precision` (semantic tier only, same entailment call), tested in
   `tests/test_semantic_standard_precision.py`.

## Step 0 — re-learned KBs, persisted

The submitted sweep never stored learned KBs; the handoff-1 re-runs did not either. Re-learned
with the library steps of `conmin_cv_evaluator._eval_conmin_fold` (raw negatives, k ∈ {1,2,3,5},
one Stage-1), QuAcq-ex (example-only, `shuffle_seed=fold`), and the per-KB QuAcq-active theory:

```bash
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.relearn_kbs_with_persistence --kbs REAL-FM-7 --learn-quacq-active --workers 4
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.relearn_kbs_with_persistence --kbs fqa arcade-game --learn-quacq-active --workers 5
    # killed by hand after fqa's QuAcq-active learn (kept); arcade's learn was aborted — imported below
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.relearn_kbs_with_persistence --kbs fqa arcade-game \
    --import-quacq-active arcade-game=scratch/rebuttal_aaai27/out/arcade-game_quacq_active_kb.json --workers 5
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.relearn_kbs_with_persistence --kbs REAL-FM-4 \
    --import-quacq-active REAL-FM-4=scratch/rebuttal_aaai27/out/REAL-FM-4_quacq_quacq_active_kb.json --workers 7
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.reproduction_gate
```

(The two imported JSONs were moved afterwards to `handoff1/`.) QuAcq-active theory per KB
(`kbs/<kb>/quacq_active.json`):

| KB | source | size | queries | stop | committed |
|---|---|---|---|---|---|
| REAL-FM-7 | learned (budget 5000 / 400 s) | 12 | 272 | no_query | 12, 272, no_query |
| fqa | learned (5000 / 400 s) | 6 | 5000 | max_queries | 6, 5000, max_queries |
| arcade-game | imported, handoff-1 learn (5000 / 7200 s) | 27 | 4264 | timeout | 27, 5000, max_queries |
| REAL-FM-4 | imported, handoff-1 learn (5000 / 20000 s) | 26 | 5000 | max_queries | 26, 5000, max_queries |

arcade-game: the handoff-1 learn stopped on the wall clock at 4,264 queries (the machine was
loaded), not on the 5,000-query rail; its theory nevertheless reproduces every gated committed
column (size, sem P/R/F1, clause F1, description F1, exact_equiv, accuracy) on all 15 folds. Both
stops are non-converged, so the Table-5 dagger semantics are the same; the aggregation uses the
committed `convergence_reason` throughout.

Record layout (`kbs/<kb>/<es>_fold<f>.json`, one record per condition and per k for C∪S):
bias-constraint names, ¬e⁻ fallback clauses (as used in the delivered theory), root clauses,
the fold's full NE clauses (negated raw training negatives), seed, fold/examples files, solver,
the shipped scores (`score_named_kb`), and for C∪S/C the cover, support and S_full names.

**Reproduction gate** (`reproduction_gate.py`): every persisted record's shipped size, sem P/R/F1,
clause F1, description F1, exact_equiv and accuracy equal the committed `conmin_eval_long.csv`
row, including C∪S k = 2, 3, 5. Result: see "Gate log" below.

## Step 0 — corrected semantic tier and precision formulas

```bash
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.semantic_tier_corrected
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.semantic_root_bounds_from_committed busybox-1.18.0
```

`semantic_precision_formulas.csv` (kb × strategy × contract: P_code, P_std, R, F1_code, F1_std,
|KB clauses|, |Cτ clauses|), `semantic_tier_corrected.csv` (submitted vs corrected),
`semantic_tier_corrected_rows.csv` (per fold), `semantic_bounds_busybox-1.18.0.csv` (bounds).
Scored through the production path `KBComparator.compare(SEMANTIC)`; the bg = [] code values are
asserted equal to the shipped values on every row. Empty KB: P_std/F1_std undefined, excluded
from the mean (`P_std_n_defined`).

## Handoff 1 (diagnosis) — moved here

`semantic-tier-missing-root-axiom-diagnosis.md`, `busybox_rerun.md`, `handoff1/` (re-run rows,
QuAcq-active JSONs, logs, text outputs). Scripts moved from `scratch/rebuttal_aaai27/` to
`apps/conmin_r1/` (`fm7_quacq_active_unentailed_clauses.py`, `root_clause_structure.py`,
`semantic_root_bounds_from_committed.py`, `handoff1_*`).

## Gate log

- 2026-10-25 02:20 — `reproduction_gate`: **480 records (REAL-FM-7, fqa, arcade-game, REAL-FM-4 ×
  5 samplings × 3 folds × {A, C, C∪S k=1,2,3,5, QuAcq-ex, QuAcq-active}), 0 mismatches.**
- Internal check in `semantic_tier_corrected`: production-path bg = [] code P/R/F1 equal the
  shipped values on all 480 rows (assert).
- Handoff-1 REAL-FM-4 QuAcq-ex / QuAcq-active completed (`handoff1/`): 30 rows, 0 mismatches.

## Empty-KB convention (decided 2026-10-25)

Empty KB: P_std undefined (reported "—", excluded from the P_std mean, `P_std_n_defined`),
F1_std = 0, the fold kept in every F1 mean and paired test. Implemented in
`SemanticStandardPrecision.f1`. Note: under the root contract an empty KB has R > 0 (root unit
and child → root are entailed by bg alone: REAL-FM-7 6/22, busybox 445/994), so F1 = 0 is a
convention, not a consequence of R = 0. The code formula keeps its historical behaviour
(P_code = 1 on an empty KB whenever bg entails a Cτ clause).

## Step 1 — solution-set precision / recall (model counting)

```bash
for kb in REAL-FM-7 fqa arcade-game REAL-FM-4; do
  PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.solution_set_model_counting count $kb; done
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.solution_set_model_counting aggregate
```

Delivered theory T = learned bias clauses ∪ ¬e⁻ fallbacks ∪ root (conmin_slice_scorer.py:67-68);
sol_precision = #(T∧Cτ)/#T, sol_recall = #(T∧Cτ)/#Cτ over the FM's feature variables. CNFs are
aux-free (every Cτ and bias variable is a feature variable, all 5 KBs), so no projection.
Counter: pysdd 1.0.6 SDD compilation (balanced vtree, auto GC + minimisation) with an exact
big-integer smoothed count (`exact_sdd_model_counter.py`), cross-checked against pysdd's double
WMC (rel. 1e-9) and against brute force on 30 random CNFs. No approximate counter was needed.
#Cτ: REAL-FM-7 80; fqa 345,113,599,559,875,744,857,599,999; arcade-game 3,299,733,576;
REAL-FM-4 ≈ 4.451e49 (291 vars). Runtime: 480 theories in 12.1 s total (max 0.9 s each).
Per-row check: sol P = R = 1 ⇔ shipped exact_equiv = 1 (assert, 480/480).
Sanity: A sol_precision = 1.0 on 60/60 folds; QuAcq-active REAL-FM-7 sol P = R = 1.0 on 15/15.
Busybox: not measured (no persisted KBs). Output `solution_set_pr.csv`, `solution_set/<kb>_rows.csv`.

## Step 2 — cover share and exact-equivalence rate

```bash
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.cover_share_and_exact_equiv
```

S = {c ∈ A ∖ C : support⁺ ≥ k} (conmin.py:252-254) is disjoint from C by construction, so the
measured inclusion is C ⊆ S_full, S_full = {c ∈ A : support⁺ ≥ 1} (support-only ablation);
C ⊆ S_full ⇔ S_full = C ∪ S (same pre-Reduce theory). Output `cover_share_rows.csv`,
`cover_share_and_exact_equiv.csv`.

## SoSyM R1 precision check (addendum point 5)

```bash
git archive feat/sosym-r1 | tar -x -C <scratch>/sosym_r1          # read-only extraction (a2c7e50)
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.sosym_r1_precision_check <scratch>/sosym_r1
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.sosym_r1_significance_rescored <scratch>/sosym_r1
```

Stored SoSyM folds already carry bg_clauses = [[1]] (= root for all 5 FMs) and SoSyM's
run_compare passed them, so the root contract is the as-submitted one; as-submitted P/R/F1
reproduce per fold (252 folds, 0 mismatches). Only the precision formula changes SoSyM numbers.
Significance re-run with the feat/sosym-r1 procedure (exact Wilcoxon, ties counted, Holm).
Output `sosym_r1_precision_check.{csv,md}`, `sosym_r1_significance_rescored.csv`. No SoSyM result
directory or manuscript was modified.

## Tests

`PYTHONPATH=. uv run --no-sync pytest tests/ -q`: all pass except two pre-existing failures at
fd84762 (= conmin-aaai-data), unrelated to r1: `test_make_tables.py::
test_render_latex_booktabs_dagger_thousands_bold` and `::test_prf_compact_drops_leading_zero_
and_keeps_bold_and_dagger` expect math-mode daggers; fd84762 switched make_tables to text mode
without updating them. New: `tests/test_semantic_standard_precision.py` (6 tests).

## Decisions recorded 2026-10-25

- **Precision formula of the revision: P_std = TP_kb/(TP_kb+FP_kb)** (what the paper's text
  defines). The submitted tables (`data/results_conmin/tables/`, Table 5 `eval-prf` and the
  semantic appendix tables) used the code formula TP_ct/(TP_ct+FP_kb). The code formula stays
  available unchanged (`EvaluationMetrics.precision`, CSV column `P_code`); P_std is the additive
  `ComparationResult.standard_precision` (CSV `P_std`). No field was removed or renamed.
- **Solution-set aggregation:** not chosen yet. `solution_set_distribution.py` reports mean,
  median, geometric mean (positive folds; zeros and undefined counted separately) and
  min/q1/q3/max side by side → `solution_set_distribution.csv`; every fold on a log axis →
  `figures/solution_set_log_scale.png`.
- **Busybox:** deferred to the revision; `busybox_rerun.md` kept current.

## Correction 3 (PENDING) — delivered theories inconsistent with the root axiom

```bash
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.relearn_kbs_with_persistence --es 2cov --workers 6
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.reproduction_gate          # 576 records, 0 mismatches
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.consistency_check <scratch>/sosym_r1
```

The 2-COV folds (excluded from Table 5) were re-learned and persisted for this check only, same
runner and gate (576 records incl. 2-COV, 0 mismatches). Per fold, SAT checks of delivered
theory ∪ root, learned ∪ root (no NE), learned alone, NE ∪ root (`consistency_check.csv`;
scoring unchanged). Result: **13 of 828 folds UNSAT with root — all 2-COV, all with
n_train_pos = 0**: AAAI-27 condition A 5/12 (KB1 3/3, KB3 1/3, KB4 1/3; UNSAT already without
the fallbacks); SoSyM-R1 ConGen 8/15 (KB1 3/3, KB3 1/3, KB4 1/3, KB5 3/3; 6 UNSAT without NE,
2 only once the stored NE clauses are added). No C, C∪S (any k), QuAcq-ex, QuAcq-active,
example-only or example-first theory is UNSAT. The exact model counts agree: #T = 0 for exactly
the 5 AAAI A folds. An UNSAT-without-NE theory entails every Cτ clause (sem R = 1.000 on all 11);
the 2 NE-induced ones score R .818 / .238 because the semantic tier excludes NE. Learned clauses
alone and NE ∪ root are each satisfiable in all 13: the contradiction needs root. Likely mechanism (not
measured): acquisition runs without the root axiom, and with no positive example the MSS keeps
mutually contradictory candidates that only clash once root is asserted. Status: pending — how to report these folds is not decided; no scoring changed.

### Correction 3 — reporting rule and method-level fix (decided 2026-10-25)

- **Reporting:** UNSAT is a separate category. An UNSAT delivered theory is never scored (no
  P/R/F1 assigned) and never dropped silently: every aggregate containing UNSAT folds is the
  mean over the consistent folds, annotated "(n UNSAT)"; a cell whose folds are all UNSAT is
  "—" and its pair leaves the paired tests. Implemented in `theory_consistency.py`, applied in
  `sosym_r1_precision_check.py`, `sosym_r1_significance_rescored.py` and the 2-COV part of the
  Reduce(A) ablation. Table-5-based aggregates contain no UNSAT fold (all UNSAT are 2-COV).
- **Method fix adopted for the revision:** a consistency gate after Stage 1 —
  fail(unusable) if A ∪ BG ∪ root is inconsistent — applying to A (AAAI-27) and ConGen (SoSyM).
  ConMin's C ∪ S: observed never UNSAT (0 of 288 persisted C∪S theories, k = 1, 2, 3, 5, incl. 2-COV); the
  rationale given is that ConMin returns the cover when S is empty. This is an observation, not
  a proof: C ⊆ A, so a cover could in principle clash with root as A does.

## Reduce(A) ablation (eSpW W2/Q3)

```bash
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.reduce_a_ablation --workers 7       # 72 folds, ~30 s
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.reduce_a_ablation_report
```

No re-learning: the task is re-prepared (`prepare_task`, minimize=False, no Stage 1), persisted
A names are mapped to assumption ids, and ConMin's own `Reduce.reduce(ids, [], task.set_b,
task.negation_map)` runs (BG = task.set_b, root outside — the `finish_kb` call). Primary order
S_full∖C → C → rest of A; pool order recorded for sensitivity (same size on all 72 folds, identical set on 63).
Gate: A and ConMin k=1 re-scored through the ablation path equal the persisted shipped scores on
72 folds (desc F1, sem P/R with bg=[], exact_equiv, accuracy). Asserted on every fold: exact
model counts of Reduce(A) and Reduce(A) ∧ Cτ equal A's. UNSAT rule applied (2-COV: KB₁ 3/3,
KB₃ 1/3, KB₄ 1/3 A and Reduce(A) folds flagged, not scored). Outputs `reduce_a/`,
`reduce_a_ablation.csv`, `reduce_a_ablation_summary.csv`, `reduce_a_ablation.md`.
Positive-scarcity view (2026-10-25): `reduce_a_binned_view.py`, called by
`reduce_a_ablation_report`, adds to `reduce_a_ablation_summary.csv` the 2-COV comparison and
the Table-5 folds in thirds of n_train_pos (within KB, 5 folds each, sorted by n_train_pos,
sampling, fold) with Stage 2's share (Reduce(A) − ConMin)/(A − ConMin) for |KB| and sem
P_std; shares with |A − ConMin| < 0.01 are not reported (flagged: KB₂ high third, P_std,
|A − ConMin| = 0.002). It regenerates the section between the BEGIN/END markers of
`reduce_a_ablation.md`; sol P/R shown as mean (median).

## Step 4 — dead features

```bash
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.dead_features --workers 7      # 72 folds, ~1 min
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.dead_features_report
```

Inputs: persisted Reduce(A) (`reduce_a/`) and records (`kbs/`), KB₁–KB₄, all samplings incl. 2-COV;
Cτ and root from the FM oracle; glucose4 throughout; no re-learning. Code: `dead_features.py`
(entry point, per-fold pipeline), `dead_features_sat.py` (selector-guarded incremental solver,
aggregated dead/core detection, QuickXPlain, HS-tree diagnosis), `dead_features_report.py`
(aggregation; regenerates the section between the markers of `dead_features/dead_features.md`).
`reduce_a_ablation.py` gained `load_fold` / `reduce_names` (extracted from `run_fold`; all 72
`reduce_a/` outputs byte-identical after the refactor) and `reduce_a_binned_view.py` gained
`thirds_by_positives` (summary CSV and markdown byte-identical). Gate: A and ConMin k=1 re-scored
through the Step-4 path equal the persisted shipped scores on 72 folds, 0 mismatches. Every fold
asserts #models(Reduce(A)) = #models(A). FastDiag replaced by a breadth-first HS-tree diagnosis
(FastDiag's precondition — background alone satisfies every test case — fails: root accepts every
training e⁻). Added theory UB_A = Reduce(A ∖ X) because UB (repair after Reduce) loses soundness on
36 of 67 consistent folds. Outputs: `dead_features/<kb>/<es>_fold<f>.json`,
`dead_features/dead_features_constraints.csv`, `dead_features/dead_features.md`.

## Step 5 — uniform positives

```bash
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.uniform_positives_sampler validate      # χ², REAL-FM-7
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.uniform_positives --kbs REAL-FM-7 fqa arcade-game --workers 5
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.uniform_positives --kbs REAL-FM-4 --variants original uniform_n --workers 6
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.uniform_positives_report
```

Exact uniform sampler over sol(Cτ ∪ root) by top-down SDD sampling (`uniform_positives_sampler.py`;
`ExactSddCounter.count_over` extracted from `count` for it — all 576 persisted model counts
re-verified identical). Validation on REAL-FM-7 (80 solutions): 8,000 draws χ² = 99.86, df 79,
p = 0.057; confirmation 80,000 draws p = 0.63 (seed 82) and 0.83 (seed 83)
(`uniform_positives/sampler_validation.json`). Learning through the library path
(`uniform_positives_learn.py`); per-run pipeline `uniform_positives.py`; aggregation
`uniform_positives_report.py` (regenerates the section between the markers of
`uniform_positives/uniform_positives.md`). Seeds `82 + fold`, nested draws. Gate: with the original
positives the re-learn reproduces the persisted Reduce(A) names and 10 score columns (Reduce(A) and
ConMin k=1) on 72 folds, 0 mismatches. Scope decided 2026-10-26: KB₁–KB₃ all variants; KB₄
`original` + `uniform_n` only (Stage 1 with 696 uniform positives > 2 h for one fold; one probe
`uniform_4n` file kept, reported as partial). Timing: KB₁ 8 s, KB₂/KB₃ ~2.5 h wall on 5 workers,
KB₄ 2 h 27 min wall on 6 workers (rs_3n folds ~1 h original, longer uniform).

## Reduce order ablation (eSpW Q3 follow-up) — revision / CC report only

```bash
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.reduce_order --workers 7        # 72 folds, < 2 min
PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.reduce_order_report
```

Inputs: persisted A, C, C∪S (k = 1, 2, 3, 5) and fallbacks (`kbs/`), persisted A′ = Reduce(A)
(`reduce_a/`); KB₁–KB₄, all samplings incl. 2-COV; raw negatives; no re-learning. Code:
`reduce_order.py` (task re-prepared via `reduce_a_ablation.load_fold`, which now also returns the
`model`; ConMin's own `_compute_cover` on A and on A′ in A's pool order, then `finish_kb` per k on one
checker), `reduce_order_report.py` (CSV + generated section of `reduce_order.md`). Gate: O1
recomputed from the persisted A reproduces the persisted cover and the persisted C∪S names and
fallbacks on 72 folds × 4 k, 0 mismatches. Asserted/recorded: finish_kb's Reduce on C′ ∪ S′ ∪ F′
removes no bias constraint (0 of 288 O2 runs); every target constraint removed by Reduce is entailed
by the kept theory (all cells). Outputs: `reduce_order.csv` (576 rows), `reduce_order.md`,
`reduce_order/<kb>/<es>_fold<f>.json`. Not quoted in the rebuttal.

## Cover and output structure (Cowork, 2026-10-26) — revision / rebuttal wording only

```bash
python3 apps/conmin_r1/cover_structure.py  > data/results_conmin_r1/cover_structure.txt
python3 apps/conmin_r1/output_structure.py > data/results_conmin_r1/output_structure.txt
```

Inputs: persisted condition C (all samplings, 72 folds, 91 cover elements) and C∪S k=1 (Table-5
folds) from `kbs/`; `data/bias/<kb>-bias.json` for operator/parent/children; `data/fms/<kb>.uvl`
for feature depth, target relations and cross-tree constraints (indentation parser inside
`cover_structure.py`; a few `A | !B` cross-tree forms are not parsed — fqa 8, arcade-game 3 —
and count as "not in target"). Description level only; no SAT, no re-scoring. Findings in
`cover_structure.md` §1–4: covers are hierarchy constraints of highest rejection degree (2/91
cross-tree); they often take the strongest candidate (alternative where the target has an
or-group, KB₄ 18/24); the non-target part of the k=1 output is dominated by cross-tree
requires/excludes (24–71%), operator neighbours are 2–8%. Used qualitatively in the eSpW (3) and
R3dC (1) boxes; no figure from these files is quoted in the rebuttal.
