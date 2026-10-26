# Step 4 — dead features of Reduce(A) ∪ root

2026-10-25 · persisted Reduce(A) (`../reduce_a/`), no re-learning · KB₁ REAL-FM-7, KB₂ fqa, KB₃
arcade-game, KB₄ REAL-FM-4, all samplings; busybox not measured · glucose4 throughout ·
provenance: `../PROVENANCE.md` § Step 4. Per fold: `<kb>/<es>_fold<f>.json`; per constraint:
`dead_features_constraints.csv`. 72 folds, 67 consistent (5 UNSAT 2-COV folds counted, not scored).

## Definitions implemented

- T = Reduce(A) ∪ root. **Dead** in Θ: Θ ∧ f UNSAT. Dead(Cτ ∪ root) is empty on all four KBs, so
  no feature is excluded from the test-case sets. **False optional**: T ⊨ f, Cτ ∪ root ⊭ f.
- **Aggregation**: one incremental solver, constraints selector-guarded; every model found marks all
  features it selects as attainable, only unmarked features cost a call ("SAT calls" vs "#features").
- **CS(f)**: one minimal conflict ⊆ Reduce(A) by QuickXPlain against root ∪ {f}, Reduce(A) order.
- **Spurious** c: Cτ ⊭ c, i.e. some clause of c is not entailed by Cτ (Cτ contains the root unit) —
  the semantic tier's precision-side check, on one incremental solver.
- **Certain** = {c ∈ Reduce(A) : ∃ f ∈ Dead(T) ∖ Dead(Cτ), root ∪ {c} ∪ {f} UNSAT}; only c whose
  variables include f is checked.
- **Classes** (first match): R∩C (cover ∩ R); C∖R (cover element rejecting no negative alone);
  R∖C (rejects a training negative, not in the cover); S (support⁺ ≥ 1, not in R); V otherwise —
  V_unseen if none of its trigger features (variables occurring negatively in one of its clauses)
  is selected in any training example (positive or negative), else V_obs.
- **UB** = Reduce(A) ∖ {spurious c in some computed CS(f)}. **EST** = (Reduce(A) ∖ Certain) ∖ D.
- **D**: FastDiag is not applicable — its precondition requires the background alone (root) to
  satisfy every test case, and root accepts every training e⁻. D is therefore a minimum-cardinality
  diagnosis by breadth-first HS-tree over QuickXPlain conflicts of the still-dead features
  (positives), children in removal-preference order (support⁺ ascending, then non-cover first);
  a node that accepts a required e⁻ (rejected by Reduce(A) ∖ Certain) is pruned — removing more
  constraints only accepts more examples. Node limit 2,000.
- **UB_A** (added) = Reduce(A ∖ X), X = every spurious constraint of A in a conflict of a dead
  feature (QuickXPlain repeated until f is alive). Repair *before* Reduce — see note 1.
- Scoring: `reduce_a_ablation._score` (all tiers, root in the premise, P_std; sol P/R by exact pysdd
  counting — scoring only). Bins = Table-5 thirds of n_train_pos (as `reduce_a_ablation.md`),
  2-COV separate. Gap closed per fold with Reduce(A) sol R = r₀, repaired r₁: linear
  (r₁ − r₀)/(1 − r₀), log log(r₁/r₀)/log(1/r₀).

## Notes

1. **UB loses soundness.** UB's sol P < 1 on 36 of 67 consistent folds (EST: 33). Reduce has already
   deleted target constraints that a spurious killer entails (anything "f → …" once ¬f holds), so
   removing the killer from Reduce(A) revives f without them. UB_A, repairing A before Reduce, keeps
   sol P = 1 on 60 of 67 folds.
2. **The 7 UB_A exceptions** are all KB₄ (ff f0, rs_1n f0–f2, rs_m f0–f2; sol P .94–.999): target
   constraint 14 (`Previouslyvisitedpages → Locallyvisitedpages ∨ Externalreferringpages`) is a
   3-literal clause with no bias counterpart; A entails it only via a stronger spurious *requires*
   (c1124 or c1265), which is also a killer. Removing it loses that target clause — a bias-
   expressiveness limit, not a repair defect.
3. **EST node limit** hit on 2 folds (KB₄ rs_m f1, f2: 45 and 58 dead features), which keep their
   dead features (KB₄ low: EST "#dead remaining" 20.6 mean).
4. Conflicts are almost never singletons outside KB₁: 10 of 12 on KB₁, **0 of 663** on KB₂–KB₄
   (median size 7 / 3 / 4) — so Certain is empty on KB₂–KB₄. No target constraint is ever in Certain.

<!-- BEGIN generated -->

**Gate:** A and ConMin k=1 re-scored through the Step-4 path equal the persisted shipped scores on 72 folds, **0 mismatches**.

## Part 1 — detection

