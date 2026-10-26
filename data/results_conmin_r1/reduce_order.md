# Reduce order ablation (eSpW Q3 follow-up): Reduce last (O1) vs Reduce first (O2)

2026-10-26 · revision / CC report only — not quoted in the rebuttal · KB₁ REAL-FM-7, KB₂ fqa, KB₃
arcade-game, KB₄ REAL-FM-4; all persisted folds incl. 2-COV; k ∈ {1, 2, 3, 5}; raw negatives ·
provenance: `PROVENANCE.md` § Reduce order ablation · per fold: `reduce_order/<kb>/<es>_fold<f>.json`,
per fold × k × order: `reduce_order.csv`.

- **O1** (shipped): KB = Reduce(C ∪ S ∪ F), C = AcqMinCover(A), S = {c ∈ A ∖ C : supp⁺ ≥ k}.
- **O2**: A′ = Reduce(A) (persisted, order S_full ∖ C → C → rest), C′ = AcqMinCover(A′) with A′ in A's
  pool order, S′ = {c ∈ A′ ∖ C′ : supp⁺ ≥ k}, KB′ = C′ ∪ S′ ∪ F′; finish_kb's own Reduce runs again
  and is asserted to remove nothing.
- No re-learning: task re-prepared (no Stage 1); ConMin's own `_compute_cover` (τ = 15) and
  `finish_kb` (assemble F → S → C, Reduce with BG = task.set_b = ∅, root outside) on one checker.
- Target construct = bias constraint whose description is in Cτ's descriptions (description tier).
  Scoring through `reduce_a_ablation._score` (all tiers, root in the premise, P_std and P_code,
  exact_equiv, accuracy, sol P/R by exact counting); UNSAT theories counted, not scored.

<!-- BEGIN generated -->

**Gate:** O1 recomputed from the persisted A reproduces the persisted cover and the persisted C∪S names and fallbacks on 72 folds × 4 k, **0 mismatches**. Reduce applied again to C′ ∪ S′ ∪ F′ removed a bias constraint in **0** of 288 O2 runs.

## Table-5-style summary, k = 1 (excl. 2-COV; mean (median))

| KB | order | folds | \|KB\| | \|C\| | \|S\| | Reduce removals | desc P | desc F1 | sem P_std | sem F1 | sol P | sol R | exact_equiv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KB₁ | O1 | 15 | 14.9 (15.0) | 0.9 (1.0) | 77.0 (72.0) | 63.0 (60.0) | 0.64 (0.67) | 0.68 (0.69) | 0.78 (0.77) | 0.86 (0.87) | 0.78 (1.00) | 0.37 (0.30) | 0.07 (0.00) |
| KB₁ | O2 | 15 | 14.5 (14.0) | 0.9 (1.0) | 13.6 (13.0) | 83.3 (75.0) | 0.66 (0.67) | 0.69 (0.69) | 0.78 (0.77) | 0.85 (0.87) | 0.74 (1.00) | 0.38 (0.30) | 0.07 (0.00) |
| KB₂ | O1 | 15 | 108.5 (126.0) | 1.2 (1.0) | 176.9 (200.0) | 69.6 (71.0) | 0.70 (0.68) | 0.70 (0.75) | 0.89 (0.91) | 0.78 (0.87) | 0.24 (0.00075) | 0.0093 (0.0034) | 0.00 (0.00) |
| KB₂ | O2 | 15 | 108.5 (126.0) | 1.2 (1.0) | 107.3 (125.0) | 125.5 (97.0) | 0.70 (0.68) | 0.70 (0.75) | 0.89 (0.91) | 0.78 (0.87) | 0.24 (0.00075) | 0.0093 (0.0034) | 0.00 (0.00) |
| KB₃ | O1 | 15 | 162.0 (186.0) | 1.3 (1.0) | 342.0 (346.0) | 181.3 (130.0) | 0.33 (0.25) | 0.41 (0.36) | 0.52 (0.43) | 0.62 (0.59) | 0.51 (0.43) | 8.9e-05 (5.1e-06) | 0.00 (0.00) |
| KB₃ | O2 | 15 | 157.9 (178.0) | 1.3 (1.0) | 156.6 (177.0) | 474.8 (364.0) | 0.36 (0.26) | 0.42 (0.38) | 0.53 (0.43) | 0.62 (0.59) | 0.49 (0.43) | 0.00019 (5.1e-06) | 0.00 (0.00) |
| KB₄ | O1 | 15 | 223.4 (252.0) | 1.3 (1.0) | 511.3 (524.0) | 289.2 (265.0) | 0.69 (0.68) | 0.67 (0.70) | 0.78 (0.79) | 0.80 (0.80) | 0.16 (0.0026) | 1.1e-06 (7.7e-09) | 0.00 (0.00) |
| KB₄ | O2 | 15 | 222.3 (252.0) | 1.3 (1.0) | 221.1 (251.0) | 564.1 (421.0) | 0.69 (0.68) | 0.67 (0.70) | 0.79 (0.79) | 0.78 (0.79) | 0.16 (0.0026) | 1.3e-06 (7.7e-09) | 0.00 (0.00) |

