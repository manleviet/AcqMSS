# Reduce(A) ablation (eSpW W2/Q3)

2026-10-25 · persisted KBs, no re-learning · KB₁ REAL-FM-7, KB₂ fqa, KB₃ arcade-game, KB₄
REAL-FM-4; KB₅ busybox not measured (no persisted KBs; `busybox_rerun.md`) · provenance:
`PROVENANCE.md`. Per fold: `reduce_a/<kb>/<es>_fold<f>.json` (Reduce(A), removed constraints,
R and V); `reduce_a_ablation.csv` (per fold × condition, all tiers); summary
`reduce_a_ablation_summary.csv`.

**Method.** Reduce(A) = ConMin's own `Reduce.reduce(ids, [], task.set_b, task.negation_map)`
(BG = ∅, root outside, as in `finish_kb`) on A's ids, mapped from the persisted names after a
cheap task re-preparation. Order = S_full∖C → C → rest of A (ConMin's F→S→C order extended to
A); A's plain pool order gives the same |Reduce(A)| on all 72 folds and the identical set on 63 of
72 (different representatives of redundant pairs on 9) — sensitivity column.
R = constraints rejecting ≥ 1 training negative (clause-level SAT, BG = ∅); S_full = support⁺ ≥ 1;
V = A ∖ (R ∪ S_full). Scored on every tier through the same path as the other conditions;
**gate**: A and ConMin re-scored here equal the persisted shipped scores (72 folds, 0
mismatches). **Assert**: #models(Reduce(A)) = #models(A) and #models(Reduce(A) ∧ Cτ) =
#models(A ∧ Cτ) on every fold (exact counts) — Reduce preserves the solution set.
sem = corrected contract (root as background), P_std, F1 with P_std (empty KB → F1 0).
UNSAT rule: UNSAT folds are counted, not scored.

### Table 5 (excl. 2-COV) — mean (median) over folds

| KB | condition | \|KB\| | desc P | desc F1 | sem P_std | sem F1 | sol P | sol R | \|V kept\| |
|---|---|---|---|---|---|---|---|---|---|
| KB₁ | A  | 99.3 (91.0) | 0.15 (0.14) | 0.25 (0.25) | 0.71 (0.69) | 0.81 (0.82) | 1.00 (1.00) | 0.34 (0.25) | 15.8 (0.0) |
| KB₁ | Reduce(A)  | 15.9 (16.0) | 0.64 (0.67) | 0.70 (0.71) | 0.77 (0.77) | 0.87 (0.87) | 1.00 (1.00) | 0.34 (0.25) | 1.0 (0.0) |
| KB₁ | ConMin k=1  | 14.9 (15.0) | 0.64 (0.67) | 0.68 (0.69) | 0.78 (0.77) | 0.86 (0.87) | 0.78 (1.00) | 0.37 (0.30) | 0.0 (0.0) |
| KB₂ | A  | 252.9 (230.0) | 0.39 (0.41) | 0.54 (0.57) | 0.83 (0.86) | 0.90 (0.92) | 1.00 (1.00) | 0.0076 (0.00086) | 41.1 (0.0) |
| KB₂ | Reduce(A)  | 127.4 (131.0) | 0.69 (0.68) | 0.76 (0.77) | 0.88 (0.89) | 0.94 (0.94) | 1.00 (1.00) | 0.0076 (0.00086) | 9.2 (0.0) |
| KB₂ | ConMin k=1  | 108.5 (126.0) | 0.70 (0.68) | 0.70 (0.75) | 0.89 (0.91) | 0.78 (0.87) | 0.24 (0.00075) | 0.0093 (0.0034) | 0.0 (0.0) |
| KB₃ | A  | 641.9 (545.0) | 0.13 (0.12) | 0.23 (0.22) | 0.32 (0.31) | 0.47 (0.47) | 1.00 (1.00) | 3e-06 (7.4e-07) | 193.1 (30.0) |
| KB₃ | Reduce(A)  | 167.1 (181.0) | 0.32 (0.26) | 0.41 (0.38) | 0.46 (0.46) | 0.62 (0.63) | 1.00 (1.00) | 3e-06 (7.4e-07) | 5.3 (1.0) |
| KB₃ | ConMin k=1  | 162.0 (186.0) | 0.33 (0.25) | 0.41 (0.36) | 0.52 (0.43) | 0.62 (0.59) | 0.51 (0.43) | 8.9e-05 (5.1e-06) | 0.0 (0.0) |
| KB₄ | A  | 822.5 (687.0) | 0.30 (0.32) | 0.46 (0.48) | 0.59 (0.61) | 0.73 (0.76) | 1.00 (1.00) | 8.9e-07 (5.5e-16) | 192.7 (0.0) |
| KB₄ | Reduce(A)  | 258.5 (264.0) | 0.65 (0.65) | 0.70 (0.71) | 0.72 (0.70) | 0.83 (0.82) | 1.00 (1.00) | 8.9e-07 (5.5e-16) | 18.5 (0.0) |
| KB₄ | ConMin k=1  | 223.4 (252.0) | 0.69 (0.68) | 0.67 (0.70) | 0.78 (0.79) | 0.80 (0.80) | 0.16 (0.0026) | 1.1e-06 (7.7e-09) | 0.0 (0.0) |

