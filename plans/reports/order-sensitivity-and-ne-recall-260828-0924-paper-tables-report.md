# Two paper tables: Reduce order-sensitivity, and the NE recall interval

Date 2026-08-28. Branch `feat/sosym-r1`, final code state (`c0f448f`). Both measured on
the 72-fold ConGen re-run plus busybox `2cov`/`rs_m`. No acquisition re-run: B′ is
recovered from a scored fold as `kb_constraints ∪ redundant_constraints`, **gated against
`n_mss` and holding on 72/72 folds**, and one Reduce pass is ~150 ms.

## Table A — spread of the score over Reduce's input order

10 cells across all five knowledge bases, 3 folds each, **20 permutations** of B′.
The memorized ¬e⁻ stay first, as the shipped code assembles them: permuting those would
measure something the shipped code does not do.

Spread = max − min over the 20 permutations, per fold.

| tier | metric | mean range | median range | max range | folds with zero spread |
|---|---|---|---|---|---|
| description | P | 0.1094 | 0.0350 | 0.5182 | 5/30 |
| description | R | 0.1106 | 0.0297 | 0.4615 | 7/30 |
| clause | P | 0.0915 | 0.0251 | 0.3262 | 2/30 |
| clause | R | 0.0744 | 0.0152 | 0.3636 | 2/30 |
| semantic | P | 0.0250 | 0.0060 | 0.3650 | 6/30 |
| **semantic** | **R** | **0.0556** | **0.0000** | 0.8385 | **21/30** |

### This CORRECTS the previously reported finding

The earlier claim — "the semantic tier is up to 17× more order-stable than description"
— rested on 3 cells × 1 fold × 5 permutations. At 10 cells × 3 folds × 20 permutations
it does not survive as stated:

- The description : semantic spread ratio has **median 2.4×**, range **0.0× to 21.3×**,
  with 6 cells at zero semantic spread (ratio undefined, not infinite in any useful sense).
- **On 7 of 30 folds the semantic tier is the LESS stable one** — arcade `2cov` all three
  folds (0.1833 vs 0.8385, 0.0747 vs 0.3231, 0.1061 vs 0.2308), REAL-FM-4 `rs_1n` f1,
  fqa `rs_2n` f2, busybox `2cov` f1/f2.

The defensible statement is narrower and about semantic RECALL specifically: it has
**zero spread on 21 of 30 folds** and a median spread of 0.0000, where description recall
has a median spread of 0.0297. Semantic recall is the most order-stable quantity measured.
It is not a uniform multiple, and on the degenerate `2cov` cells (train_pos = 0) the
ordering reaches semantic harder than it reaches description.

### Where the shipped run sits

Mean percentile of the shipped result within its own permutation distribution:
description P 0.34 / R 0.29, clause P 0.45 / R 0.42, semantic P 0.29. The published
numbers sit at or below the median of what a random reduction order would produce — the
shipped ordering is not a favourable draw. (Semantic R is not summarized this way: with
21/30 folds at zero spread the percentile is undefined for most of them.)

## Table B — how much the tiers understate recall by excluding NE

The three tiers score against the bias vocabulary and a ¬e⁻ has no bias id, so it is
excluded by the guard at `kb_comparator.py:293`. That is deliberate — the tiers measure
what was LEARNED — but the delivered theory is B′ ∪ NE, so reported recall is a lower
bound. This is the width of that bound: semantic P/R from the bias constraints alone
versus from the delivered theory, same folds.

72 folds, 42 deliver at least one ¬e⁻, **14 move**:

| fold | R bias | R +NE | ΔR | P bias | P +NE | ΔP |
|---|---|---|---|---|---|---|
| arcade-game 2cov f0 | 0.2385 | **1.0000** | +0.7615 | 0.7381 | 0.9220 | +0.1839 |
| REAL-FM-7 rs_m f2 | 0.7273 | **1.0000** | +0.2727 | 0.5714 | 0.6471 | +0.0756 |
| REAL-FM-7 2cov f1 | 0.8182 | **1.0000** | +0.1818 | 0.6923 | 0.7333 | +0.0410 |
| REAL-FM-4 rs_1n f1 | 0.9229 | **1.0000** | +0.0771 | 0.7104 | 0.7267 | +0.0162 |
| arcade-game ff f0 | 0.9462 | **1.0000** | +0.0538 | 0.6000 | 0.6132 | +0.0132 |
| arcade-game rs_1n f0 | 0.9538 | **1.0000** | +0.0462 | 0.5061 | 0.5179 | +0.0118 |
| arcade-game rs_2n f2 | 0.9538 | **1.0000** | +0.0462 | 0.3899 | 0.4012 | +0.0113 |
| arcade-game rs_3n f0 | 0.9538 | **1.0000** | +0.0462 | 0.4247 | 0.4362 | +0.0116 |
| arcade-game rs_3n f2 | 0.9538 | **1.0000** | +0.0462 | 0.4306 | 0.4422 | +0.0116 |
| REAL-FM-7 rs_3n f1 | 0.9545 | **1.0000** | +0.0455 | 0.8750 | 0.8800 | +0.0050 |
| REAL-FM-7 rs_m f1 | 0.9545 | **1.0000** | +0.0455 | 0.7500 | 0.7586 | +0.0086 |
| arcade-game rs_1n f1 | 0.9615 | **1.0000** | +0.0385 | 0.4883 | 0.4981 | +0.0098 |
| arcade-game rs_1n f2 | 0.9923 | **1.0000** | +0.0077 | 0.5059 | 0.5078 | +0.0019 |
| arcade-game rs_3n f1 | 0.9923 | **1.0000** | +0.0077 | 0.4358 | 0.4377 | +0.0019 |

Over the 42 folds that deliver a ¬e⁻: recall Δ mean **+0.0399**, max **+0.7615**;
precision Δ mean **+0.0096**, max **+0.1839**. Neither ever falls.

**Every fold that moves lands on recall exactly 1.0000.** On those folds the delivered
theory entails the whole target model, and the reported figure understates it by between
0.008 and 0.762. The extreme is arcade `2cov` fold 0, a degenerate cell with
train_pos = 0 where almost nothing is learned and the memorized negative carries the
theory.

This turns C6's "conservative lower bound" from a hedge into an interval. It is a
disclosure, not a proposed change: folding NE into the tiers would change what the tiers
measure, from learned to delivered.

## Unresolved

1. Table A's cells are 10 of 30 available. The `2cov` cells drive the counterexamples
   and are degenerate (train_pos = 0); a reader may reasonably ask whether they belong
   in the headline at all, which is an editorial call.
2. busybox contributes only `2cov` and `rs_m` here; `ff` was still running and `rs_1n`
   needs its own stretch.
3. Table B is computed on the ConGen re-run only. QuAcq delivers no NE, so it has no
   analogue — which is itself the reason the comparison in Table 13 is not symmetric.