| KB | bin (n_train_pos) | folds | #dead(Cτ) | #dead(T) | SAT calls | #features | #false optionals |
|---|---|---|---|---|---|---|---|
| KB₁ | low (4–5) | 5 (0 UNSAT) | 0 | 2.0 (2.0) | 6.6 (7.0) | 14 | 0.2 (0.0) |
| KB₁ | mid (6–17) | 5 (0 UNSAT) | 0 | 0.4 (0.0) | 7.2 (7.0) | 14 | 0.0 (0.0) |
| KB₁ | high (17–26) | 5 (0 UNSAT) | 0 | 0.0 (0.0) | 8.0 (8.0) | 14 | 0.0 (0.0) |
| KB₁ | 2-COV | 3 (3 UNSAT) | 0 | — | — | 14 | — |
| KB₂ | low (10–39) | 5 (0 UNSAT) | 0 | 5.6 (7.0) | 103.4 (103.0) | 179 | 0.0 (0.0) |
| KB₂ | mid (40–215) | 5 (0 UNSAT) | 0 | 1.2 (0.0) | 106.6 (107.0) | 179 | 0.0 (0.0) |
| KB₂ | high (215–323) | 5 (0 UNSAT) | 0 | 0.2 (0.0) | 106.6 (107.0) | 179 | 0.0 (0.0) |
| KB₂ | 2-COV | 3 (0 UNSAT) | 0 | 127.0 (127.0) | 152.0 (152.0) | 179 | 0.0 (0.0) |
| KB₃ | low (8–11) | 5 (0 UNSAT) | 0 | 13.6 (17.0) | 25.6 (27.0) | 65 | 0.6 (0.0) |
| KB₃ | mid (12–78) | 5 (0 UNSAT) | 0 | 1.8 (1.0) | 24.0 (24.0) | 65 | 0.0 (0.0) |
| KB₃ | high (78–118) | 5 (0 UNSAT) | 0 | 0.0 (0.0) | 27.8 (27.0) | 65 | 0.0 (0.0) |
| KB₃ | 2-COV | 3 (1 UNSAT) | 0 | 0.0 (0.0) | 2.0 (2.0) | 65 | 44.0 (44.0) |
| KB₄ | low (11–64) | 5 (0 UNSAT) | 0 | 31.6 (45.0) | 165.0 (168.0) | 291 | 4.8 (8.0) |
| KB₄ | mid (64–349) | 5 (0 UNSAT) | 0 | 2.0 (2.0) | 159.4 (158.0) | 291 | 0.0 (0.0) |
| KB₄ | high (349–524) | 5 (0 UNSAT) | 0 | 0.4 (0.0) | 162.0 (162.0) | 291 | 0.0 (0.0) |
| KB₄ | 2-COV | 3 (1 UNSAT) | 0 | 0.0 (0.0) | 86.0 (86.0) | 291 | 123.0 (123.0) |

## Part 2 — anatomy

Spurious constraints by class: total / in a conflict / in Certain / in no conflict (= residual), fold means.

| KB | bin | #dead(T) | singleton CS | \|Certain\| | #spurious | R∩C | C∖R | R∖C | S | V_obs | V_unseen |
|---|---|---|---|---|---|---|---|---|---|---|---|
| KB₁ | low (4–5) | 2.0 (2.0) | 8/10 | 1.6 (1.0) | 7.8 (8.0) | 0 | 0 | 3.2/0.4/0.4/2.8 | 3.2/0.0/0.0/3.2 | 1.4/1.4/1.2/0.0 | 0 |
| KB₁ | mid (6–17) | 0.4 (0.0) | 2/2 | 0.4 (0.0) | 6.4 (6.0) | 0 | 0 | 2.0/0.0/0.0/2.0 | 4.0/0.0/0.0/4.0 | 0.4/0.4/0.4/0.0 | 0 |
| KB₁ | high (17–26) | 0.0 (0.0) | — | 0.0 (0.0) | 2.8 (3.0) | 0 | 0 | 1.8/0.0/0.0/1.8 | 1.0/0.0/0.0/1.0 | 0 | 0 |
| KB₁ | 2-COV | — | — | — | — | 0 | 0 | 0 | 0 | 0 | 0 |
| KB₂ | low (10–39) | 5.6 (7.0) | 0/28 | 0.0 (0.0) | 32.0 (31.0) | 0 | 0 | 16.8/2.8/0.0/14.0 | 6.0/0.8/0.0/5.2 | 6.0/4.2/0.0/1.8 | 3.2/2.8/0.0/0.4 |
| KB₂ | mid (40–215) | 1.2 (0.0) | 0/6 | 0.0 (0.0) | 34.0 (33.0) | 0 | 0 | 32.2/1.0/0.0/31.2 | 1.4/0.0/0.0/1.4 | 0.2/0.2/0.0/0.0 | 0.2/0.2/0.0/0.0 |
| KB₂ | high (215–323) | 0.2 (0.0) | 0/1 | 0.0 (0.0) | 35.4 (35.0) | 0.2/0.0/0.0/0.2 | 0 | 35.2/0.4/0.0/34.8 | 0 | 0 | 0 |
| KB₂ | 2-COV | 127.0 (127.0) | 0/381 | 0.0 (0.0) | 27.0 (27.0) | 1.0/1.0/0.0/0.0 | 0 | 25.7/18.7/0.0/7.0 | 0 | 0.3/0.3/0.0/0.0 | 0 |
| KB₃ | low (8–11) | 13.6 (17.0) | 0/68 | 0.0 (0.0) | 43.6 (38.0) | 0 | 0 | 16.0/4.2/0.0/11.8 | 14.6/0.0/0.0/14.6 | 6.4/5.6/0.0/0.8 | 6.6/6.6/0.0/0.0 |
| KB₃ | mid (12–78) | 1.8 (1.0) | 0/9 | 0.0 (0.0) | 123.2 (127.0) | 0.2/0.0/0.0/0.2 | 0 | 78.6/2.8/0.0/75.8 | 43.6/0.0/0.0/43.6 | 0.6/0.6/0.0/0.0 | 0.2/0.2/0.0/0.0 |
| KB₃ | high (78–118) | 0.0 (0.0) | — | 0.0 (0.0) | 175.8 (168.0) | 0.2/0.0/0.0/0.2 | 0 | 172.2/0.0/0.0/172.2 | 3.4/0.0/0.0/3.4 | 0 | 0 |
| KB₃ | 2-COV | 0.0 (0.0) | — | 0.0 (0.0) | 38.0 (38.0) | 1.0/0.0/0.0/1.0 | 0 | 34.0/0.0/0.0/34.0 | 3.0/0.0/0.0/3.0 | 0 | 0 |
| KB₄ | low (11–64) | 31.6 (45.0) | 0/158 | 0.0 (0.0) | 85.6 (86.0) | 0.8/0.0/0.0/0.8 | 0 | 46.4/6.0/0.0/40.4 | 15.2/1.0/0.0/14.2 | 13.8/6.8/0.0/7.0 | 9.4/6.4/0.0/3.0 |
| KB₄ | mid (64–349) | 2.0 (2.0) | 0/10 | 0.0 (0.0) | 91.2 (90.0) | 1.2/0.0/0.0/1.2 | 0 | 87.0/3.0/0.0/84.0 | 3.0/0.0/0.0/3.0 | 0 | 0 |
| KB₄ | high (349–524) | 0.4 (0.0) | 0/2 | 0.0 (0.0) | 78.4 (76.0) | 1.6/0.0/0.0/1.6 | 0 | 76.8/0.8/0.0/76.0 | 0 | 0 | 0 |
| KB₄ | 2-COV | 0.0 (0.0) | — | 0.0 (0.0) | 93.0 (93.0) | 0 | 0 | 92.5/0.0/0.0/92.5 | 0.5/0.0/0.0/0.5 | 0 | 0 |

