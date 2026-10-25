# SoSyM R1: semantic precision re-scored from the stored KBs (2026-10-25)

> **Addendum 2 (2026-10-25) — UNSAT rule applied (supersedes the 2-COV ConGen numbers and the
> significance figures in Addendum 1).** 8 ConGen 2-COV folds are UNSAT with the root axiom
> (`consistency_check.csv`). They are not scored: cells average the consistent folds and carry
> "(n UNSAT)". `tab:comparison_strategies` / `tab:iterative_semantic` ConGen 2-COV: KB_1
> **— (3 UNSAT)**, KB_5 **— (3 UNSAT)**, KB_3 F1_std .818 (1 UNSAT), KB_4 .877 (1 UNSAT); the
> as-submitted reproduction (all folds) still matches every cell. ConGen F1_std range over the 26
> defined cells: **0.552–0.951** (abstract says 0.580–0.997; the 0.997 maximum is an all-UNSAT
> cell). Significance (pairs with an all-UNSAT cell dropped, n = 26): (i) 26/26, median 0.777,
> p 2.98e-8; **(ii) 23 of 26, median 0.352, p 9.8e-7** — losses KB_3 RS(n), RS(2n), RS(3n);
> (iii) 28/28, median 0.188; (iv) 26/26, median 0.311; 2-COV vs random n = 3, not testable.
> Under the submitted F1 with UNSAT folds removed: (i) 26/26 median 0.738, (ii) 25/26 median
> 0.387, p 1.5e-7 — so the UNSAT folds alone already break "all p < 10⁻⁷" for (ii).

> **Addendum 2026-10-25 — empty-KB rule adopted (supersedes the "undefined" / `F1_std_empty0`
> statements below).** Empty KB: P_std is reported "—" (undefined) and F1_std = 0; the pair stays
> in the tests. (Under the root contract an empty KB still has R > 0 — root unit and child→root
> are entailed by bg alone — so F1 = 0 is a convention, not a consequence of R = 0.)
> Numbers under this rule (contract = root = as submitted; regenerated CSVs):
> - `tab:iterative_semantic`: **40 of 84** F1 cells move, all down. The six example-only cells
>   that were "undefined" become **0.000** (KB_1 RS(2n)/RS(3n)/RS(m) from 0.429, KB_2 RS(m) 0.034,
>   KB_4 RS(m) 0.014, KB_5 RS(m) 0.618). Bold moves to example-first in **3** more columns:
>   KB_3 RS(n) (.630 vs .624), KB_3 RS(2n) (.564 vs .552), KB_1 2-COV (.680 vs .492).
> - Abstract/l.940 ranges: ConGen 0.492–0.951; example-only **0.000**–0.627; example-first
>   0.072–0.749.
> - `tab:comparison_strategies`: 26 of 28 P and 26 of 28 F1 cells move (max −0.653 P, −0.500 F1).
> - Significance (same procedure as feat/sosym-r1 `significance_tests.py`: exact Wilcoxon,
>   ties counted, Holm; `sosym_r1_significance_rescored.csv`). Submitted F1 reproduces the paper
>   (0.631/0.314/0.146/0.357, p = 7.45e-9). Under F1_std: (i) 28/28, median 0.767, p 7.45e-9;
>   **(ii) 24 of 28, median 0.263, p = 3.33e-6 (Holm 3.33e-6)** — losses KB_1 2-COV, KB_3 RS(n),
>   RS(2n), RS(3n); (iii) 28/28, median 0.188; (iv) 28/28, median 0.311; 2-COV vs random
>   median −0.104 (1 of 5 wins, p 0.125, n = 5 not testable). So "27 of 28" → 24 of 28 and
>   "all p < 10⁻⁷" fails for (ii) only.


Measurement only, nothing re-learned. Script: `apps/conmin_r1/sosym_r1_precision_check.py`
(`PYTHONPATH=. uv run --no-sync python -m apps.conmin_r1.sosym_r1_precision_check <extracted feat/sosym-r1>`).
Rows: `sosym_r1_precision_check.csv`, one row per printed semantic cell × contract (168 cells × 2 = 336).
Inputs: `data/results_sosym_r1/{congen,interactive}/*.json` of `feat/sosym-r1` (extracted with `git archive`,
read-only). FMs and bias files are byte-identical between that branch and this one.

## Result

