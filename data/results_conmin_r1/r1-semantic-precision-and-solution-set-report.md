# AAAI-27 revision — corrected semantic tier, precision formulas, solution-set P/R

2026-10-25 · code = tag `conmin-aaai-data` (fd84762) + uncommitted r1 changes · derived data; the
submitted numbers in `data/results_conmin/` are unchanged · provenance: `PROVENANCE.md`.
Measured: KB₁ REAL-FM-7, KB₂ fqa, KB₃ arcade-game, KB₄ REAL-FM-4. KB₅ busybox: bounds only.
Aggregation = Table 5 (`eval-prf`): exclude 2-COV, ConMin raw k=1, fold means, † = non-converged.
Re-learned KBs reproduce every gated committed column: **480 records, 0 mismatches**.

## 1. Corrected semantic tier — both contracts, both precision formulas

Two corrections of the semantic tier (description, clause, exact_equiv, accuracy unchanged):
(1) root axiom missing from the premise (`conmin_slice_scorer.py:59` → `kb_comparator.py:297-298`
at fd84762); (2) precision TP_ct/(TP_ct+FP_kb) mixes populations (`kb_comparator.py:312-314` +
`metrics.py:48-57`); standard P_std = TP_kb/(TP_kb+FP_kb). Empty KB: P_std "—", F1_std = 0.

P/R/F1 at 2 dp, bold = row max F1 (as Table 5):