### 2-COV — mean (median) over folds

| KB | condition | \|KB\| | desc P | desc F1 | sem P_std | sem F1 | sol P | sol R | \|V kept\| |
|---|---|---|---|---|---|---|---|---|---|
| KB₁ | A (3 UNSAT) | 294.0 (294.0) | — (—) | — (—) | — (—) | — (—) | — (—) | — (—) | 39.7 (36.0) |
| KB₁ | Reduce(A) (3 UNSAT) | 16.0 (16.0) | — (—) | — (—) | — (—) | — (—) | — (—) | — (—) | 2.3 (2.0) |
| KB₁ | ConMin k=1  | 2.0 (2.0) | 1.00 (1.00) | 0.27 (0.27) | 1.00 (1.00) | 0.69 (0.71) | 0.05 (0.05) | 1.00 (1.00) | 0.0 (0.0) |
| KB₂ | A  | 458.0 (458.0) | 0.21 (0.21) | 0.34 (0.34) | 0.60 (0.60) | 0.75 (0.75) | 1.00 (1.00) | 1e-25 (1e-25) | 16.3 (16.0) |
| KB₂ | Reduce(A)  | 104.0 (104.0) | 0.33 (0.33) | 0.33 (0.33) | 0.74 (0.74) | 0.85 (0.85) | 1.00 (1.00) | 1e-25 (1e-25) | 3.7 (3.0) |
| KB₂ | ConMin k=1  | 1.7 (2.0) | 0.33 (0.50) | 0.01 (0.02) | 0.46 (0.47) | 0.10 (0.10) | 1.9e-31 (7.8e-32) | 1.8e-06 (2.7e-06) | 0.0 (0.0) |
| KB₃ | A (1 UNSAT) | 1374.7 (1185.0) | 0.06 (0.06) | 0.11 (0.11) | 0.15 (0.15) | 0.26 (0.26) | 1.00 (1.00) | 6.1e-10 (6.1e-10) | 37.3 (0.0) |
| KB₃ | Reduce(A) (1 UNSAT) | 68.0 (71.0) | 0.41 (0.41) | 0.41 (0.41) | 0.71 (0.71) | 0.83 (0.83) | 1.00 (1.00) | 6.1e-10 (6.1e-10) | 0.3 (0.0) |
| KB₃ | ConMin k=1  | 47.7 (71.0) | 0.61 (0.41) | 0.28 (0.41) | 0.81 (0.71) | 0.58 (0.83) | 0.67 (1.00) | 0.33 (6.1e-10) | 0.0 (0.0) |
| KB₄ | A (1 UNSAT) | 1678.7 (1479.0) | 0.15 (0.15) | 0.26 (0.26) | 0.36 (0.36) | 0.53 (0.53) | 1.00 (1.00) | 3.9e-20 (3.9e-20) | 24.0 (0.0) |
| KB₄ | Reduce(A) (1 UNSAT) | 210.0 (213.0) | 0.52 (0.52) | 0.51 (0.51) | 0.81 (0.81) | 0.90 (0.90) | 1.00 (1.00) | 3.9e-20 (3.9e-20) | 2.7 (0.0) |
| KB₄ | ConMin k=1  | 142.7 (213.0) | 0.68 (0.52) | 0.35 (0.51) | 0.87 (0.81) | 0.62 (0.90) | 0.67 (1.00) | 0.33 (3.9e-20) | 0.0 (0.0) |