**Background contract.** SoSyM did **not** have the ConMin `bg = []` defect. Every stored fold carries
`bg_clauses = [[1]]` (84 ConGen folds, 168 interactive folds), and SoSyM's `run_compare` passed it through
`ConGenResultData.from_dict`. `FMOracle(...).get_root_clauses()` gives `[[1]]` for all five FMs, so the root
contract **is** the as-submitted contract. `bg_empty` is only a counterfactual here. It would lower every cell
(recall by up to 0.972) and is not proposed.

**Reproduction.** Under `bg_root`, this branch's comparator reproduces every stored per-fold semantic P/R/F1
exactly (0 mismatches over 252 folds, tolerance 1e-9). It also reproduces all 168 printed cells at 3 dp and the
prose medians 0.631 / 0.314 / 0.146 / 0.045.

**Effect of P_std (root contract).** Recall does not change. Of the 28 ConGen P cells in Table
`tab:comparison_strategies`, 26 move, all downward, by −0.001 to −0.653. The matching 26 Sem-F1 cells move by
−0.001 to −0.500. The largest moves are on cells where the KB is small and Cτ is large: KB_5 2-COV goes from
P 0.994 to 0.341 and F1 0.997 to 0.497 (8.3 KB clauses against 994 Cτ clauses). KB_1 2-COV goes from 0.775 to
0.341 and from 0.849 to 0.492. KB_4 2-COV goes from 0.872 to 0.688 and from 0.930 to 0.807. KB_2 barely moves
(at most −0.043). In `tab:iterative_semantic`, 33 of 84 F1 cells move: the 26 ConGen cells, plus 7
example-only/first cells that move up by +0.004 to +0.031. In those 7, an empty-KB fold drops out of the mean.
Six example-only cells become **undefined** under P_std because every fold has an empty KB: KB_1 RS(2n),
RS(3n) and RS(m); KB_2 RS(m); KB_4 RS(m); KB_5 RS(m). Their printed values (0.429, 0.034, 0.014, 0.618) come
entirely from P_code = 1 on an empty KB, where the root alone entails some Cτ clauses. The CSV column
`F1_std_empty0` gives the alternative convention, F1 = 0 for an empty KB.

**Conclusions that change.** Under P_std, ConGen exceeds example-first on 23 of 28 combinations, not 27 of 28.
The new losses are KB_3 RS(n), RS(2n) and RS(3n), KB_1 2-COV and KB_5 2-COV. ConGen also loses to example-only
on KB_5 2-COV (0.497 against 0.619 over 2 defined folds). The 2-COV-versus-random median flips from +0.045 to
−0.104. Two sentences are already inconsistent with the printed numbers, whatever the formula. The
definition sentence (l. 682) describes P_std, not the P_code that the tables print. Line 1041 reads P_code 0.500
as "half of the 177 constraints are entailed", but P_code is not a share of the KB.

**Not measurable from stored data.**
* `tab:rule_learners`: semantic P/R/F1, 36 cells. `baselines.json` stores only scores and `n_rules`, not the
  learned rules.
* l. 1047 order sensitivity: `order_sensitivity.json` stores per-permutation P/R only, not the KBs.

## Sentences and cells in `main-r1.tex` that quote semantic precision or F1

"P_std" below means the root contract with the standard precision (= the corrected as-submitted contract).
The root contract alone changes nothing, because it is what SoSyM already used.

