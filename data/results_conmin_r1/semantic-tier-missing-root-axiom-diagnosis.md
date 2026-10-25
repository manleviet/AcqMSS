# Diagnosis — semantic tier scores learned KBs without the root axiom

> Moved from `scratch/rebuttal_aaai27/` on 2026-10-25. Scripts now live in `apps/conmin_r1/`
> (step1 → `fm7_quacq_active_unentailed_clauses`, step2a → `root_clause_structure`, step2b →
> `semantic_root_bounds_from_committed`, step2 → `handoff1_*`); outputs in `handoff1/`. KB₄
> QuAcq-ex / QuAcq-active are no longer pending: F1 .02 → .03 and .18† → .23† (0 mismatches).
> Follow-up corrections and measures: `PROVENANCE.md`.

Date 2026-10-25 · branch `feat/conmin` (HEAD fd84762) · read-only on all submitted artifacts ·
scripts + raw outputs in `scratch/rebuttal_aaai27/`.

## TL;DR

- **Root cause confirmed, but it is not QuAcq-specific.** Every condition (A, C, C∪S, QuAcq,
  QuAcq-active) is scored on the semantic tier with `bg = []`, so the root unit and every
  `child → root` clause of Cτ count as "not entailed" unless the learned KB happens to contain them.
- REAL-FM-7 QuAcq-active: **6 of 22** Cτ clauses unentailed (not 3/11; same ratio .727). All six
  are `jplug` or `x → jplug`. With bg = root: **22/22, R = 1.000**, consistent with exact_equiv = 1.
- Precision side: FP counts are root-independent (identical vs Cτ and Cτ∖root on every row).
  But reported "semantic precision" = TP_ct / (TP_ct + FP_kb) mixes the two entailment
  directions, so **P moves too** when TP_ct moves.
- **Table 5 changes:** 15 of the 18 cells re-computed exactly change at 2 decimals; the KB₁
  bold winner moves from ConMin (.85→.88) to QuAcq-active (.84→1.00). This invalidates the main-text
  claim "ConMin matches or exceeds the active baseline on semantic recovery on all five"
  (main_short.tex:436) and the ".85 against .84" comparisons (l.436, l.438).
- Exact cells: KB₁–KB₄, except KB₄ QuAcq / QuAcq-active (re-run still learning at time of
  writing). KB₅ = analytic bounds only (by your decision).

## 1. Root cause (file:line)

| Path | KB side | bg | Cτ |
|---|---|---|---|
| Semantic P/R/F1 | bias clauses of the KB names | **`[]`** — `conacq/eval/conmin_slice_scorer.py:59` builds `ConGenResultData(..., bg_clauses=[])`, consumed at `conacq/eval/kb_comparator.py:298` | `ground_truth.clauses` (`kb_comparator.py:297`), a list incl. root unit and duplicates |
| exact_equiv | slice ∪ ¬e⁻ fallbacks ∪ **root** (`conmin_slice_scorer.py:67`) | root (`:71`) | `ground_truth.clause_set` |

- The `bg_clauses=[]` is deliberate (comment `conmin_slice_scorer.py:54-58`): the **clause**
  tier unions `bg_clauses` into the compared KB (`kb_comparator.py:211`), so root would count as a
  learned constraint there. One object feeds all three tiers, but in the **semantic** tier bg is
  only a premise of KB ⊨ Cτ (`semantic_equivalence.py:95`). Correct for clause, wrong for semantic.
- Brief said exact_equiv lives in `apps/run_compare.py::exact_equivalence` with
  `fold['ne_clauses']`/`fold['bg_clauses']`: no such function exists. The live code is
  `conmin_slice_scorer.py:67-72`; bg = `oracle.oracle_data.get_root_clauses()`
  (`conmin_cv_evaluator.py:81`) = the root unit only.
- Why learners miss these clauses: every positive example and every oracle-valid query has
  root = true, so `x → root` is never violated by any data → never learned/kept. Bias has no root
  unit constraint (checked, all 5 KBs).

## 2. REAL-FM-7, QuAcq-active (fold-independent; all 18 folds identical)

Re-learned: size 12, 272 queries, `no_query` = committed. Root = `jplug`. |Cτ| = 22 clauses.

| unentailed Cτ clause (bg = []) | why not entailed by KB alone |
|---|---|
| `jplug` | root unit; no bias constraint asserts it |
| `¬interface ∨ jplug` | child→root; never violated by data, not in KB |
| `¬gui_builder ∨ jplug` | same |
| `¬model_code_synch ∨ jplug` | same |
| `¬compiler ∨ jplug` | same |
| `¬diagram_builder ∨ jplug` | same |