### Partition of A and what Stage 2 removes beyond Reduce (Table-5 folds, means)

| KB | \|A\| | \|R\| | \|S_full\| | \|V\| | \|Reduce(A)\| | \|V ∩ Reduce(A)\| | \|Reduce(A) ∖ ConMin\| = V + unsupported R∖C + S_full | \|ConMin ∖ Reduce(A)\| |
|---|---|---|---|---|---|---|---|---|
| KB₁ | 99.3 | 28.3 | 77.9 | 15.8 | 15.9 | 1.0 | 1.4 = 1.0 + 0.4 + 0.0 | 0.4 |
| KB₂ | 252.9 | 189.9 | 177.8 | 41.1 | 127.4 | 9.2 | 18.9 = 9.2 + 9.7 + 0.0 | 0.0 |
| KB₃ | 641.9 | 347.1 | 343.3 | 193.1 | 167.1 | 5.3 | 11.7 = 5.3 + 4.0 + 2.4 | 6.5 |
| KB₄ | 822.5 | 547.4 | 512.3 | 192.7 | 258.5 | 18.5 | 37.5 = 18.5 + 17.7 + 1.3 | 2.4 |

Share of the A → ConMin gain that Reduce(A) already achieves, (A − Reduce(A)) / (A − ConMin):

| KB | \|KB\| | desc P | sem P_std |
|---|---|---|---|
| KB₁ | 98.8% | 98.8% | 90.3% |
| KB₂ | 86.9% | 95.2% | 76.9% |
| KB₃ | 98.9% | 91.9% | 68.0% |
| KB₄ | 94.1% | 89.6% | 66.2% |

## Verdict

Most of ConMin's gain over A in size and construct precision is Reduce's, not Stage 2's.
Reduce(A) alone removes 87–99% of the constraints ConMin removes (KB₁ 99 → 16 vs ConMin 15;
KB₄ 823 → 258 vs 223) and achieves 90–99% of the description-precision gain. Stage 2 adds more
on semantic precision (P_std): Reduce accounts for 90% of the gain on KB₁ but only 66–77% on
KB₂–KB₄, so Stage 2 contributes +.007/+.015/+.065/+.066 P_std beyond Reduce(A). On F1 Stage 2
does not help: Reduce(A) matches or beats ConMin on description F1 (.70/.76/.41/.70 vs
.68/.70/.41/.67) and on semantic F1 (.87/.94/.62/.83 vs .86/.78/.62/.80), because Reduce(A)
keeps A's solution set — semantic recall 1.0, sol P = 1 — while ConMin trades soundness
(sol P .78/.24/.51/.16) for a solution-set recall gain that stays negligible on KB₂–KB₄.
Stage 2's residual effect is as expected but only half vacuous: what it removes beyond
Reduce(A) is every vacuous constraint Reduce keeps (|V ∩ Reduce(A)| = 1.0/9.2/5.3/18.5, all
dropped by ConMin) plus about as many unsupported rejectors outside the cover
(0.4/9.7/4.0/17.7), and almost nothing supported. On 2-COV (A ≈ the whole bias), Reduce(A)
shrinks A 4–20-fold (294 → 16, 458 → 104, 1375 → 68, 1679 → 210) while ConMin collapses to
the bare cover on KB₁/KB₂ (2.0, 1.7 constraints); KB₁ 2-COV is UNSAT in all 3 folds for A
and hence for Reduce(A), which preserves the model set, so neither is scored there.

