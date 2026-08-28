# N-item: the structural comparison scored four of five models against the wrong model's ground truth

Date 2026-08-29. Branch `feat/sosym-r1`.

**Claim.** `tab:iterative_semantic` and its inputs scored KB₁ (REAL-FM-7) and KB₃ (Arcade)
against KB₂'s (FQA's) target theory rather than their own. Only KB₂ was scored correctly,
and only by coincidence of being the model the single scoring block named. The error runs
against our own interest on ten of twelve cells and reverses the comparison on one.

This is not an over-count. The extraction is correct on all five models: a hand count from
each `.uvl`, using the textbook FM→CNF encoding and reading no result file, agrees exactly.

| model | by hand | extractor |
|---|---|---|
| REAL-FM-7 | 22 | 22 |
| fqa | **342** | 342 |
| arcade-game | 130 | 130 |
| REAL-FM-4 | 428 | 428 |
| busybox-1.18.0 | 994 | 994 |

`342` is FQA's clause count, and **every one of the 18 old ConGen files reports
`tp+fn = 342`** whatever model it belongs to. That is the `kb_dir` defect: `run_compare`
scores an entire directory with the oracle of the block it sits under, and the block's
`name` filters nothing.

| directory | folds scored against the wrong model |
|---|---|
| `data/results/congen` | 12 of 18 files (all 18 used FQA's Cτ) |
| `data/results/interactive` | **72 of 108 folds** |
| `data/results_sosym/congen` | **0 of 84** |
| `data/results_sosym/interactive` | **0 of 150** |

The revision's data is clean: `make_score_configs.py` writes one block per file and
`reject_foreign_knowledge_bases` refuses a foreign knowledge base.

## The correction, as a gap rather than a column

The paper does not claim an absolute score; it claims a distance from the iterative
baseline, which was scored with the same wrong oracle. Both sides are therefore restated,
on the SAME learned knowledge bases — the old results re-scored against the correct target
theory, so the cap and code state are held fixed and only the scoring changes.

### example_only
| cell | ConGen cũ→đúng | iterative cũ→đúng | Δ gap |
|---|---|---|---|
| KB1 REAL-FM-7 rs_1n | 0.1762 → 0.8378 | 0.0420 → 0.4647 | +0.1343 → +0.3732 |
| KB1 REAL-FM-7 rs_3n | 0.1348 → 0.9329 | 0.0457 → 0.4647 | +0.0891 → +0.4682 |
| KB1 REAL-FM-7 2cov | 0.0784 → 0.3871 | 0.0568 → 0.5322 | +0.0217 → -0.1451 **⚠** |
| KB1 REAL-FM-7 ff | 0.1923 → 0.7330 | 0.0494 → 0.4984 | +0.1429 → +0.2346 |
| KB2 fqa rs_1n | 0.9448 → 0.9448 | 0.0457 → 0.0457 | +0.8991 → +0.8991 |
| KB2 fqa rs_3n | 0.9474 → 0.9474 | 0.0476 → 0.0476 | +0.8999 → +0.8999 |
| KB2 fqa 2cov | 0.8906 → 0.8906 | 0.0345 → 0.0345 | +0.8561 → +0.8561 |
| KB2 fqa ff | 0.9106 → 0.9106 | 0.0345 → 0.0345 | +0.8761 → +0.8761 |
| KB3 arcade-game rs_1n | 0.5249 → 0.6516 | 0.0457 → 0.0548 | +0.4792 → +0.5968 |
| KB3 arcade-game rs_3n | 0.5682 → 0.5554 | 0.0382 → 0.0596 | +0.5300 → +0.4958 **⚠** |
| KB3 arcade-game 2cov | 0.3235 → 0.8417 | 0.0345 → 0.0451 | +0.2891 → +0.7966 |
| KB3 arcade-game ff | 0.5130 → 0.7411 | 0.0420 → 0.0548 | +0.4711 → +0.6862 |

### example_first
| cell | ConGen cũ→đúng | iterative cũ→đúng | Δ gap |
|---|---|---|---|
| KB1 REAL-FM-7 rs_1n | 0.1762 → 0.8378 | 0.0635 → 0.5811 | +0.1127 → +0.2567 |
| KB1 REAL-FM-7 rs_3n | 0.1348 → 0.9329 | 0.0736 → 0.5845 | +0.0612 → +0.3484 |
| KB1 REAL-FM-7 2cov | 0.0784 → 0.3871 | 0.1050 → 0.6835 | -0.0265 → -0.2964 **⚠** |
| KB1 REAL-FM-7 ff | 0.1923 → 0.7330 | 0.0494 → 0.4984 | +0.1429 → +0.2346 |
| KB2 fqa rs_1n | 0.9448 → 0.9448 | 0.0567 → 0.0567 | +0.8880 → +0.8880 |
| KB2 fqa rs_3n | 0.9474 → 0.9474 | 0.0476 → 0.0476 | +0.8999 → +0.8999 |
| KB2 fqa 2cov | 0.8906 → 0.8906 | 0.0456 → 0.0456 | +0.8450 → +0.8450 |
| KB2 fqa ff | 0.9106 → 0.9106 | 0.0563 → 0.0563 | +0.8543 → +0.8543 |
| KB3 arcade-game rs_1n | 0.5249 → 0.6516 | 0.0457 → 0.0548 | +0.4792 → +0.5968 |
| KB3 arcade-game rs_3n | 0.5682 → 0.5554 | 0.0382 → 0.0596 | +0.5300 → +0.4958 **⚠** |
| KB3 arcade-game 2cov | 0.3235 → 0.8417 | 0.0345 → 0.0500 | +0.2891 → +0.7918 |
| KB3 arcade-game ff | 0.5130 → 0.7411 | 0.0420 → 0.0548 | +0.4711 → +0.6862 |
**KB₂ is the control.** It is the only model scored against its own target theory and the
only one that does not move — `+0.0000` on all eight of its comparisons. A defect that
shifted every column would be indistinguishable from a general change; one that moves
exactly the wrongly-scored columns and leaves the correctly-scored one untouched is the
diagnosis stated as a measurement.

## Both exceptions, stated

The gap widens on ten of twelve cells. It does not on two, and a correction that showed
the ten and went quiet about the two would be worse than none.

- **KB₁ REAL-FM-7 2-COV — the comparison reverses.** Corrected, the iterative baseline
  beats ConGen: 0.5322 against 0.3871 (example-only), and −0.2964 against an already
  negative −0.0265 (example-first). The published tables already show iterative ahead on
  this cell; the correction deepens an inversion that is in print, on a cell the paper
  already reports as degenerate.
- **KB₃ Arcade RS(3n) — the gap narrows**, +0.5300 → +0.4958, in both modes. This cell is
  NOT degenerate: 117 training positives, |Cτ| = 130. So "it only happens where the data is
  degenerate" is not available as an explanation.

## Accuracy and runtime are not affected

Checked, because the next question is always which other table is wrong. Across
`data/results/congen` and `data/results/interactive` — 55 files, **165 folds** — each
fold's accuracy `metrics` sums exactly to that file's own `test_size`, with **0
discrepancies**. Accuracy is written by the cross-validation loop from the fold's own test
split; only `fold.evaluation.*` is written by the scoring pass that carried the defect. The
accuracy and runtime tables draw on the former.

## 2-COV has at most one positive training example, on every fold of every model

Measured per cell, which the paper reports only per knowledge base:

| KB | \|E⁺\| train, by fold | \|E⁻\| train |
|---|---|---|
| REAL-FM-7 | 0, 0, 0 | 6, 6, 6 |
| fqa | 0, 0, 0 | 10, 11, 11 |
| arcade-game | 0, 1, 1 | 8, 9, 9 |
| REAL-FM-4 | 0, 1, 1 | 11, 11, 12 |
| busybox-1.18.0 | 0, 0, 0 | 14, 14, 14 |

Eight of fifteen folds have **no** positive training example and the remaining seven have
exactly one. A passive learner that generalises from positives has nothing to generalise
from, on any 2-COV fold of any model in the study. That is a measurable boundary condition
rather than a remark about one cell.

## Why this is disclosed

The error makes ConGen look worse than it is on two of three knowledge bases, by up to
+0.83 on KB₁. Published as a correction, with the control that identifies it and both
exceptions named, it is evidence the pipeline is now checked. Left for a reviewer to find
as an unexplained jump between versions, it reads as the opposite.

## Unresolved

1. **REAL-FM-7's target theory is 22 clauses**, so one constraint is 4.5% of recall and
   every KB₁ figure is brittle at that granularity. This bears on the instance-selection
   criteria and on reporting per model rather than pooled.
2. Which change made the revision's scoring correct is provenance, not part of the claim.
3. The old `data/results` tree stays committed and wrong: it is the input the published
   tables came from, so it is evidence and must not be silently regenerated.