Each is a superset of the unit `jplug` → entailed as soon as root is a premise. bg = root:
unentailed_ct = 0/22, unentailed_kb = 0/16 → semantic equivalence, matching exact_equiv = 1.
Output: `step1_output.txt`.

## 3. Affected conditions — old vs bg = root (Table 5 aggregation)

Method: re-run each Table-5 cell (exclude 2cov; ConMin raw k=1; same folds, glucose4) with a
monkeypatched scorer that emits both the shipped semantic columns and `sem_*_root`
(`step2_recompute_sem_with_root.py`). **Reproduction gate: every re-run row's shipped `sem_p/r/f1`
and `size` equal the committed CSV — 0 mismatches over 270 rows.** Aggregation via make_tables'
own `select` + `cv_mean` + `make_cell` (`step2_compare_old_vs_root.py`,
`step2_table5_two_decimal_diff.txt`). Old values reproduce published Table 5 exactly.

Semantic P / R / F1 (2 dp as printed; † = non-converged):

| KB | A old → new | C old → new | ConMin (C∪S) old → new | QuAcq-ex old → new | QuAcq old → new |
|---|---|---|---|---|---|
| KB₁ REAL-FM-7 | .49/.95/.60 → .50/1.00/.62 | .87/.11/.19 → 1.00/.39/.56 | .80/.90/**.85** → .81/.96/.88 | .13/.01/.01 → 1.00/.28/.44 | 1.00/.73/.84 → 1.00/1.00/**1.00** |
| KB₂ fqa | .77/1.00/**.87** → same | .91/.05/.09 → .98/.06/.11 | .89/.75/.78 → same | .80/.01/.02 → 1.00/.03/.05 | 1.00/.03/.06† → 1.00/.04/.07† |
| KB₃ arcade | .24/.99/.38 → .25/1.00/.38 | .88/.02/.05 → .96/.07/.12 | .55/.84/**.64** → .56/.86/**.65** | .93/.01/.02 → 1.00/.04/.07 | 1.00/.29/.45† → 1.00/.42/.59† |
| KB₄ REAL-FM-4 | .49/1.00/.64 → same | .46/.02/.03 → .60/.02/.04 | .79/.81/**.78** → .80/.84/**.80** | .87/.01/.02 → *pending* ∈ [1.00/.01/.02, 1.00/1.00/1.00] | 1.00/.10/.18† → *pending* ∈ [1.00/.10/.18, 1.00/1.00/1.00]† |
| KB₅ busybox | .60/1.00/.73 → ∈ [.60/1.00/.73, .60/1.00/.73] | .92/.01/.02 → ∈ [1.00/.45/.62, 1.00/1.00/1.00] | .80/.87/**.83** → ∈ [.80/.87/.83, .82/1.00/.90] | 1.00/.01/.01 → ∈ [1.00/.45/.62, 1.00/1.00/1.00] | 1.00/.02/.04† → ∈ [1.00/.45/.62, 1.00/1.00/1.00]† |

Per KB/condition:

- **(a) QuAcq-active, other KBs:** affected everywhere. ΔR: KB₂ +.003, KB₃ +.123; KB₄ pending;
  KB₅ R ≥ .448 (from .019).
- **(b) QuAcq-ex:** affected everywhere; F1 .01–.02 → .05–.44 on KB₁–KB₃; KB₅ ≥ .62.
- **(c) A / C / C∪S:** affected, size scales with how many root clauses the KB lacks. A barely
  moves (its R ≈ 1 already). C moves the most (near-empty KB). C∪S ΔR: +.061 / +.003 / +.020 / +.032.

KB₅ bounds (`step2b_busybox_bounds.py`, `step2b_output.txt`): N = 994 Cτ clauses (989 distinct),
|R+| = 445 clauses contain `+root` (root unit + 444 `x → root`) — all entailed by root alone →
new TP ≥ max(old TP, 445), ≤ N; FP fixed (recovered from old P). Direction is certain:
**R, P, F1 are non-decreasing for every cell under bg = root** (TP can only grow, FP is
bg-independent). A on KB₅ is unchanged to 2 dp. Exact re-run commands: `busybox_rerun.md`.
KB₄ QuAcq bounds: `step2b_fm4_quacq_output.txt` (|R+| = 3 of 428, so the lower bound is weak —
REAL-FM-7 shows root also unlocks chains via `root → x` bias clauses, so R+ is not an upper
bound on the gain).

## 4. Precision false positives (argument "every FP rejects a valid target configuration")

- `unentailed_kb` = { c ∈ KB : Cτ ⊭ c } is computed as `_check_entails(ct_clauses, kb_clauses)`
  (`semantic_equivalence.py:100`) with Cτ = `ground_truth.clauses`, which **already contains the
  root unit** (verified all 5 KBs). BG is not involved in that direction.
- Counts with Cτ vs Cτ ∖ root: **identical on every re-run row** (e.g. KB₁ A 589 vs 589, KB₄ A
  8381 vs 8381; column `FP: Cτ vs Cτ\root` in `step2_compare_output.txt`). Adding root to bg does
  not touch FP either.
- So the argument is **sound as computed**: c is FP ⇔ ∃ model of Cτ violating c, and models of Cτ
  (root included) are exactly the valid configurations. It would *not* be sound against Cτ ∖ root
  (the all-false assignment is a model there but not a configuration) — the shipped code avoids that.
- Caveat for the rebuttal wording: the reported **semantic precision is not the FP rate**.
  `kb_comparator.py:312-314` sets TP = #Cτ clauses entailed by the KB (the recall numerator) and
  FP = #KB clauses not entailed by Cτ; `metrics.py:48-57` then takes TP/(TP+FP). It mixes
  directions and units, and it moves with bg through TP (e.g. KB₁ QuAcq-ex .13 → 1.00 with FP = 0
  throughout; P = 0 whenever TP = 0 regardless of FP). A direction-pure KB-side precision,
  (|KB clauses| − FP)/|KB clauses|, is bg-independent: KB₁ A .707, C∪S .779; KB₄ A .589,
  C∪S .783 (`pure P` column) — it differs from the printed P (e.g. KB₁ A .49 vs .71).

## 5. Would Table 5 of the submitted paper change?

**Yes.** With bg = root on the semantic tier:

- 15 of 18 exactly-recomputed cells change at 2 dp (unchanged: KB₂ A, KB₂ ConMin, KB₄ A).
  KB₄ QuAcq-ex / QuAcq: pending re-run. KB₅: all cells except A move upward by an unknown amount
  inside the bounds above.
- Bold winners (`formatting.py:48-57`, daggered cells compete): **KB₁ moves ConMin → QuAcq
  (1.00)**; KB₂ (A), KB₃ (ConMin), KB₄ (ConMin, pending QuAcq) unchanged; **KB₅ undecidable from
  bounds** (ConMin ∈ [.83, .90] vs QuAcq† / QuAcq-ex / C ∈ [.62, 1.00]).
- Text claims that break: "matches or exceeds the active baseline on semantic recovery on all
  five" and "0.85 against 0.84 on KB₁" (l.436, l.438) — becomes .88 vs 1.00; "QuAcq-ex … semantic
  F1 between 0.01 and 0.02" (l.436) — becomes .05–.44 on KB₁–KB₃; "0.83 against 0.04†" on KB₅
  (l.436) — QuAcq† is now ≥ .62.
- Unaffected: exact_equiv (`exact-equiv.md`), accuracy and confusion tables (they use the
  delivered theory incl. root), description and clause tiers.

## Artifacts (scratch/rebuttal_aaai27/)

`step1_fm7_quacq_active.py` · `step2a_root_structure.py` · `step2_recompute_sem_with_root.py`
(`--fold` mode verified) · `step2_compare_old_vs_root.py` · `step2b_busybox_bounds.py` ·
`busybox_rerun.md` · `out/*_rows.csv`, `out/*_quacq_active_kb.json`, `out/logs/` · `*_output.txt`.
Nothing committed; nothing under `data/results_conmin/`, Overleaf or the bundle touched.

## Unresolved questions

1. KB₄ QuAcq-ex / QuAcq exact values: the re-run was still learning at 5 h 06 m (committed learn
   4 h 18 m, slowed by the concurrent model-counting job). If it stops on the 20,000 s timeout
   instead of `max_queries`, its theory ≠ committed and the reproduction gate will flag it; the
   bounds then stand.
2. Fix choice for the revision (not done): pass root as a semantic-only premise (keep clause tier
   at `[]`), and decide whether to also replace the mixed-direction semantic precision with the
   KB-side ratio. Both change every semantic number, so all tables need regenerating.
3. `ground_truth.clauses` contains duplicates (busybox 994 vs 989 distinct), which slightly
   weights recall; exact_equiv uses the set. Keep or deduplicate in the fix?
4. KB₅ exact numbers need the deferred re-runs in `busybox_rerun.md`; QuAcq-active
   reproducibility via `max_queries=1901` is unverified.