### k = 2

| KB | order | folds | \|KB\| | \|C\| | \|S\| | Reduce removals | desc P | desc F1 | sem P_std | sem F1 | sol P | sol R | exact_equiv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KB₁ | O1 | 15 | 11.6 (12.0) | 0.9 (1.0) | 51.8 (58.0) | 41.1 (48.0) | 0.66 (0.69) | 0.62 (0.71) | 0.82 (0.83) | 0.82 (0.87) | 0.54 (0.62) | 0.50 (0.40) | 0.07 (0.00) |
| KB₁ | O2 | 15 | 11.0 (12.0) | 0.9 (1.0) | 10.1 (11.0) | 83.3 (75.0) | 0.73 (0.69) | 0.64 (0.71) | 0.83 (0.83) | 0.82 (0.87) | 0.53 (0.62) | 0.51 (0.40) | 0.07 (0.00) |
| KB₂ | O1 | 15 | 87.3 (105.0) | 1.2 (1.0) | 136.6 (173.0) | 50.5 (61.0) | 0.77 (0.70) | 0.62 (0.71) | 0.92 (0.90) | 0.65 (0.73) | 0.01 (1.2e-07) | 0.14 (0.02) | 0.00 (0.00) |
| KB₂ | O2 | 15 | 87.3 (105.0) | 1.2 (1.0) | 86.1 (104.0) | 125.5 (97.0) | 0.77 (0.70) | 0.62 (0.71) | 0.92 (0.90) | 0.65 (0.73) | 0.01 (1.2e-07) | 0.14 (0.02) | 0.00 (0.00) |
| KB₃ | O1 | 15 | 143.5 (160.0) | 1.3 (1.0) | 224.5 (276.0) | 82.3 (85.0) | 0.42 (0.27) | 0.42 (0.37) | 0.60 (0.45) | 0.63 (0.60) | 0.39 (0.08) | 0.03 (8.9e-05) | 0.00 (0.00) |
| KB₃ | O2 | 15 | 139.6 (151.0) | 1.3 (1.0) | 138.3 (150.0) | 474.8 (364.0) | 0.46 (0.28) | 0.43 (0.39) | 0.62 (0.44) | 0.63 (0.59) | 0.38 (0.08) | 0.09 (9.8e-05) | 0.00 (0.00) |
| KB₄ | O1 | 15 | 190.1 (225.0) | 1.3 (1.0) | 398.0 (425.0) | 209.2 (215.0) | 0.72 (0.73) | 0.64 (0.69) | 0.81 (0.81) | 0.76 (0.78) | 0.08 (6.6e-06) | 0.00016 (1.9e-08) | 0.00 (0.00) |
| KB₄ | O2 | 15 | 187.3 (221.0) | 1.3 (1.0) | 186.1 (220.0) | 564.1 (421.0) | 0.73 (0.73) | 0.64 (0.69) | 0.82 (0.81) | 0.74 (0.77) | 0.08 (6.3e-06) | 0.00073 (1.9e-08) | 0.00 (0.00) |