| KB | view | A | C | ConMin (C∪S) | QuAcq-ex | QuAcq |
|---|---|---|---|---|---|---|
| KB₁ | submitted (P_code, bg=[]) | .49/.95/.60 | .87/.11/.19 | .80/.90/**.85** | .13/.01/.01 | 1.00/.73/.84 |
| | P_code, bg=root | .50/1.00/.62 | 1.00/.39/.56 | .81/.96/.88 | 1.00/.28/.44 | 1.00/1.00/**1.00** |
| | **P_std, bg=root** | .71/1.00/.81 | 1.00/.39/.50 | .78/.96/.86 | 1.00/.28/.06 | 1.00/1.00/**1.00** |
| KB₂ | submitted | .77/1.00/**.87** | .91/.05/.09 | .89/.75/.78 | .80/.01/.02 | 1.00/.03/.06† |
| | P_code, bg=root | .77/1.00/**.87** | .98/.06/.11 | .89/.75/.78 | 1.00/.03/.05 | 1.00/.04/.07† |
| | **P_std, bg=root** | .83/1.00/**.90** | .97/.06/.11 | .89/.75/.78 | 1.00/.03/.05 | 1.00/.04/.07† |
| KB₃ | submitted | .24/.99/.38 | .88/.02/.05 | .55/.84/**.64** | .93/.01/.02 | 1.00/.29/.45† |
| | P_code, bg=root | .25/1.00/.38 | .96/.07/.12 | .56/.86/**.65** | 1.00/.04/.07 | 1.00/.42/.59† |
| | **P_std, bg=root** | .32/1.00/.47 | .94/.07/.12 | .52/.86/**.62** | 1.00/.04/.07 | 1.00/.42/.59† |
| KB₄ | submitted | .49/1.00/.64 | .46/.02/.03 | .79/.81/**.78** | .87/.01/.02 | 1.00/.10/.18† |
| | P_code, bg=root | .49/1.00/.64 | .60/.02/.04 | .80/.84/**.80** | 1.00/.02/.03 | 1.00/.13/.23† |
| | **P_std, bg=root** | .59/1.00/.73 | .49/.02/.04 | .78/.84/**.80** | 1.00/.02/.03 | 1.00/.13/.23† |
| KB₅ | submitted | .60/1.00/.73 | .92/.01/.02 | .80/.87/**.83** | 1.00/.01/.01 | 1.00/.02/.04† |
| | P_std, bg=root (bounds) | [.75,.98]/1.00/[.85,.99] | [.83,.98]/[.45,1]/[.52,.99] | [.77,.98]/[.87,1]/[.81,.99] | 1.00/[.45,1]/[.62,1] | 1.00/[.45,1]/[.62,1]† |

KB₁ QuAcq-ex: 13 of 15 folds learn an empty KB, so P_std averages 2 folds while F1_std (0 on
empty KBs) averages 15 — hence 1.00/.28/.06. Full numbers incl. bg=[] × P_std and the C∪S k-sweep:
`semantic_precision_formulas.csv`; KB₅ bounds: `semantic_bounds_busybox-1.18.0.csv`.

**Which formula Table 5 reports:** the code formula P_code = TP_ct/(TP_ct+FP_kb), contract
bg = []. The text never states a precision formula; it says the tier "demands the same solution
set, checked per constraint by bidirectional entailment" (main_short.tex:428), which reads as
P_std (learned constraints entailed by Cτ). Text and table therefore disagree on precision.

**A → ConMin precision gap (P_std, bg=root vs submitted):** KB₁ +.31 → **+.07** (.71→.78);
KB₂ +.12 → +.07 (.83→.89); KB₃ +.31 → +.20 (.32→.52); KB₄ +.30 → +.19 (.59→.78); KB₅ undecidable
(A [.75,.98] vs ConMin [.77,.98]). The gap narrows on every measured KB.

**"ConMin raises semantic precision from .49 to .80 on KB₁":** not a sentence of the submitted
main_short.tex/appendix.tex — only Table 5's KB₁ P cells. Under P_std with the corrected
contract it becomes **.71 → .78**; the direction survives, the size does not.

**Bold markers:** KB₁ moves ConMin → QuAcq (1.00) under both corrected views; KB₂ (A), KB₃
(ConMin), KB₄ (ConMin) unchanged; KB₅ undecidable from bounds under P_std (even with bg=[]).

## 2. Solution-set precision / recall (exact model counting)

| KB | A | C | ConMin k=1 | k=2 | k=3 | k=5 | QuAcq-ex | QuAcq |
|---|---|---|---|---|---|---|---|---|
| KB₁ solP / solR | 1 / .338 | .020 / 1 | .780 / .372 | .544 / .497 | .433 / .728 | .198 / 1 | .010 / 1 | 1 / 1 |
| KB₂ | 1 / .0076 | 1e-26 / .951 | .243 / .0093 | .013 / .144 | 4e-4 / .314 | 7e-7 / .461 | 3e-27 / 1 | 2e-27 / 1† |
| KB₃ | 1 / 3.0e-6 | 4e-10 / .916 | .507 / 8.9e-5 | .386 / .030 | .290 / .147 | .200 / .309 | 3e-10 / 1 | 2e-6 / 1† |
| KB₄ | 1 / 8.9e-7 | 6e-38 / .321 | .163 / 1.2e-6 | .076 / 1.7e-4 | .044 / .058 | .0013 / .072 | 2e-37 / 1 | 2e-32 / 1† |

Exact-equivalence rate: KB₁ A .07, ConMin .07 (k = 1…5), QuAcq 1.00, all others 0; KB₂–KB₄ 0 for
every condition. C ⊆ S_full (k=1) on KB₁ 15/15, KB₂ 11/15 (mean |C∖S_full| .27), KB₃ 15/15,
KB₄ 10/15 (.33). Counter: pysdd 1.0.6 + exact big-integer count; 480 theories in 12.1 s.

## 3. Verdict

ConMin does **not** materially improve solution-set recall over A at k=1: .338→.372 on KB₁, and
on KB₂–KB₄ both stay ≈ 0 (.0076→.0093, 3e-6→9e-5, 9e-7→1.2e-6) — every learned theory on the
larger KBs still rejects almost all valid configurations. The cost is solution-set precision:
A is sound by construction (1.0 on every fold), ConMin k=1 drops to .78/.24/.51/.16, i.e. it
accepts invalid configurations without recovering valid ones. Larger k does raise recall
(KB₁ 1.0 at k=5, KB₂ .46, KB₃ .31, KB₄ .07) at a further precision cost (KB₁ .20, KB₂ 7e-7,
KB₄ .001); no k reaches both. On the corrected semantic tier, sentences of main_short.tex that
are falsified: l.436 "matches or exceeds the active baseline on semantic recovery on all five"
(KB₁ .86–.88 vs 1.00; KB₅ undecidable); "narrowest … 0.85 against 0.84 on KB₁" and l.438 "0.85
against 0.84 on meaning" (→ .88/.86 vs 1.00); "widest on KB₅, 0.83 against 0.04†" (QuAcq ≥ .62);
"QuAcq-ex … semantic F1 between 0.01 and 0.02" (→ .03–.44 with P_code, .03–.07 with P_std);
"improves on the semantic F1 of the maximally specific pool on every KB but KB₂" holds on KB₁,
KB₃, KB₄ but is undecidable on KB₅ under P_std. l.428 "the semantic tier demands the same
solution set" is not what the tier measures: ConMin's semantic R .84 on KB₄ coexists with
solution-set recall 1e-6.

## 4. UNSAT delivered theories — own category (correction 3, pending)

`consistency_check.csv` (828 folds: 576 AAAI-27 persisted theories incl. 2-COV, 252 SoSyM-R1
stored folds). UNSAT is reported as its own category here; it is **not** folded into either
precision formula and no score was changed.

| paper | condition | sampling | UNSAT / folds | where | UNSAT without NE | sem R of UNSAT folds |
|---|---|---|---|---|---|---|
| AAAI-27 | A (maximally specific) | 2-COV | 5 / 12 | KB₁ 3/3, KB₃ 1/3, KB₄ 1/3 | 5 / 5 | 1.000 (all) |
| SoSyM-R1 | ConGen | 2-COV | 8 / 15 | KB₁ 3/3, KB₃ 1/3, KB₄ 1/3, KB₅ 3/3 | 6 / 8 | 1.000 ×6; .818, .238 (NE-induced) |
| both | every other condition × sampling | — | 0 | — | — | — |

- **Every UNSAT fold has n_train_pos = 0.** Not every n_train_pos = 0 fold is UNSAT (AAAI A 5/8,
  SoSyM ConGen 8/11); no C, C∪S (any k), QuAcq-ex, QuAcq-active, example-only or example-first
  theory is UNSAT.
- **sem R = 1.000 for every theory that is UNSAT without NE** (11/11): an UNSAT theory entails
  every clause. The 2 SoSyM folds that become UNSAT only through the stored NE clauses score
  R .818 / .238, because the semantic tier scores learned clauses ∪ bg without NE.
- Learned clauses alone and NE ∪ root are satisfiable in all 13 folds — the contradiction only
  appears with the root axiom. Exact model counts agree (#T = 0 for exactly the 5 AAAI folds).
- Accuracy on these folds is uninformative: their test folds hold 0–1 positives, so a theory
  rejecting every configuration scores .833–1.000.

**AAAI-27 cells containing UNSAT folds.** Table 5 (`eval-prf`), the cost table, app-accuracy,
app-checks, app-ksweep and app-rawred exclude 2-COV: **unaffected**. Affected (all samplings):
`app-perset` A column KB₁ (3 of 18 folds), KB₃ (1/18), KB₄ (1/18); `app-confusion` A columns,
same folds. Sentence: appendix.tex:509-516 "Table~\ref{tab:app-perset} repeats the main table
over all available samplings, so it adds the 2-COV folds … The maximally specific pool falls in
the same direction on all five" — the A side of that comparison includes UNSAT theories.
main_short.tex quotes no 2-COV A number.

**SoSyM-R1 cells containing UNSAT folds** (ConGen, 2-COV): `tab:comparison_strategies`
KB₁ (l.813, 3/3), KB₃ (l.827, 1/3), KB₄ (l.834, 1/3), KB₅ (l.841, 3/3); `tab:iterative_semantic`
ConGen 2-COV row (l.927: .849, .705, .930, .997); `tab:iterative_accuracy` ConGen 2-COV (l.889);
`tab:accuracy_all` 2-COV row (l.756); `tab:fm_summary` 2-COV |KB| (l.784). Sentences:
- l.149 (abstract): "Its semantic F1-scores … range from 0.580 to 0.997" — the 0.997 maximum is
  KB₅ 2-COV, 3/3 folds UNSAT.
- l.762: "2-wise coverage (2-COV) yields the highest accuracy on every knowledge base, reaching
  $1.000$ on $KB_1$, $KB_2$, and $KB_5$ …" — KB₁ and KB₅ are UNSAT theories on test folds without
  positives.
- l.790: "For $KB_1$, the final $|KB|$ ranges from $9$ (2-COV) …" and "… to $99.9\%$ ($KB_5$,
  2-COV)" — sizes of UNSAT theories.
- l.846: "On $KB_1$ and $KB_5$, the description-based F1 is $0.000$ while the semantic F1 reaches
  $0.849$ and $0.997$" — both cells entirely UNSAT.
- l.1039: "The 2-COV strategy yields the highest accuracy on every knowledge base … its median
  advantage of $0.045$ in semantic F1 over random sampling" and "(4) … by up to $0.997$ in F1
  ($KB_5$ under 2-COV …)".
(l.676 already warns that a theory rejecting every configuration reaches accuracy 1.000 on
2-COV test folds — that is exactly what these theories are.)

## 5. Solution-set ratios — distribution, not one summary

`solution_set_distribution.csv` gives n, mean, median, geometric mean (positive folds),
min/q1/q3/max per KB × strategy; `figures/solution_set_log_scale.png` plots every fold on a log
axis. The summaries diverge by orders of magnitude, e.g. ConMin sol_recall on KB₄: mean 1.2e-6,
median 7.7e-9, geometric mean 2.3e-10, range [1.3e-16, 1.3e-5]; on KB₂ sol_precision: mean .24,
median 7.5e-4, geometric mean 1.6e-6. No zero or undefined value occurs in the Table-5
selection (UNSAT occurs only on 2-COV). The summary for the table is not chosen yet.

## Decisions recorded

1. The revision reports P_std; the code formula stays as a separate field (`P_code`);
   PROVENANCE records that the submitted tables used the code formula.
2. Solution-set aggregation: mean, median, geometric mean and the per-fold distribution side
   by side, log scale; choice deferred to table writing.
3. Busybox deferred; `busybox_rerun.md` current (now includes a 2-COV pass).

## Unresolved questions

1. How to report the UNSAT folds (correction 3 is pending).
2. Busybox exact numbers and 854-variable model counting remain untested.
