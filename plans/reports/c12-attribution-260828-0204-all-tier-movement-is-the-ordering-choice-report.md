# Attribution: every moved tier metric is C12, not the defect fixes

Date 2026-08-28. Branch `feat/sosym-r1`. Two full ConGen sweeps into scratch, 72 folds
each, 4 knowledge bases (busybox NOT covered), scored through `run_compare` one block per
CV file. `data/` verified clean throughout. C12 was reverted for the second sweep and
restored from a saved copy immediately after; `reduce.py:78` is back to NE-first.

The split is C12 versus (a)+(b), not (b) versus the rest, because (a) and (b) are defect
fixes with no discretion in them — (a) repairs a redundancy test that could never fire,
(b) repairs a Definition 6 violation in the delivered theory — while C12 is the one
deliberate choice (Viet-Man's sacrifice priority). A discretionary change that moves
published numbers is a different disclosure from a bug fix that does.

## The number

| code state | tier metrics moved vs committed | max abs Δ | mean abs Δ |
|---|---|---|---|
| (a) + (b), **no C12** | **0 / 216** | 0.0000 | 0.00000 |
| (a) + C12 + (b) | **155 / 216** | 0.0909 | 0.00853 |
| **C12's own share** | **155 / 216** | **0.0909** | **0.00853** |

**All of it.** The two defect fixes move no published tier number at all.

Mechanism, verified rather than inferred: without C12 the bias `kb_constraints` are
identical to the committed run on **72 / 72 folds**. (a) and (b) touch only the NE side of
the KB, and the three tiers are scored from `kb_constraints` with NE excluded by the bias
guard at `kb_comparator.py:293`. C12 reorders what Reduce tests against what, so it is the
only one of the three that can change which bias constraints survive.

## But C12 is not decoration — it is what keeps the C6 premise true

`n_ne` per fold, over the same 72 folds:

| code state | distribution | max | total ¬e⁻ retained |
|---|---|---|---|
| committed (combined) | {0: 5, 1: 67} | 1 | 17 objects (each a conjunction) |
| (a) + (b), **no C12** | {0: 18, 1: 17, 2: 16, 3: 8, 4: 7, 5: 5, 6: 1} | **6** | **132** |
| (a) + C12 + (b) | {0: 30, 1: 42} | **1** | 42 |

Without C12, the per-e⁻ split makes `n_ne` climb to 6 and |KB| = n_kb + n_ne rises by
+2/+20/+12/+31 across the four KBs. With C12 it stays in {0, 1}.

So the earlier statement "C6's premise survives (b) intact" was right but incompletely
attributed: it survives *because of C12*. Reduce tests NE against what is LEFT of the KB,
so assembling NE last leaves each ¬e⁻ facing a KB already stripped of the constraints that
would entail it. C12 tests them against the whole of B′, where they discharge each other.

## Exact equivalence belongs to (b), not to C12

| code state | exactly equivalent |
|---|---|
| committed (bias + BG; its ¬e⁻ clause is auxiliary-only, so semantically empty) | 0 / 72 |
| (a) + (b), no C12 | **1 / 72** — `REAL-FM-7_rs_3n` fold 2 |
| (a) + C12 + (b) | **1 / 72** — same fold |

Both states reach it, by different routes, on the same fold:

| state | n_kb | n_ne | ne_clauses | equiv with NE | equiv without NE |
|---|---|---|---|---|---|
| no C12 | 9 (= committed) | 3 | `[[-14, 13], [2], [1]]` | True | **False** (2 target clauses unentailed) |
| with C12 | 11 | 1 | `[[1]]` | True | True |

Without C12 the equivalence is carried by the real ¬e⁻ clauses — which is exactly what (b)
restores and what the combined encoding threw away. With C12 those two facts have moved
from the NE side into the bias side instead. Either way the credit is (b)'s: with the old
auxiliary-only clause the fold is not equivalent in either ordering.

A 1/72 is only meaningful because the scorer is known able to return 1
(`tests/test_semantic_scorer_positive_control.py`, 6/6). Not to be quoted until the final
code state is fixed.

## An incidental worth keeping

On REAL-FM-7 the surviving ¬e⁻ is frequently `[[1]]` — the root literal, already present in
BG. Root non-emptiness re-derived as a memorized negative: the root-dependence story
surfacing in the *delivered theory* rather than in the reduction context.

## QuAcq needs no re-scoring — checked, not assumed

`quacq_runner.py` contains no reference to `Reduce`, `GenerateNE`, or `set_neg_tv`;
`QuAcqTaskPreparation` never builds `set_neg_tv` and never calls `GenerateNE`. So QuAcq's
delivered theories cannot move. `run_compare` iterates per file, computes `summary` per
file and writes back per file, with no cross-file state, so scoring ConGen cannot touch
QuAcq's figures. What DOES change is the comparison: ConGen moves beside a fixed QuAcq, so
Table 13's gap changes with one column untouched. That belongs in the disclosure.

## The decision this hands back

C12 was originally justified as a precondition for (a) — with NE bundled, the combined
constraint had to be tested against the whole of B′ or it could never discharge. With (b)
that justification is gone: (a)+(b) repairs Definition 6 and reaches the exact equivalence
without C12, moving zero tier metrics. C12's remaining justifications are that it keeps
`n_ne` in {0, 1}, preserving the reporting premise C6 was decided on, and that it matches
ConMin's F → S → C assembly.

Against that, it moves 155 of 216 tier metrics by up to 0.0909. That trade is Viet-Man's,
not a measurement question, and the sentence has to be written either way rather than
discovered by a reviewer.

## Unresolved

1. C12 in or out. If in, the disclosure names a deliberate ordering choice and its effect
   size. If out, `n_ne` reporting changes shape and C6 reopens.
2. busybox: 12 folds, 12.73 h, night window. Largest root reach of any KB.
3. Goldens (5) re-frozen only after the code state is fixed.