### k = 3

| KB | order | folds | \|KB\| | \|C\| | \|S\| | Reduce removals | desc P | desc F1 | sem P_std | sem F1 | sol P | sol R | exact_equiv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KB₁ | O1 | 15 | 9.2 (10.0) | 0.9 (1.0) | 37.9 (48.0) | 29.6 (39.0) | 0.73 (0.73) | 0.58 (0.61) | 0.90 (0.88) | 0.79 (0.82) | 0.43 (0.19) | 0.73 (0.75) | 0.07 (0.00) |
| KB₁ | O2 | 15 | 8.7 (9.0) | 0.9 (1.0) | 7.7 (8.0) | 83.3 (75.0) | 0.86 (0.86) | 0.58 (0.64) | 0.91 (0.91) | 0.78 (0.79) | 0.43 (0.15) | 0.74 (0.75) | 0.07 (0.00) |
| KB₂ | O1 | 15 | 75.5 (83.0) | 1.2 (1.0) | 116.9 (129.0) | 42.7 (47.0) | 0.80 (0.78) | 0.56 (0.66) | 0.93 (0.93) | 0.57 (0.62) | 0.00036 (3.8e-11) | 0.31 (0.03) | 0.00 (0.00) |
| KB₂ | O2 | 15 | 75.5 (83.0) | 1.2 (1.0) | 74.3 (82.0) | 125.5 (97.0) | 0.80 (0.78) | 0.56 (0.66) | 0.93 (0.93) | 0.57 (0.62) | 0.00036 (3.8e-11) | 0.31 (0.03) | 0.00 (0.00) |
| KB₃ | O1 | 15 | 122.1 (98.0) | 1.3 (1.0) | 183.5 (181.0) | 62.6 (70.0) | 0.48 (0.40) | 0.43 (0.45) | 0.66 (0.62) | 0.64 (0.66) | 0.29 (0.05) | 0.15 (0.0013) | 0.00 (0.00) |
| KB₃ | O2 | 15 | 119.1 (94.0) | 1.3 (1.0) | 117.8 (93.0) | 474.8 (364.0) | 0.52 (0.41) | 0.44 (0.45) | 0.67 (0.61) | 0.63 (0.61) | 0.29 (0.05) | 0.27 (0.0013) | 0.00 (0.00) |
| KB₄ | O1 | 15 | 168.5 (204.0) | 1.3 (1.0) | 339.7 (396.0) | 172.5 (184.0) | 0.76 (0.76) | 0.62 (0.68) | 0.84 (0.87) | 0.74 (0.74) | 0.04 (2.1e-08) | 0.06 (3.2e-07) | 0.00 (0.00) |
| KB₄ | O2 | 15 | 165.7 (202.0) | 1.3 (1.0) | 164.4 (201.0) | 564.1 (421.0) | 0.76 (0.77) | 0.61 (0.69) | 0.85 (0.87) | 0.72 (0.74) | 0.04 (1.1e-08) | 0.08 (3.2e-07) | 0.00 (0.00) |

### k = 5