Target (non-spurious) constraints in Certain: **0**.

## Part 3 — what repair recovers

| KB | bin | theory | \|KB\| | desc P | desc F1 | sem P_std | sem F1 | sol P | sol R | #dead remaining |
|---|---|---|---|---|---|---|---|---|---|---|
| KB₁ | low (4–5) | Reduce(A) | 16.4 (17.0) | 0.49 (0.47) | 0.54 (0.53) | 0.69 (0.68) | 0.82 (0.81) | 1.00 (1.00) | 0.07 (0.07) | 2.0 (2.0) |
| KB₁ | low (4–5) | ConMin k=1 | 13.8 (15.0) | 0.50 (0.50) | 0.51 (0.50) | 0.70 (0.68) | 0.79 (0.79) | 0.46 (0.50) | 0.14 (0.10) | 0.0 (0.0) |
| KB₁ | low (4–5) | UB | 14.6 (15.0) | 0.55 (0.53) | 0.58 (0.57) | 0.74 (0.74) | 0.82 (0.82) | 0.66 (0.64) | 0.15 (0.11) | 0.0 (0.0) |
| KB₁ | low (4–5) | EST | 14.8 (15.0) | 0.54 (0.53) | 0.58 (0.57) | 0.74 (0.74) | 0.83 (0.83) | 0.76 (0.70) | 0.13 (0.11) | 0.0 (0.0) |
| KB₁ | low (4–5) | UB_A | 15.2 (15.0) | 0.53 (0.53) | 0.57 (0.57) | 0.72 (0.72) | 0.84 (0.84) | 1.00 (1.00) | 0.13 (0.11) | 0.0 (0.0) |
| KB₁ | low (4–5) | EST diagnosis | |D| 0.0 (0.0) | spurious in D 0.0 (0.0) | checks 1 (2) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₁ | mid (6–17) | Reduce(A) | 16.6 (16.0) | 0.60 (0.67) | 0.68 (0.71) | 0.74 (0.77) | 0.85 (0.87) | 1.00 (1.00) | 0.24 (0.25) | 0.4 (0.0) |
| KB₁ | mid (6–17) | ConMin k=1 | 16.2 (16.0) | 0.61 (0.67) | 0.67 (0.69) | 0.75 (0.77) | 0.85 (0.87) | 0.88 (1.00) | 0.28 (0.25) | 0.0 (0.0) |
| KB₁ | mid (6–17) | UB | 16.2 (16.0) | 0.62 (0.67) | 0.68 (0.74) | 0.76 (0.77) | 0.86 (0.87) | 0.96 (1.00) | 0.28 (0.25) | 0.0 (0.0) |
| KB₁ | mid (6–17) | EST | 16.2 (16.0) | 0.62 (0.67) | 0.68 (0.74) | 0.76 (0.77) | 0.86 (0.87) | 0.96 (1.00) | 0.28 (0.25) | 0.0 (0.0) |
| KB₁ | mid (6–17) | UB_A | 16.6 (17.0) | 0.61 (0.67) | 0.68 (0.74) | 0.75 (0.77) | 0.86 (0.87) | 1.00 (1.00) | 0.28 (0.25) | 0.0 (0.0) |
| KB₁ | mid (6–17) | EST diagnosis | |D| 0.0 (0.0) | spurious in D 0.0 (0.0) | checks 1 (1) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₁ | high (17–26) | Reduce(A) | 14.8 (15.0) | 0.82 (0.80) | 0.87 (0.86) | 0.88 (0.87) | 0.94 (0.93) | 1.00 (1.00) | 0.70 (0.65) | 0.0 (0.0) |
| KB₁ | high (17–26) | ConMin k=1 | 14.8 (15.0) | 0.82 (0.80) | 0.87 (0.86) | 0.88 (0.87) | 0.94 (0.93) | 1.00 (1.00) | 0.70 (0.65) | 0.0 (0.0) |
| KB₁ | high (17–26) | UB | 14.8 (15.0) | 0.82 (0.80) | 0.87 (0.86) | 0.88 (0.87) | 0.94 (0.93) | 1.00 (1.00) | 0.70 (0.65) | 0.0 (0.0) |
| KB₁ | high (17–26) | EST | 14.8 (15.0) | 0.82 (0.80) | 0.87 (0.86) | 0.88 (0.87) | 0.94 (0.93) | 1.00 (1.00) | 0.70 (0.65) | 0.0 (0.0) |
| KB₁ | high (17–26) | UB_A | 14.8 (15.0) | 0.82 (0.80) | 0.87 (0.86) | 0.88 (0.87) | 0.94 (0.93) | 1.00 (1.00) | 0.70 (0.65) | 0.0 (0.0) |
| KB₁ | high (17–26) | EST diagnosis | |D| 0.0 (0.0) | spurious in D 0.0 (0.0) | checks 2 (2) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₁ | 2-COV | Reduce(A) | — | — | — | — | — | — | — | — |
| KB₁ | 2-COV | ConMin k=1 | — | — | — | — | — | — | — | — |
| KB₁ | 2-COV | UB | — | — | — | — | — | — | — | — |
| KB₁ | 2-COV | EST | — | — | — | — | — | — | — | — |
| KB₁ | 2-COV | UB_A | — | — | — | — | — | — | — | — |
| KB₂ | low (10–39) | Reduce(A) | 117.2 (115.0) | 0.69 (0.70) | 0.74 (0.73) | 0.86 (0.86) | 0.92 (0.93) | 1.00 (1.00) | 7.7e-07 (4.7e-07) | 5.6 (7.0) |
| KB₂ | low (10–39) | ConMin k=1 | 71.2 (57.0) | 0.74 (0.77) | 0.58 (0.55) | 0.90 (0.91) | 0.56 (0.45) | 7.3e-07 (6.1e-18) | 0.00089 (0.00014) | 0.0 (0.0) |
| KB₂ | low (10–39) | UB | 106.6 (101.0) | 0.77 (0.82) | 0.78 (0.80) | 0.88 (0.90) | 0.93 (0.93) | 0.59 (0.43) | 0.00018 (4.4e-06) | 0.0 (0.0) |
| KB₂ | low (10–39) | EST | 112.6 (109.0) | 0.72 (0.75) | 0.76 (0.76) | 0.87 (0.87) | 0.92 (0.92) | 0.89 (1.00) | 1.5e-06 (1.1e-06) | 0.0 (0.0) |
| KB₂ | low (10–39) | UB_A | 114.4 (110.0) | 0.74 (0.77) | 0.78 (0.80) | 0.89 (0.90) | 0.94 (0.95) | 1.00 (1.00) | 7.6e-06 (4.4e-06) | 0.0 (0.0) |
| KB₂ | low (10–39) | EST diagnosis | |D| 4.6 (6.0) | spurious in D 4.6 (6.0) | checks 5629 (1970) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₂ | mid (40–215) | Reduce(A) | 129.8 (131.0) | 0.68 (0.68) | 0.76 (0.76) | 0.88 (0.89) | 0.94 (0.94) | 1.00 (1.00) | 0.0028 (0.0032) | 1.2 (0.0) |
| KB₂ | mid (40–215) | ConMin k=1 | 119.8 (126.0) | 0.68 (0.68) | 0.73 (0.75) | 0.89 (0.88) | 0.85 (0.87) | 0.08 (0.00075) | 0.007 (0.0055) | 0.0 (0.0) |
| KB₂ | mid (40–215) | UB | 128.4 (131.0) | 0.69 (0.69) | 0.77 (0.76) | 0.88 (0.89) | 0.94 (0.94) | 0.94 (1.00) | 0.0032 (0.0032) | 0.0 (0.0) |
| KB₂ | mid (40–215) | EST | 129.4 (131.0) | 0.69 (0.69) | 0.77 (0.76) | 0.88 (0.89) | 0.94 (0.94) | 1.00 (1.00) | 0.0032 (0.0032) | 0.0 (0.0) |
| KB₂ | mid (40–215) | UB_A | 129.8 (131.0) | 0.69 (0.69) | 0.77 (0.76) | 0.89 (0.89) | 0.94 (0.94) | 1.00 (1.00) | 0.0032 (0.0032) | 0.0 (0.0) |
| KB₂ | mid (40–215) | EST diagnosis | |D| 0.4 (0.0) | spurious in D 0.4 (0.0) | checks 27 (23) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₂ | high (215–323) | Reduce(A) | 135.2 (135.0) | 0.68 (0.68) | 0.78 (0.78) | 0.90 (0.91) | 0.95 (0.95) | 1.00 (1.00) | 0.02 (0.03) | 0.2 (0.0) |
| KB₂ | high (215–323) | ConMin k=1 | 134.4 (135.0) | 0.68 (0.68) | 0.77 (0.78) | 0.90 (0.91) | 0.94 (0.95) | 0.65 (1.00) | 0.02 (0.03) | 0.0 (0.0) |
| KB₂ | high (215–323) | UB | 134.8 (135.0) | 0.68 (0.68) | 0.78 (0.78) | 0.90 (0.91) | 0.95 (0.95) | 1.00 (1.00) | 0.02 (0.03) | 0.0 (0.0) |
| KB₂ | high (215–323) | EST | 135.0 (135.0) | 0.68 (0.68) | 0.78 (0.78) | 0.90 (0.91) | 0.95 (0.95) | 1.00 (1.00) | 0.02 (0.03) | 0.0 (0.0) |
| KB₂ | high (215–323) | UB_A | 135.0 (135.0) | 0.68 (0.68) | 0.78 (0.78) | 0.90 (0.91) | 0.95 (0.95) | 1.00 (1.00) | 0.02 (0.03) | 0.0 (0.0) |
| KB₂ | high (215–323) | EST diagnosis | |D| 0.2 (0.0) | spurious in D 0.2 (0.0) | checks 38 (35) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₂ | 2-COV | Reduce(A) | 104.0 (104.0) | 0.33 (0.33) | 0.33 (0.33) | 0.74 (0.74) | 0.85 (0.85) | 1.00 (1.00) | 1e-25 (1e-25) | 127.0 (127.0) |
| KB₂ | 2-COV | ConMin k=1 | 1.7 (2.0) | 0.33 (0.50) | 0.01 (0.02) | 0.46 (0.47) | 0.10 (0.10) | 1.9e-31 (7.8e-32) | 1.8e-06 (2.7e-06) | 0.0 (0.0) |
| KB₂ | 2-COV | UB | 84.0 (84.0) | 0.40 (0.40) | 0.37 (0.37) | 0.94 (0.94) | 0.74 (0.74) | 9.4e-12 (9.4e-12) | 0.02 (0.02) | 0.0 (0.0) |
| KB₂ | 2-COV | EST | 102.0 (102.0) | 0.33 (0.33) | 0.33 (0.33) | 0.79 (0.78) | 0.72 (0.72) | 2.5e-13 (3.7e-13) | 1.6e-16 (2.4e-16) | 0.0 (0.0) |
| KB₂ | 2-COV | UB_A | 107.0 (107.0) | 0.64 (0.64) | 0.65 (0.65) | 0.86 (0.86) | 0.93 (0.93) | 1.00 (1.00) | 8.8e-09 (8.8e-09) | 0.0 (0.0) |
| KB₂ | 2-COV | EST diagnosis | |D| 2.0 (2.0) | spurious in D 2.0 (2.0) | checks 639 (602) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₃ | low (8–11) | Reduce(A) | 85.8 (78.0) | 0.46 (0.48) | 0.50 (0.50) | 0.49 (0.46) | 0.66 (0.63) | 1.00 (1.00) | 5.7e-08 (6.3e-08) | 13.6 (17.0) |
| KB₃ | low (8–11) | ConMin k=1 | 69.8 (62.0) | 0.51 (0.53) | 0.50 (0.51) | 0.71 (0.74) | 0.70 (0.70) | 0.03 (0.0046) | 0.00026 (2.5e-05) | 0.0 (0.0) |
| KB₃ | low (8–11) | UB | 69.4 (60.0) | 0.58 (0.62) | 0.56 (0.57) | 0.53 (0.51) | 0.66 (0.64) | 0.28 (0.26) | 2.4e-06 (2.2e-06) | 0.0 (0.0) |
| KB₃ | low (8–11) | EST | 81.8 (76.0) | 0.47 (0.48) | 0.50 (0.51) | 0.49 (0.45) | 0.64 (0.61) | 0.25 (0.01) | 3e-07 (3.3e-07) | 0.0 (0.0) |
| KB₃ | low (8–11) | UB_A | 86.6 (84.0) | 0.53 (0.54) | 0.59 (0.58) | 0.53 (0.50) | 0.69 (0.67) | 1.00 (1.00) | 1.4e-06 (1.3e-06) | 0.0 (0.0) |
| KB₃ | low (8–11) | EST diagnosis | |D| 4.0 (2.0) | spurious in D 3.4 (1.0) | checks 2517 (330) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₃ | mid (12–78) | Reduce(A) | 176.8 (181.0) | 0.28 (0.26) | 0.39 (0.38) | 0.47 (0.46) | 0.64 (0.63) | 1.00 (1.00) | 1e-06 (7.4e-07) | 1.8 (1.0) |
| KB₃ | mid (12–78) | ConMin k=1 | 177.4 (186.0) | 0.27 (0.25) | 0.37 (0.36) | 0.45 (0.43) | 0.59 (0.58) | 0.49 (0.43) | 2e-06 (1.6e-06) | 0.0 (0.0) |
| KB₃ | mid (12–78) | UB | 173.2 (179.0) | 0.29 (0.27) | 0.39 (0.39) | 0.48 (0.46) | 0.64 (0.63) | 0.75 (0.84) | 2e-06 (1.7e-06) | 0.0 (0.0) |
| KB₃ | mid (12–78) | EST | 175.0 (180.0) | 0.28 (0.27) | 0.39 (0.39) | 0.48 (0.46) | 0.64 (0.63) | 0.83 (0.93) | 1.4e-06 (1.3e-06) | 0.0 (0.0) |
| KB₃ | mid (12–78) | UB_A | 179.6 (184.0) | 0.28 (0.26) | 0.40 (0.38) | 0.48 (0.46) | 0.65 (0.63) | 1.00 (1.00) | 2e-06 (1.8e-06) | 0.0 (0.0) |
| KB₃ | mid (12–78) | EST diagnosis | |D| 1.8 (1.0) | spurious in D 1.8 (1.0) | checks 141 (19) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₃ | high (78–118) | Reduce(A) | 238.8 (230.0) | 0.22 (0.22) | 0.34 (0.34) | 0.40 (0.41) | 0.57 (0.58) | 1.00 (1.00) | 7.8e-06 (6.9e-06) | 0.0 (0.0) |
| KB₃ | high (78–118) | ConMin k=1 | 238.8 (230.0) | 0.22 (0.22) | 0.34 (0.34) | 0.40 (0.41) | 0.57 (0.58) | 1.00 (1.00) | 7.8e-06 (6.9e-06) | 0.0 (0.0) |
| KB₃ | high (78–118) | UB | 238.8 (230.0) | 0.22 (0.22) | 0.34 (0.34) | 0.40 (0.41) | 0.57 (0.58) | 1.00 (1.00) | 7.8e-06 (6.9e-06) | 0.0 (0.0) |
| KB₃ | high (78–118) | EST | 238.8 (230.0) | 0.22 (0.22) | 0.34 (0.34) | 0.40 (0.41) | 0.57 (0.58) | 1.00 (1.00) | 7.8e-06 (6.9e-06) | 0.0 (0.0) |
| KB₃ | high (78–118) | UB_A | 238.8 (230.0) | 0.22 (0.22) | 0.34 (0.34) | 0.40 (0.41) | 0.57 (0.58) | 1.00 (1.00) | 7.8e-06 (6.9e-06) | 0.0 (0.0) |
| KB₃ | high (78–118) | EST diagnosis | |D| 0.0 (0.0) | spurious in D 0.0 (0.0) | checks 11 (12) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₃ | 2-COV | Reduce(A) | 71.0 (71.0) | 0.41 (0.41) | 0.41 (0.41) | 0.71 (0.71) | 0.83 (0.83) | 1.00 (1.00) | 6.1e-10 (6.1e-10) | 0.0 (0.0) |
| KB₃ | 2-COV | ConMin k=1 | 71.0 (71.0) | 0.41 (0.41) | 0.41 (0.41) | 0.71 (0.71) | 0.83 (0.83) | 1.00 (1.00) | 6.1e-10 (6.1e-10) | 0.0 (0.0) |
| KB₃ | 2-COV | UB | 71.0 (71.0) | 0.41 (0.41) | 0.41 (0.41) | 0.71 (0.71) | 0.83 (0.83) | 1.00 (1.00) | 6.1e-10 (6.1e-10) | 0.0 (0.0) |
| KB₃ | 2-COV | EST | 71.0 (71.0) | 0.41 (0.41) | 0.41 (0.41) | 0.71 (0.71) | 0.83 (0.83) | 1.00 (1.00) | 6.1e-10 (6.1e-10) | 0.0 (0.0) |
| KB₃ | 2-COV | UB_A | 71.0 (71.0) | 0.41 (0.41) | 0.41 (0.41) | 0.71 (0.71) | 0.83 (0.83) | 1.00 (1.00) | 6.1e-10 (6.1e-10) | 0.0 (0.0) |
| KB₃ | 2-COV | EST diagnosis | |D| 0.0 (0.0) | spurious in D 0.0 (0.0) | checks 9 (9) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₄ | low (11–64) | Reduce(A) | 236.4 (232.0) | 0.60 (0.61) | 0.62 (0.61) | 0.65 (0.65) | 0.79 (0.78) | 1.00 (1.00) | 6e-23 (4.3e-26) | 31.6 (45.0) |
| KB₄ | low (11–64) | ConMin k=1 | 154.2 (116.0) | 0.71 (0.71) | 0.56 (0.54) | 0.83 (0.84) | 0.70 (0.68) | 2.2e-08 (1.6e-18) | 6.9e-07 (1e-07) | 0.0 (0.0) |
| KB₄ | low (11–64) | UB | 216.2 (200.0) | 0.66 (0.66) | 0.65 (0.65) | 0.67 (0.66) | 0.78 (0.78) | 0.13 (0.0027) | 4.1e-18 (4.4e-21) | 0.0 (0.0) |
| KB₄ | low (11–64) | EST | 234.6 (232.0) | 0.60 (0.61) | 0.62 (0.61) | 0.65 (0.65) | 0.78 (0.78) | 0.66 (1.00) | 9.2e-22 (8.3e-23) | 20.6 (0.0) |
| KB₄ | low (11–64) | UB_A | 240.6 (244.0) | 0.62 (0.62) | 0.65 (0.63) | 0.65 (0.65) | 0.79 (0.79) | 0.96 (0.95) | 1.6e-21 (1.1e-22) | 0.0 (0.0) |
| KB₄ | low (11–64) | EST diagnosis | |D| 3.0 (2.0) | spurious in D 1.8 (2.0) | checks 28223 (1278) | status found, node_limit | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₄ | mid (64–349) | Reduce(A) | 269.0 (266.0) | 0.65 (0.65) | 0.71 (0.71) | 0.72 (0.70) | 0.84 (0.82) | 1.00 (1.00) | 2.6e-08 (5.5e-16) | 2.0 (2.0) |
| KB₄ | mid (64–349) | ConMin k=1 | 250.6 (252.0) | 0.65 (0.66) | 0.69 (0.70) | 0.73 (0.71) | 0.81 (0.80) | 0.02 (0.0026) | 7.7e-08 (4.5e-15) | 0.0 (0.0) |
| KB₄ | mid (64–349) | UB | 266.0 (262.0) | 0.65 (0.66) | 0.72 (0.72) | 0.72 (0.70) | 0.84 (0.82) | 0.64 (0.87) | 2.6e-08 (6.6e-16) | 0.0 (0.0) |
| KB₄ | mid (64–349) | EST | 268.0 (264.0) | 0.65 (0.65) | 0.71 (0.71) | 0.72 (0.70) | 0.83 (0.82) | 0.94 (0.95) | 2.6e-08 (6.6e-16) | 0.0 (0.0) |
| KB₄ | mid (64–349) | UB_A | 276.4 (278.0) | 0.63 (0.62) | 0.71 (0.70) | 0.71 (0.68) | 0.83 (0.81) | 1.00 (1.00) | 2.6e-08 (1.3e-15) | 0.0 (0.0) |
| KB₄ | mid (64–349) | EST diagnosis | |D| 1.0 (1.0) | spurious in D 1.0 (1.0) | checks 69 (50) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₄ | high (349–524) | Reduce(A) | 270.0 (270.0) | 0.69 (0.69) | 0.76 (0.76) | 0.79 (0.79) | 0.88 (0.88) | 1.00 (1.00) | 2.7e-06 (1.2e-08) | 0.4 (0.0) |
| KB₄ | high (349–524) | ConMin k=1 | 265.4 (265.0) | 0.70 (0.69) | 0.76 (0.76) | 0.80 (0.79) | 0.87 (0.87) | 0.47 (0.51) | 2.7e-06 (3.3e-08) | 0.0 (0.0) |
| KB₄ | high (349–524) | UB | 269.2 (270.0) | 0.69 (0.69) | 0.77 (0.76) | 0.79 (0.79) | 0.88 (0.88) | 0.85 (1.00) | 2.7e-06 (1.4e-08) | 0.0 (0.0) |
| KB₄ | high (349–524) | EST | 269.6 (270.0) | 0.69 (0.69) | 0.76 (0.76) | 0.79 (0.79) | 0.88 (0.88) | 0.99 (1.00) | 2.7e-06 (1.2e-08) | 0.0 (0.0) |
| KB₄ | high (349–524) | UB_A | 270.0 (270.0) | 0.70 (0.69) | 0.77 (0.76) | 0.79 (0.79) | 0.88 (0.88) | 1.00 (1.00) | 2.7e-06 (1.4e-08) | 0.0 (0.0) |
| KB₄ | high (349–524) | EST diagnosis | |D| 0.4 (0.0) | spurious in D 0.4 (0.0) | checks 75 (58) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |
| KB₄ | 2-COV | Reduce(A) | 213.0 (213.0) | 0.52 (0.52) | 0.51 (0.51) | 0.81 (0.81) | 0.90 (0.90) | 1.00 (1.00) | 3.9e-20 (3.9e-20) | 0.0 (0.0) |
| KB₄ | 2-COV | ConMin k=1 | 213.0 (213.0) | 0.52 (0.52) | 0.51 (0.51) | 0.81 (0.81) | 0.90 (0.90) | 1.00 (1.00) | 3.9e-20 (3.9e-20) | 0.0 (0.0) |
| KB₄ | 2-COV | UB | 213.0 (213.0) | 0.52 (0.52) | 0.51 (0.51) | 0.81 (0.81) | 0.90 (0.90) | 1.00 (1.00) | 3.9e-20 (3.9e-20) | 0.0 (0.0) |
| KB₄ | 2-COV | EST | 213.0 (213.0) | 0.52 (0.52) | 0.51 (0.51) | 0.81 (0.81) | 0.90 (0.90) | 1.00 (1.00) | 3.9e-20 (3.9e-20) | 0.0 (0.0) |
| KB₄ | 2-COV | UB_A | 213.0 (213.0) | 0.52 (0.52) | 0.51 (0.51) | 0.81 (0.81) | 0.90 (0.90) | 1.00 (1.00) | 3.9e-20 (3.9e-20) | 0.0 (0.0) |
| KB₄ | 2-COV | EST diagnosis | |D| 0.0 (0.0) | spurious in D 0.0 (0.0) | checks 12 (12) | status found | e⁻ broken by Certain 0.0 (0.0) |  |  |  |

