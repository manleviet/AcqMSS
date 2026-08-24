# Step 2 calibration — the ConGen / condition-A ratio

Branch `feat/sosym-r1`, code commit `e1908fd`. Measured 2026-08-23, first home
window. 59 ConGen folds, one process per fold, all output to
`data/results_sosym/`; `git status --porcelain data/results/` empty throughout.

## The premise the handoff asked me to check, checked

> "Every figure below is derived from `data/results_conmin/*_long.csv`, condition
> A, which is AcqMss only. ConGen is AcqMss plus Reduce, so all of them are
> **floors** of unknown tightness."

**Falsified.** ConGen ran *faster* than condition A on every cell with a
non-trivial reference. The estimates are ceilings, by roughly 2× to 9×.

Reference = `mean(total_ms)/3.6e6` over the three condition-A folds in
`data/results_conmin/*_long.csv`. Observed = mean wall-clock of the ConGen fold,
one fold per process.

| kb | sampling | condA h/fold | ConGen h/fold | ratio |
|---|---|---|---|---|
| REAL-FM-4 | ff | 0.0906 | 0.0114 | 0.13× |
| REAL-FM-4 | rs_m | 0.0106 | 0.0014 | 0.13× |
| REAL-FM-4 | 2cov | 0.0014 | 0.0006 | 0.43× |
| arcade | rs_3n | 0.1340 | 0.0146 | 0.11× |
| arcade | rs_2n | 0.0677 | 0.0081 | 0.12× |
| arcade | rs_1n | 0.0253 | 0.0032 | 0.13× |
| arcade | rs_m | 0.0041 | 0.0007 | 0.16× |
| arcade | 2cov | 0.0009 | 0.0003 | 0.37× |
| fqa | rs_3n | 0.0212 | 0.0093 | 0.44× |
| fqa | rs_2n | 0.0126 | 0.0045 | 0.35× |
| fqa | rs_1n | 0.0037 | 0.0015 | 0.40× |
| fqa | ff | 0.0010 | 0.0005 | 0.50× |
| REAL-FM-7 | all six | ≤0.0007 | ≤0.0002 | 0.20×–1.00× |

Over the folds whose reference is ≥ 0.01 h — the only ones where a window could
plausibly fail to hold a unit — **median 0.13×**.

**Read the spread only on those cells.** Sub-0.01 h references are dominated by
interpreter start-up, and a ratio taken over one describes process overhead, not
ConGen. Quoting them inflates the apparent within-KB variability by 3×:

| kb | all cells | **cells with reference ≥ 0.01 h** |
|---|---|---|
| arcade | 0.113–0.370 | **0.113–0.125** (3 samplings) |
| REAL-FM-4 | 0.101–0.429 | **0.101–0.132** (5 samplings) |
| fqa | 0.354–0.667 | **0.354–0.440** (2 samplings) |
| REAL-FM-7 | 0.200–1.000 | *no cell qualifies* |
| busybox | — | **0.166** (`ff`, 1 cell) |

### Within-KB projection is supported; cross-KB is not

The data contains one controlled size comparison, and it is reassuring:

| REAL-FM-4 | reference | ratio |
|---|---|---|
| rs_1n | 0.480 h | 0.108 |
| rs_2n | 1.774 h | 0.106 |
| rs_3n | 4.174 h | 0.101 |

An **8.7× size step moves the ratio by 6 %**. So projecting a ratio across samplings
*within* a knowledge base is sound, and busybox `ff` → `rs_1n` is a 7.5× step —
smaller than the one already validated.

**The cross-KB refusal stands unchanged**, and fqa is the proof: it sits 3× away from
every other knowledge base on the same metric. A ratio measured on one KB licenses
nothing about another.

⚠ **A nominal estimate is not a reference.** busybox `rs_m` has no condition-A figure
at all — its 0.2 h is a placeholder chosen to make the unit schedulable. Computing
`actual / estimate` over it produced a "0.060× ratio" against a number nobody
measured. Units now carry `estimate_source`, and the ratio is restricted to ConGen
units with a genuine condition-A reference.

The two cells the handoff named are both in there: REAL-FM-4 `rs_1n`'s reference
reproduces exactly (0.4801 h/fold measured against the handoff's 0.48), and
arcade `rs_3n`'s does too (0.1340 against ≤0.13). The estimates were right about
condition A. What is wrong is the assumption about which side of it ConGen falls.

**Hypothesis, not verified here**: the checker-gate split (~4.2× measured) and
the C10 profiler hoisting both landed after those CSVs were recorded. That would
account for a several-fold across-the-board speedup. Worth confirming before the
number is used in prose, since it changes what Table 7/8 is comparing.

## What went into the ledger

Not one global multiplier. A single ratio fitted across these cells would be
dominated by knowledge bases of 6 to 14 features, and the only unit that can
actually break a window is an 854-feature one. The ledger carries a per-KB map,
each KB charged at *its own worst observed cell*, with the safety factor still on
top:

```
{"REAL-FM-7": 1.0, "fqa": 1.0, "arcade": 0.44, "REAL-FM-4": 0.5, "default": 1.0}
```

**busybox is deliberately absent and charges the full condition-A estimate.** It
has no measurement, it is 60× larger than anything here, and letting a ratio
gathered on arcade authorise starting a 28.6 h unit is exactly the mistake the
budget check exists to prevent.

## What this does to the schedule, and what it does not

If the 0.13× median held at busybox scale, the §8 arithmetic would change
completely: the 117.5 h ConGen total would be ~15 h, and busybox `rs_1n` would
drop from 28.6 h/fold to ~3.7 h/fold — inside a single home window, which would
retire the "keep or cut busybox" fork without needing the two-week extension.

**That extrapolation is not licensed and I have not made it.** Every measured
ratio comes from a model of 6 to 14 features. busybox is 854. The ratio could
differ in either direction — a large bias changes the solver's working set, and
Reduce's cost does not obviously scale like AcqMss's.

The measurement that settles it is **busybox `ff`**: reference 3.79 h/fold, so
even at 1.00× it fits a home window, and it is the only large-KB cell that is both
affordable and informative. Running it yields the busybox ratio, which is what the
busybox decision actually turns on. It is next in the queue.

## First window, for the record

Budget 0.3 h, wall-clock 9m23s, **59 units done, 0 failed**. The queue refused
REAL-FM-4 `rs_1n`/`rs_2n`/`rs_3n` and busybox `ff` on budget and exited cleanly
with 0.14 h unspent. ConGen is now complete for REAL-FM-7 (all 6 samplings), fqa
(all 6), arcade (5 of 6) and REAL-FM-4 (3 of 6).

## Unresolved

1. Confirm the speedup hypothesis before any prose compares ConGen's runtime to
   the recorded ConMin condition-A numbers — they are not from the same code.
2. busybox's ratio is unmeasured and the busybox schedule decision depends on it.
3. QuAcq's 171 units still carry no estimate; step 4's probe fills them.