| KB | order | folds | \|KB\| | \|C\| | \|S\| | Reduce removals | desc P | desc F1 | sem P_std | sem F1 | sol P | sol R | exact_equiv |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KB₁ | O1 | 15 | 4.6 (3.0) | 0.9 (1.0) | 19.1 (9.0) | 15.4 (6.0) | 0.95 (1.00) | 0.42 (0.27) | 1.00 (1.00) | 0.71 (0.67) | 0.20 (0.04) | 1.00 (1.00) | 0.07 (0.00) |
| KB₁ | O2 | 15 | 4.3 (2.0) | 0.9 (1.0) | 3.4 (2.0) | 83.3 (75.0) | 1.00 (1.00) | 0.43 (0.27) | 1.00 (1.00) | 0.70 (0.67) | 0.19 (0.04) | 1.00 (1.00) | 0.07 (0.00) |
| KB₂ | O1 | 15 | 56.5 (55.0) | 1.2 (1.0) | 89.7 (94.0) | 34.3 (37.0) | 0.88 (0.89) | 0.53 (0.61) | 0.96 (0.97) | 0.51 (0.49) | 6.9e-07 (1.4e-14) | 0.46 (0.20) | 0.00 (0.00) |
| KB₂ | O2 | 15 | 56.5 (55.0) | 1.2 (1.0) | 55.3 (54.0) | 125.5 (97.0) | 0.88 (0.89) | 0.53 (0.61) | 0.96 (0.97) | 0.51 (0.49) | 6.9e-07 (1.4e-14) | 0.46 (0.20) | 0.00 (0.00) |
| KB₃ | O1 | 15 | 90.4 (45.0) | 1.3 (1.0) | 134.3 (76.0) | 45.1 (36.0) | 0.59 (0.71) | 0.47 (0.47) | 0.77 (0.92) | 0.67 (0.68) | 0.20 (0.04) | 0.31 (0.33) | 0.00 (0.00) |
| KB₃ | O2 | 15 | 88.3 (44.0) | 1.3 (1.0) | 87.1 (43.0) | 474.8 (364.0) | 0.63 (0.73) | 0.47 (0.47) | 0.78 (0.93) | 0.65 (0.64) | 0.20 (0.04) | 0.51 (0.50) | 0.00 (0.00) |
| KB₄ | O1 | 15 | 145.3 (162.0) | 1.3 (1.0) | 291.0 (329.0) | 146.9 (158.0) | 0.79 (0.80) | 0.59 (0.67) | 0.86 (0.87) | 0.71 (0.70) | 0.0013 (3.2e-13) | 0.07 (8.8e-06) | 0.00 (0.00) |
| KB₄ | O2 | 15 | 142.5 (160.0) | 1.3 (1.0) | 141.2 (159.0) | 564.1 (421.0) | 0.80 (0.80) | 0.59 (0.67) | 0.87 (0.87) | 0.69 (0.69) | 0.0013 (3.2e-13) | 0.10 (8.8e-06) | 0.00 (0.00) |

## Target constructs lost (per fold; description tier)

"Lost to Reduce": target in the pre-Reduce theory (O1: C ∪ S; O2: A), absent after Reduce (O1: KB; O2: A′). "Lost to Stage 2": target in the Stage-2 pool (O1: A; O2: A′), absent from C ∪ S. "entailed / lost": lost-to-Reduce target constraints entailed by the kept theory.

### Table-5 samplings