sol R of the repaired theory relative to Reduce(A), per fold: median and geometric mean of the ratio; share of the sol R gap (to 1) closed, linear and log scale.

| KB | bin | theory | folds | ratio median | ratio geo-mean | gap closed (linear) | gap closed (log) |
|---|---|---|---|---|---|---|---|
| KB₁ | low (4–5) | UB | 5 | 1.4 | 1.87 | 0.08 (0.04) | 0.24 (0.14) |
| KB₁ | low (4–5) | UB_A | 5 | 1.4 | 1.7 | 0.06 (0.03) | 0.20 (0.12) |
| KB₁ | mid (6–17) | UB | 5 | 1 | 1.13 | 0.04 (0.00) | 0.08 (0.00) |
| KB₁ | mid (6–17) | UB_A | 5 | 1 | 1.22 | 0.05 (0.00) | 0.11 (0.00) |
| KB₁ | high (17–26) | UB | 5 | 1 | 1 | 0.00 (0.00) | 0.00 (0.00) |
| KB₁ | high (17–26) | UB_A | 5 | 1 | 1 | 0.00 (0.00) | 0.00 (0.00) |
| KB₁ | 2-COV | UB | 0 | — | — | — | — |
| KB₁ | 2-COV | UB_A | 0 | — | — | — | — |
| KB₂ | low (10–39) | UB | 5 | 97.4 | 51 | 0.00018 (3.2e-06) | 0.23 (0.23) |
| KB₂ | low (10–39) | UB_A | 5 | 36.2 | 111 | 6.8e-06 (3.8e-06) | 0.23 (0.24) |
| KB₂ | mid (40–215) | UB | 5 | 1 | 1.42 | 0.00034 (0.00) | 0.03 (0.00) |
| KB₂ | mid (40–215) | UB_A | 5 | 1 | 2.29 | 0.00035 (0.00) | 0.06 (0.00) |
| KB₂ | high (215–323) | UB | 5 | 1 | 1.15 | 0.00017 (0.00) | 0.02 (0.00) |
| KB₂ | high (215–323) | UB_A | 5 | 1 | 1.15 | 0.00017 (0.00) | 0.02 (0.00) |
| KB₂ | 2-COV | UB | 3 | 1.64e+23 | 1.64e+23 | 0.02 (0.02) | 0.93 (0.93) |
| KB₂ | 2-COV | UB_A | 3 | 8.65e+16 | 8.65e+16 | 8.8e-09 (8.8e-09) | 0.68 (0.68) |
| KB₃ | low (8–11) | UB | 5 | 31 | 39.1 | 2.4e-06 (2.1e-06) | 0.22 (0.21) |
| KB₃ | low (8–11) | UB_A | 5 | 28.4 | 26.2 | 1.4e-06 (1.3e-06) | 0.19 (0.20) |
| KB₃ | mid (12–78) | UB | 5 | 1.96 | 3.12 | 1e-06 (8.5e-07) | 0.07 (0.05) |
| KB₃ | mid (12–78) | UB_A | 5 | 1.85 | 3.09 | 1e-06 (7.6e-07) | 0.07 (0.04) |
| KB₃ | high (78–118) | UB | 5 | 1 | 1 | 0.00 (0.00) | 0.00 (0.00) |
| KB₃ | high (78–118) | UB_A | 5 | 1 | 1 | 0.00 (0.00) | 0.00 (0.00) |
| KB₃ | 2-COV | UB | 2 | 1 | 1 | 0.00 (0.00) | 0.00 (0.00) |
| KB₃ | 2-COV | UB_A | 2 | 1 | 1 | 0.00 (0.00) | 0.00 (0.00) |
| KB₄ | low (11–64) | UB | 5 | 8.41e+05 | 5.16e+04 | 4.1e-18 (4.2e-21) | 0.18 (0.23) |
| KB₄ | low (11–64) | UB_A | 5 | 811 | 216 | 1.5e-21 (1.1e-22) | 0.09 (0.11) |
| KB₄ | mid (64–349) | UB | 5 | 2 | 1.53 | 1.2e-16 (4.5e-19) | 0.01 (0.02) |
| KB₄ | mid (64–349) | UB_A | 5 | 1.96 | 2.22 | 4.7e-16 (2.3e-16) | 0.02 (0.02) |
| KB₄ | high (349–524) | UB | 5 | 1 | 1.09 | 5.6e-10 (0.00) | 0.0044 (0.00) |
| KB₄ | high (349–524) | UB_A | 5 | 1 | 1.09 | 5.6e-10 (0.00) | 0.0044 (0.00) |
| KB₄ | 2-COV | UB | 2 | 1 | 1 | 0.00 (0.00) | 0.00 (0.00) |
| KB₄ | 2-COV | UB_A | 2 | 1 | 1 | 0.00 (0.00) | 0.00 (0.00) |

