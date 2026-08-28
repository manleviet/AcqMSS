# busybox, measured on its own terms

Date 2026-08-28. Branch `feat/sosym-r1`, final code state. 9 folds — `2cov`, `rs_m`, `ff`,
three folds each — re-run with the negative-example fixes into scratch and scored through
`run_compare`. `data/` has no tracked-file modifications.

Reported apart from the other four knowledge bases and not folded into their tables.
busybox has the largest root reach of any knowledge base here, which is where the
root-dependence story could behave differently, so nothing above it was taken by
inference. `rs_1n` (10.8 h of busybox's 12.73 h) is not included; `rs_2n`/`rs_3n` were
never completed in the sweep and have no baseline to compare against.

## n_ne

| | 2cov | rs_m | ff |
|---|---|---|---|
| \|E⁻\| per fold | 14 | 1, 1, 2 | 6 |
| `n_ne` | 1, 1, 1 | 1, 1, 1 | 1, 1, 1 |
| discarded | 13, 13, 13 | 0, 0, 1 | 5, 5, 5 |

**Maximum `n_ne` is 1 on all 9 folds**, and `n_ne + discarded = |E⁻|` closes on every one.
Same as the other four. The memorized fact is retained everywhere — never discharged —
which is what a knowledge base whose conflicts turn on the root axiom looks like, and the
opposite of fqa, where all 17 were discharged.

## Tier deltas

| | busybox (9 folds) | the other four (72 folds) |
|---|---|---|
| metrics moved | 18 / 27 | 155 / 216 |
| **max abs Δ** | **0.0027** | **0.0909** |

All movement is on `ff`; `2cov` and `rs_m` are unchanged to twelve decimal places. Largest
single move: clause recall 0.5150 → 0.5177.

The direction of the difference is the opposite of what was feared. busybox moves by a
third of a percent where REAL-FM-7 moves by nine, and the reason is arithmetic rather than
semantic: the reduction order changes the surviving set by a couple of constraints, and a
couple of constraints out of ~600 is a much smaller relative change than out of 11. The
largest knowledge base is the least disturbed.

## Exact equivalence and accuracy

| | |
|---|---|
| exact equivalence | **0 / 9** — `2cov` 0/3, `rs_m` 0/3, `ff` 0/3 |
| test-fold FP moves when the ¬e⁻ clauses are real | **0 / 9** (0 control failures) |
| fold accuracy differs from committed | **0 / 9** |
| NE recall interval (semantic R with vs without NE) | **+0.0000 on all 9** |

The zero-equivalence column is a result, not a gap: busybox is the knowledge base where a
delivered theory comes nowhere near recovering the target, and no F1 says that on its own.

The NE recall interval being flat here is worth stating beside the other four, where 14 of
42 folds moved and one moved by +0.7615. On busybox the bias constraints already entail
everything the memorized fact would add, so the tiers understate nothing.

## Unresolved

1. `rs_1n` is unmeasured — 3 folds, ~10.8 h, its own stretch. It is the busybox cell with
   the largest example pool and the only one whose behaviour is not represented here.
2. `rs_2n` / `rs_3n` remain out of scope: never completed in the sweep, so there is no
   committed baseline to compare a re-run against.