| KB | k | lost to Reduce O1 | lost to Reduce O2 | lost to Stage 2 O1 | lost to Stage 2 O2 | entailed / lost (all) | C ≠ C′ folds | KB ≠ KB′ folds |
|---|---|---|---|---|---|---|---|---|
| KB₁ | 1 | 2.5 (2.0) | 3.0 (3.0) | 1.0 (0.0) | 0.5 (0.0) | 82 / 82 | 0/15 | 3/15 |
| KB₁ | 2 | 1.3 (1.0) | 3.0 (3.0) | 3.7 (2.0) | 1.9 (1.0) | 64 / 64 | 0/15 | 5/15 |
| KB₁ | 3 | 0.5 (1.0) | 3.0 (3.0) | 5.4 (5.0) | 3.0 (3.0) | 53 / 53 | 0/15 | 7/15 |
| KB₁ | 5 | 0.2 (0.0) | 3.0 (3.0) | 8.5 (11.0) | 5.7 (6.0) | 48 / 48 | 0/15 | 3/15 |
| KB₂ | 1 | 3.1 (3.0) | 6.7 (4.0) | 16.2 (6.0) | 12.5 (6.0) | 147 / 147 | 0/15 | 0/15 |
| KB₂ | 2 | 1.7 (2.0) | 6.7 (4.0) | 30.0 (19.0) | 25.0 (18.0) | 127 / 127 | 0/15 | 0/15 |
| KB₂ | 3 | 1.5 (1.0) | 6.7 (4.0) | 38.2 (31.0) | 32.9 (29.0) | 123 / 123 | 0/15 | 0/15 |
| KB₂ | 5 | 0.9 (1.0) | 6.7 (4.0) | 47.1 (45.0) | 41.2 (42.0) | 114 / 114 | 0/15 | 0/15 |
| KB₃ | 1 | 15.1 (16.0) | 21.1 (20.0) | 7.7 (2.0) | 1.7 (1.0) | 544 / 544 | 0/15 | 9/15 |
| KB₃ | 2 | 10.6 (12.0) | 21.1 (20.0) | 15.5 (10.0) | 5.0 (5.0) | 476 / 476 | 0/15 | 10/15 |
| KB₃ | 3 | 9.2 (11.0) | 21.1 (20.0) | 19.5 (17.0) | 7.7 (9.0) | 455 / 455 | 0/15 | 12/15 |
| KB₃ | 5 | 6.9 (5.0) | 21.1 (20.0) | 25.0 (30.0) | 11.1 (13.0) | 420 / 420 | 0/15 | 12/15 |
| KB₄ | 1 | 31.1 (31.0) | 50.5 (41.0) | 35.1 (16.0) | 16.3 (8.0) | 1223 / 1223 | 0/15 | 6/15 |
| KB₄ | 2 | 23.2 (25.0) | 50.5 (41.0) | 59.3 (34.0) | 33.1 (24.0) | 1105 / 1105 | 0/15 | 8/15 |
| KB₄ | 3 | 19.7 (23.0) | 50.5 (41.0) | 72.7 (49.0) | 43.1 (30.0) | 1052 / 1052 | 0/15 | 9/15 |
| KB₄ | 5 | 16.1 (16.0) | 50.5 (41.0) | 87.6 (76.0) | 54.5 (51.0) | 998 / 998 | 0/15 | 12/15 |

### 2-COV

| KB | k | lost to Reduce O1 | lost to Reduce O2 | lost to Stage 2 O1 | lost to Stage 2 O2 | entailed / lost (all) | C ≠ C′ folds | KB ≠ KB′ folds |
|---|---|---|---|---|---|---|---|---|
| KB₁ | 1 | 0.0 (0.0) | 13.0 (13.0) | 11.0 (11.0) | 0.0 (0.0) | 39 / 39 | 3/3 | 3/3 |
| KB₁ | 2 | 0.0 (0.0) | 13.0 (13.0) | 11.0 (11.0) | 0.0 (0.0) | 39 / 39 | 3/3 | 3/3 |
| KB₁ | 3 | 0.0 (0.0) | 13.0 (13.0) | 11.0 (11.0) | 0.0 (0.0) | 39 / 39 | 3/3 | 3/3 |
| KB₁ | 5 | 0.0 (0.0) | 13.0 (13.0) | 11.0 (11.0) | 0.0 (0.0) | 39 / 39 | 3/3 | 3/3 |
| KB₂ | 1 | 0.0 (0.0) | 60.0 (60.0) | 93.3 (93.0) | 34.0 (34.0) | 180 / 180 | 2/3 | 2/3 |
| KB₂ | 2 | 0.0 (0.0) | 60.0 (60.0) | 93.3 (93.0) | 34.0 (34.0) | 180 / 180 | 2/3 | 2/3 |
| KB₂ | 3 | 0.0 (0.0) | 60.0 (60.0) | 93.3 (93.0) | 34.0 (34.0) | 180 / 180 | 2/3 | 2/3 |
| KB₂ | 5 | 0.0 (0.0) | 60.0 (60.0) | 93.3 (93.0) | 34.0 (34.0) | 180 / 180 | 2/3 | 2/3 |
| KB₃ | 1 | 25.3 (38.0) | 42.0 (38.0) | 22.0 (0.0) | 5.3 (0.0) | 202 / 202 | 1/3 | 1/3 |
| KB₃ | 2 | 0.0 (0.0) | 42.0 (38.0) | 66.0 (66.0) | 24.0 (28.0) | 126 / 126 | 1/3 | 1/3 |
| KB₃ | 3 | 0.0 (0.0) | 42.0 (38.0) | 66.0 (66.0) | 24.0 (28.0) | 126 / 126 | 1/3 | 1/3 |
| KB₃ | 5 | 0.0 (0.0) | 42.0 (38.0) | 66.0 (66.0) | 24.0 (28.0) | 126 / 126 | 1/3 | 1/3 |
| KB₄ | 1 | 71.3 (107.0) | 108.7 (107.0) | 72.0 (0.0) | 34.7 (0.0) | 540 / 540 | 1/3 | 1/3 |
| KB₄ | 2 | 0.0 (0.0) | 108.7 (107.0) | 216.3 (216.0) | 107.7 (109.0) | 326 / 326 | 1/3 | 1/3 |
| KB₄ | 3 | 0.0 (0.0) | 108.7 (107.0) | 216.3 (216.0) | 107.7 (109.0) | 326 / 326 | 1/3 | 1/3 |
| KB₄ | 5 | 0.0 (0.0) | 108.7 (107.0) | 216.3 (216.0) | 107.7 (109.0) | 326 / 326 | 1/3 | 1/3 |