<!-- END generated -->

## Verdict

(i) **Dead features explain little of the solution-recall gap, and only under positive scarcity.** Share
of the log-scale sol R gap closed by repair (UB_A, mean (median)): lowest third .20 (.12) KB₁, .23 (.24)
KB₂, .19 (.20) KB₃, .09 (.11) KB₄; middle ≤ .11; highest .00 / .02 / .00 / .004. On **KB₄-high**
(349–524 positives) repair recovers nothing: UB_A/Reduce(A) sol R ratio median 1.00, geo-mean 1.09 —
the gap is not dead features. On the linear scale every share is ≤ .06.
(ii) **Singletons are a KB₁ phenomenon** (10/12 conflicts; 0/663 on KB₂–KB₄), so Certain is non-empty
only on KB₁ (≤ 1.6 per fold) and is 100 % spurious — the domain-completeness axiom holds on every fold.
(iii) **The residual is rejectors outside the cover, not vacuous constraints.** Spurious constraints in no
conflict are overwhelmingly R∖C (highest third: KB₂ 34.8 of 35.4 spurious, KB₃ 172.2 of 175.8, KB₄ 76.0
of 78.4); spurious V constraints are nearly all killers inside a conflict (residual V: mean 10.0 per fold on
KB₄ low, ≤ 2.2 elsewhere).
