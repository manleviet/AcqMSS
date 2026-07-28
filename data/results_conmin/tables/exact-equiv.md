# exact-equiv (reference — attainment counts per KB × condition)

exact-equivalence is logical equivalence of the delivered theory (including BG) via `SemanticEquivalenceChecker`; it does NOT require the named-constraint P/R/F1 (name-set only, BG excluded) to be 1.
Counts are reproducible from the committed `_long.csv` (same principle as the band-aid counters). A *configuration* = (example_set, k, negatives); it attains only when ALL its folds do.
> **QuAcq-active is learned once per KB and scored on every fold** — its 18 identical rows are ONE observation, so the denominator is collapsed to 1, NOT 18.

| KB | condition | rows attaining / scored | configs (all-folds) / total |
|---|---|---|---|
| $KB_{1}$ | A | 1 / 18 | 0 / 6 |
| $KB_{1}$ | C | 0 / 36 | 0 / 12 |
| $KB_{1}$ | ConMin | 8 / 144 | 0 / 48 |
| $KB_{1}$ | QuAcq(exonly) | 0 / 18 | 0 / 6 |
| $KB_{1}$ | QuAcq-active | 1 / 1 obs (learned once/KB) | n/a |
| $KB_{2}$ | A | 0 / 18 | 0 / 6 |
| $KB_{2}$ | C | 0 / 36 | 0 / 12 |
| $KB_{2}$ | ConMin | 0 / 144 | 0 / 48 |
| $KB_{2}$ | QuAcq(exonly) | 0 / 18 | 0 / 6 |
| $KB_{2}$ | QuAcq-active | 0 / 1 obs (learned once/KB) | n/a |
| $KB_{3}$ | A | 0 / 18 | 0 / 6 |
| $KB_{3}$ | C | 0 / 36 | 0 / 12 |
| $KB_{3}$ | ConMin | 0 / 144 | 0 / 48 |
| $KB_{3}$ | QuAcq(exonly) | 0 / 18 | 0 / 6 |
| $KB_{3}$ | QuAcq-active | 0 / 1 obs (learned once/KB) | n/a |
| $KB_{4}$ | A | 0 / 18 | 0 / 6 |
| $KB_{4}$ | C | 0 / 36 | 0 / 12 |
| $KB_{4}$ | ConMin | 0 / 144 | 0 / 48 |
| $KB_{4}$ | QuAcq(exonly) | 0 / 18 | 0 / 6 |
| $KB_{4}$ | QuAcq-active | 0 / 1 obs (learned once/KB) | n/a |
| $KB_{5}$ | A | 0 / 9 | 0 / 3 |
| $KB_{5}$ | C | 0 / 18 | 0 / 6 |
| $KB_{5}$ | ConMin | 0 / 72 | 0 / 24 |
| $KB_{5}$ | QuAcq(exonly) | 0 / 9 | 0 / 3 |
| $KB_{5}$ | QuAcq-active | 0 / 1 obs (learned once/KB) | n/a |

**Note — ConMin on REAL-FM-7 (the 8/144 row):** all eight attaining rows are ONE fold (RS-3n, fold 2, replicated over k in {1,2,3,5} x {raw, reduced}) — 0/48 configurations across all folds, a per-fold artifact rather than scattered success. This one-fold structure is the entire reason 8/144 is kept.

Text sentence (v1): among the passive strategies, exact structural equivalence is attained only on REAL-FM-7 (ConMin 8/144 rows — all one fold (RS-3n, fold 2, replicated over k in {1,2,3,5} x {raw, reduced}), 0/48 configurations across all folds; A 1/18); elsewhere 0.