## Net target constructs in the final theory (excl. 2-COV)

Number of target constructs in KB′ minus in KB, per fold; "fewer / more" counts folds where Reduce-first keeps fewer / more of them.

| KB | k = 1: Δ mean (median) · O2 fewer / more | k = 2: Δ mean (median) · O2 fewer / more | k = 3: Δ mean (median) · O2 fewer / more | k = 5: Δ mean (median) · O2 fewer / more |
|---|---|---|---|---|
| KB₁ | 0.00 (0.00) · 0 / 0 | 0.07 (0.00) · 0 / 1 | -0.07 (0.00) · 1 / 0 | 0.07 (0.00) · 0 / 1 |
| KB₂ | 0.00 (0.00) · 0 / 0 | 0.00 (0.00) · 0 / 0 | 0.00 (0.00) · 0 / 0 | 0.00 (0.00) · 0 / 0 |
| KB₃ | 0.00 (0.00) · 1 / 1 | -0.07 (0.00) · 1 / 0 | -0.13 (0.00) · 2 / 0 | -0.40 (0.00) · 5 / 0 |
| KB₄ | -0.60 (0.00) · 4 / 0 | -1.07 (0.00) · 6 / 0 | -1.20 (0.00) · 6 / 0 | -1.33 (0.00) · 6 / 0 |

## Examples (largest KB ≠ KB′ difference per KB)

- **KB₃ ff fold 2, k = 1** (n_train_pos 12): |KB| 97 → |KB′| 92; cover same; desc F1 0.46 → 0.46, sol R 1.56e-06 → 3.56e-06.
  KB ∖ KB′: ArcadeGame --mandatory--> ClassDiagram; BottomPaddle requires PlayPong; Bowling requires PlayPong; BowlingBall excludes Leftpong; BowlingPin excludes Leftpong; Brick requires PlayPong; BrickPile requires PlayPong; BricklesBoard excludes PlayPong; BricklesBoard requires Brickles; Floorbrickles requires PlayPong; PlayPong requires PongBoard; PlayPong requires PongGameMenu; Pong requires PlayPong; PongGameMenu requires PlayPong; Pucksupply requires PlayPong
  KB′ ∖ KB: BottomPaddle excludes BricklesBoard; Bowling excludes BricklesBoard; BowlingBall excludes Edge; BowlingPin excludes Edge; Brick excludes BricklesBoard; BrickPile excludes BricklesBoard; BricklesBoard excludes Floorbrickles; BricklesBoard excludes Pong; BricklesBoard excludes Pucksupply; Menu --or--> ['Pong', 'Brickles', 'Bowling']
