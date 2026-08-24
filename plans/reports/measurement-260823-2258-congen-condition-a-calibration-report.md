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

**Cause — superseded, see the mechanism report.** This section originally guessed at
drift. The mechanism was then located: check counts agree with condition A at
0.98–1.09, and the per-check time ratio equals the wall-clock ratio, so the gap is
the cost of a check rather than the number of them. NE form is eliminated in every
form. The remaining candidate is checker-level, by elimination rather than evidence,
and fqa is unexplained. Full working in
`measurement-260823-2347-congen-condition-a-ratio-mechanism-report.md`.

## What went into the ledger

Not one global multiplier. A single ratio fitted across these cells would be
dominated by knowledge bases of 6 to 14 features, and the only unit that can
actually break a window is an 854-feature one. The ledger carries a per-KB map,
each KB charged at *its own worst observed cell*, with the safety factor still on
top:

```
{"REAL-FM-7": 1.0, "fqa": 1.0, "arcade": 0.44, "REAL-FM-4": 0.5,
 "busybox": 0.20, "default": 1.0}
```

**busybox was deliberately absent and charged the full condition-A estimate** until it
had a measurement of its own: it is 60× larger than anything else here, and letting a
ratio gathered on arcade authorise starting a 28.6 h unit is exactly the mistake the
budget check exists to prevent. It entered on 2026-08-24 at 0.20× — its own `ff`
measurement of 0.166×, rounded up — and on that basis only.

## What this does to the schedule — measured, 2026-08-24

The extrapolation this section originally declined has now been replaced by a
measurement. **busybox `ff` fold 0: 0.6303 h against a 3.7923 h reference = 0.166×.**
busybox is slower than the 0.10–0.13 cluster and faster than fqa, and it did not have
to be either.

Projecting *within* busybox — which the REAL-FM-4 size-step control supports — at
0.166×:

| | reference | at 0.166× |
|---|---|---|
| busybox `ff`, 3 folds | 11.38 h | 1.89 h |
| busybox `rs_1n`, per fold | 28.56 h | **4.75 h** |
| busybox `rs_1n`, 3 folds | 85.69 h | **14.24 h** |

**The "keep or cut busybox" fork dissolves.** All three `rs_1n` folds fit in a single
overnight stretch rather than needing a two-week extension. Charged with the safety
factor the unit is 7.1 h/fold, so it is refused by a 6.5 h office window and taken by
an evening one — which is the schedule, not a judgement call.

## First window, for the record

Budget 0.3 h, wall-clock 9m23s, **59 units done, 0 failed**. The queue refused
REAL-FM-4 `rs_1n`/`rs_2n`/`rs_3n` and busybox `ff` on budget and exited cleanly
with 0.14 h unspent. ConGen is now complete for REAL-FM-7 (all 6 samplings), fqa
(all 6), arcade (5 of 6) and REAL-FM-4 (3 of 6).

## Unresolved

1. No prose compares ConGen runtime to recorded condition-A runtime — they are not
   from the same code state, and condition A belongs to an unpublished paper that
   SoSyM cannot cite in any case. Internal validation only.
2. ~~busybox's ratio is unmeasured~~ — measured 2026-08-24 at 0.166× on `ff` fold 0,
   n=1. Folds 1–2 confirm or refute; `rs_1n` remains a within-KB projection.
3. QuAcq's 168 units still carry no estimate; step 4's probe fills them.