<!-- BEGIN binned view (generated) -->

## Positive scarcity: Reduce(A) vs ConMin (k = 1)

Means over folds; sol P / sol R also as median (ratios span orders of magnitude). sem = root as background, P_std, F1 with P_std. UNSAT folds counted, not scored.

### 2-COV folds (0–1 training positives)

| KB | n_train_pos | condition | \|KB\| | sem P_std | sem F1 | sol P mean (median) | sol R mean (median) | \|V kept\| |
|---|---|---|---|---|---|---|---|---|
| KB₁ | 0 | Reduce(A) (3 UNSAT) | 16.0 | — | — | — (—) | — (—) | 2.3 |
| KB₁ | 0 | ConMin k=1  | 2.0 | 1.00 | 0.69 | 0.05 (0.05) | 1.00 (1.00) | 0.0 |
| KB₂ | 0 | Reduce(A)  | 104.0 | 0.74 | 0.85 | 1.00 (1.00) | 1e-25 (1e-25) | 3.7 |
| KB₂ | 0 | ConMin k=1  | 1.7 | 0.46 | 0.10 | 1.9e-31 (7.8e-32) | 1.8e-06 (2.7e-06) | 0.0 |
| KB₃ | 0–1 | Reduce(A) (1 UNSAT) | 68.0 | 0.71 | 0.83 | 1.00 (1.00) | 6.1e-10 (6.1e-10) | 0.3 |
| KB₃ | 0–1 | ConMin k=1  | 47.7 | 0.81 | 0.58 | 0.67 (1.00) | 0.33 (6.1e-10) | 0.0 |
| KB₄ | 0–1 | Reduce(A) (1 UNSAT) | 210.0 | 0.81 | 0.90 | 1.00 (1.00) | 3.9e-20 (3.9e-20) | 2.7 |
| KB₄ | 0–1 | ConMin k=1  | 142.7 | 0.87 | 0.62 | 0.67 (1.00) | 0.33 (3.9e-20) | 0.0 |

### Table-5 folds by thirds of n_train_pos (within KB, 5 folds each)

Stage 2 share = (Reduce(A) − ConMin) / (A − ConMin) on the means. A share whose denominator |A − ConMin| < 0.01 is not reported (near-zero denominator).