- **KB₄ rs_m fold 2, k = 1** (n_train_pos 12): |KB| 102 → |KB′| 98; cover same; desc F1 0.45 → 0.44, sol R 3.16e-06 → 4.09e-06.
  KB ∖ KB′: Buypaths --mandatory--> Checkout; Categories requires Services; Eletronicgoods excludes Services; Permissions requires Services; Preferences requires Services; ProductInformation --optional--> Size; Registeredcheckout requires Registration; Registertobuy requires Registeredcheckout; Registration --mandatory--> Registrationenforcement; Services requires Registeredcheckout; Services requires Servicesfulfillment; Servicesfulfillment requires Services; Storefront --mandatory--> Buypaths
  KB′ ∖ KB: Buypaths --optional--> Checkout; Catalog --optional--> Categories; Categories excludes Eletronicgoods; Eletronicgoods excludes Permissions; Eletronicgoods excludes Preferences; Registration --optional--> Registrationenforcement; Registrationinformation --optional--> Preferences; Storefront --optional--> Buypaths; Wishlist --optional--> Permissions
- **KB₁ ff fold 1, k = 2** (n_train_pos 4): |KB| 8 → |KB′| 5; cover same; desc F1 0.19 → 0.33, sol R 0.375 → 0.375.
  KB ∖ KB′: gui_builder requires compiler; gui_builder requires mdi; mdi requires jplug; mvc requires gui_builder
  KB′ ∖ KB: jplug --optional--> gui_builder

<!-- END generated -->

## Why the theories differ (examples above)

- **KB₄ rs_m f2** shows the hypothesised mechanism. `Storefront --mandatory--> Buypaths` (a target
  construct) is (Storefront → Buypaths) ∧ (Buypaths → Storefront). In A′ its downward half is
  entailed by a five-link chain — Storefront `--mandatory-->` Registration, Registration `requires`
  Registeredcheckout, `Checkouttype --alternative--> [Registeredcheckout, Guestcheckout]`,
  Checkout `--mandatory-->` Checkouttype, Buypaths `--optional-->` Checkout — and its upward half by
  `Storefront --optional--> Buypaths`, so Reduce-first deletes the mandatory edge. Stage 2 then drops
  the alternative group (unsupported), the chain breaks, and only the weaker `--optional-->` edge
  survives in KB′. `Buypaths --mandatory--> Checkout` is lost the same way (QuickXPlain over A′,
  checked). KB′ is weaker, so sol R rises slightly (3.2e-6 → 4.1e-6) while description F1 falls
  (.45 → .44).
- **KB₃ ff f2**: two families of mutually entailing candidates (`X requires PlayPong` vs `X excludes
  BricklesBoard`, plus the `Menu` or-group). Reduce over A keeps the representatives that come first
  in A's order and Stage 2 cannot bring the others back, so KB′ carries a different family of the
  same size class; neither order is uniformly better on that fold.
- **KB₁ ff f1, k = 2**: the opposite direction — Reduce-first leaves `jplug --optional--> gui_builder`
  (a target construct) where O1 keeps four non-target `requires` (two of them spurious, Cτ ⊭ c); desc F1 .19 → .33.
- C′ = C on every Table-5 fold (the cover is unaffected); on 2-COV (A ≈ the whole bias) the cover
  differs on 7 of 12 folds.

## Verdict

The hypothesis holds only weakly, and only on the two larger knowledge bases. Reduce-first always
loses more target constructs to Reduce itself (A is larger: e.g. KB₄ 50.5 vs 31.1 per fold at k = 1),
but most of them O1 loses anyway to Stage 2 (35.1 vs 16.3), so the net effect on the final theory is
small: KB′ holds the same number of target constructs as KB on KB₁ and KB₂ at every k, and fewer on
KB₃ (−0.4 per fold at k = 5, 5 of 15 folds) and KB₄ (−0.6 at k = 1 to −1.3 at k = 5, 4–6 of 15
folds; never more). Every target removed by Reduce is entailed by the kept theory, and the cover
never changes on Table-5 folds, so the loss comes entirely from Stage 2 discarding the entailer that
Reduce chose to keep. Table-5-level scores barely move: description F1 equal or +.01, semantic F1 −.01 (KB₁)
and −.02 (KB₄), sol P −.04 (KB₁) and −.02 (KB₃), sol R equal or slightly higher. Reduce last, as shipped, is the safer order, but the
order is not what drives ConMin's construct precision.