| line | quote (abridged) | changes under P_std? |
|---|---|---|
| 149 (abstract) | "semantic F1-scores … range from 0.580 to 0.997, whereas the iterative approaches reach 0.014 to 0.627 … and 0.077 to 0.749" | **Yes.** ConGen 0.492–0.951. Example-only 0.023–0.627 (6 cells undefined), or 0.000–0.627 with empty→0. Example-first 0.088–0.749 (0.072 with empty→0). The ranges now overlap. "comparable or better structural quality" weakens. |
| 185 (contrib. 4) | "reaches comparable or better structural quality as measured by semantic F1" | Qualitatively **yes**: ConGen trails example-first on 5 of 28 combinations. |
| 680 | "A constraint in Cτ is entailed if KB ∪ BG ⊨ c" | No: BG = root, which matches the code. |
| 682 | "precision is the share of the constraints of KB that are credited" | **The text already contradicts the printed P.** It describes P_std, but the tables print P_code. Fix the text, or switch the tables to P_std. Note also that P_std counts clauses, not constraints. |
| 801–844 `tab:comparison_strategies` Sem-F1 (28 cells) | | **26 of 28 move**, −0.001 to −0.500 (CSV). |
| same table, P (28 cells) | | **26 of 28 move**, −0.001 to −0.653. |
| same table, R (28 cells) | | No (0 move). |
| 846 | "semantic F1 at least as high as clause-based on every combination, and both exceed description-based" | Still true. |
| 846 | "On KB_1 and KB_5 … semantic F1 reaches 0.849 and 0.997, and on KB_2 … 0.867" | **Yes**: 0.492, 0.497, 0.838. The 2-COV "largest gap" claim no longer holds. The largest semantic-minus-description gap becomes 0.567 (KB_1 RS(3n)). |
| 846 | "Semantic precision stays below 1 on all 28 combinations, so F1 varies mainly with precision" | Still true (max P_std 0.917). |
| 860 | introduces semantic F1 (no number) | No. |
| 903–936 `tab:iterative_semantic` F1 (84 cells) | | **33 move** (26 ConGen down, 7 baseline cells up by ≤ 0.031). **6 become undefined.** Bold moves in 4 more columns, each to example-first: KB_3 RS(n) and RS(2n), KB_1 2-COV, and KB_5 2-COV (0.629). KB_3 RS(3n) was already example-first. |
| 940 | "iterative … reach 0.014–0.627 … 0.077–0.749. For KB_2, ConGen reaches 0.867–0.951 against 0.034–0.064 … and 0.141–0.202" | **Yes**: 0.023–0.627 (or 0.000); 0.088–0.749. KB_2: ConGen 0.838–0.951; example-only 0.049–0.064 (RS(m) undefined, 0.000 with empty→0); example-first unchanged. |
| 946 | "example-only … at the lowest structural quality of the three methods" | Mostly holds. Exception: KB_5 2-COV, where example-only (0.619) is above ConGen (0.497). |
| 984 / 986, `tab:rule_learners` P/R/F1 | "below 0.07 on KB_2 and KB_4, 0.138–0.163 on KB_3, 0.606–0.625 on KB_5, well below ConGen" | **Not measurable** (rules not stored). Its "well below ConGen" comparison now faces ConGen F1_std values (KB_5 RS(n) 0.821) that are still above. |
| 1034 | "exceeds … (i) on all 28 … (ii) on 27 of 28 (exception KB_3 RS(3n)), median differences 0.631 and 0.314. Oracle access (iii) … 0.146, … semantic vs description (iv) … 0.357. All four p < 10⁻⁷. … 2-COV vs random … 0.045" | **Yes.** (i) 21 of 22 defined, median 0.656, p = 1.4e-6; with empty→0: 28 of 28, 0.767. (ii) 23 of 28, median 0.263, p = 8.0e-6, exceptions KB_3 RS(n), RS(2n), RS(3n), KB_1 2-COV, KB_5 2-COV. (iii) 0.147 (n = 22) or 0.188. (iv) 0.311, 28 of 28, p = 7.5e-9. "All four p < 10⁻⁷" becomes false: three p values move to about 10⁻⁶. 2-COV vs random: −0.104 (1 of 5 wins). |
| 1039 (2) | "median advantage of 0.045 in semantic F1 over random sampling" | **Yes**: −0.104, so the sign flips. |
| 1039 (4) | "understates … by up to 0.997 in F1 (KB_5 under 2-COV)" | **Yes**: 0.567 (KB_1 RS(3n)). |
| 1039 (5) | "given an oracle they exceed ConGen on one of 28 combinations" | **Yes**: 5 of 28. |
| 1039 (5) | "Rule learners … semantic F1 well below ConGen's" | Not measurable (rules side). |
| 1039 (6) | "oracle access improves the baseline by a median of 0.146" | **Yes**: 0.147 (n = 22) or 0.188 (empty→0). |
| 1039 (7) | "precision stays below 1 on all of them" | No. |
| 1041 | "an F1 of 0.660 … only half of the 177 constraints it delivers … are entailed" | **Yes**: F1 0.624, P_std 0.460 over 233.3 clauses, so "less than half". The current wording already misreads P_code 0.500. |
| 1045 | "Logically equivalent KBs can differ in semantic F1 … report P and R alongside F1" | No number. |
| 1047 | "semantic F1 moves by 0.004 at the median … up to 0.71" | **Not measurable** (KBs per order not stored). |
| 1061 (conclusion) | "with oracle access they exceed it on one combination" | **Yes**: five. |

Recall-only claims (18 of 28 at 1.000; ≥ 0.746 / 74.6 %) do not change under P_std or the root contract.