| KB | n_train_pos | condition | \|KB\| | sem P_std | sem F1 | sol P mean (median) | sol R mean (median) | \|V kept\| | Stage 2 share \|KB\| / P_std |
|---|---|---|---|---|---|---|---|---|---|
| KB₁ low | 4–5 | Reduce(A)  | 16.4 | 0.69 | 0.82 | 1.00 (1.00) | 0.07 (0.07) | 2.4 | |
| KB₁ low | 4–5 | ConMin k=1  | 13.8 | 0.70 | 0.79 | 0.46 (0.50) | 0.14 (0.10) | 0.0 | 2% / 7% |
| KB₁ mid | 6–17 | Reduce(A)  | 16.6 | 0.74 | 0.85 | 1.00 (1.00) | 0.24 (0.25) | 0.6 | |
| KB₁ mid | 6–17 | ConMin k=1  | 16.2 | 0.75 | 0.85 | 0.88 (1.00) | 0.28 (0.25) | 0.0 | 1% / 9% |
| KB₁ high | 17–26 | Reduce(A)  | 14.8 | 0.88 | 0.94 | 1.00 (1.00) | 0.70 (0.65) | 0.0 | |
| KB₁ high | 17–26 | ConMin k=1  | 14.8 | 0.88 | 0.94 | 1.00 (1.00) | 0.70 (0.65) | 0.0 | 0% / 0% |
| KB₂ low | 10–39 | Reduce(A)  | 117.2 | 0.86 | 0.92 | 1.00 (1.00) | 7.7e-07 (4.7e-07) | 26.8 | |
| KB₂ low | 10–39 | ConMin k=1  | 71.2 | 0.90 | 0.56 | 7.3e-07 (6.1e-18) | 0.00089 (0.00014) | 0.0 | 19% / 24% |
| KB₂ mid | 40–215 | Reduce(A)  | 129.8 | 0.88 | 0.94 | 1.00 (1.00) | 0.0028 (0.0032) | 0.8 | |
| KB₂ mid | 40–215 | ConMin k=1  | 119.8 | 0.89 | 0.85 | 0.08 (0.00075) | 0.007 (0.0055) | 0.0 | 9% / 21% |
| KB₂ high | 215–323 | Reduce(A)  | 135.2 | 0.90 | 0.95 | 1.00 (1.00) | 0.02 (0.03) | 0.0 | |
| KB₂ high | 215–323 | ConMin k=1  | 134.4 | 0.90 | 0.94 | 0.65 (1.00) | 0.02 (0.03) | 0.0 | 1% / —† |
| KB₃ low | 8–11 | Reduce(A)  | 85.8 | 0.49 | 0.66 | 1.00 (1.00) | 5.7e-08 (6.3e-08) | 14.8 | |
| KB₃ low | 8–11 | ConMin k=1  | 69.8 | 0.71 | 0.70 | 0.03 (0.0046) | 0.00026 (2.5e-05) | 0.0 | 2% / 41% |
| KB₃ mid | 12–78 | Reduce(A)  | 176.8 | 0.47 | 0.64 | 1.00 (1.00) | 1e-06 (7.4e-07) | 1.0 | |
| KB₃ mid | 12–78 | ConMin k=1  | 177.4 | 0.45 | 0.59 | 0.49 (0.43) | 2e-06 (1.6e-06) | 0.0 | -0% / -15% |
| KB₃ high | 78–118 | Reduce(A)  | 238.8 | 0.40 | 0.57 | 1.00 (1.00) | 7.8e-06 (6.9e-06) | 0.0 | |
| KB₃ high | 78–118 | ConMin k=1  | 238.8 | 0.40 | 0.57 | 1.00 (1.00) | 7.8e-06 (6.9e-06) | 0.0 | 0% / 0% |
| KB₄ low | 11–64 | Reduce(A)  | 236.4 | 0.65 | 0.79 | 1.00 (1.00) | 6e-23 (4.3e-26) | 54.6 | |
| KB₄ low | 11–64 | ConMin k=1  | 154.2 | 0.83 | 0.70 | 2.2e-08 (1.6e-18) | 6.9e-07 (1e-07) | 0.0 | 8% / 45% |
| KB₄ mid | 64–349 | Reduce(A)  | 269.0 | 0.72 | 0.84 | 1.00 (1.00) | 2.6e-08 (5.5e-16) | 0.8 | |
| KB₄ mid | 64–349 | ConMin k=1  | 250.6 | 0.73 | 0.81 | 0.02 (0.0026) | 7.7e-08 (4.5e-15) | 0.0 | 4% / 7% |
| KB₄ high | 349–524 | Reduce(A)  | 270.0 | 0.79 | 0.88 | 1.00 (1.00) | 2.7e-06 (1.2e-08) | 0.0 | |
| KB₄ high | 349–524 | ConMin k=1  | 265.4 | 0.80 | 0.87 | 0.47 (0.51) | 2.7e-06 (3.3e-08) | 0.0 | 2% / 16% |

† not reported — KB₂ high: near-zero denominator (|A − ConMin| = 0.002).

<!-- END binned view (generated) -->
