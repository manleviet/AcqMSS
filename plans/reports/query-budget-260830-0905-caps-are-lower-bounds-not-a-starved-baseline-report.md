# The query cap: five budgets, no convergence, and why the figures are lower bounds

Date 2026-08-30. Branch `feat/sosym-r1`. Evidence: `data/results_sosym/cap_probe*`,
committed; busybox measured fresh at cap 1,000 on 2026-08-29.

The busybox column invites one objection — that the baseline was starved by the cap — and
the cap-sensitivity probes answer it directly.

## Across a 20× budget range, nothing converges

**Every run, at every cap, on every model, stops on `max_queries`.** Not one of the
fourteen configurations reaches `no_query` or `pool_exhausted`. The budget is never what
the method finishes inside; it is always what the method is cut off by.

Learned constraints, as the **mean over folds** — the aggregation the tables use:

| model | 250 | 500 | 1,000 | 2,000 | 5,000 | growth |
|---|---|---|---|---|---|---|
| REAL-FM-4 RS(n) | 4.33 | 7.33 | 9.00 | 9.00 | 12.33 | **2.8×** over 20× budget |
| arcade RS(n) | 11.00 | 18.00 | 24.33 | 26.33 | 32.67 | **3.0×** over 20× budget |

| model | 1,000 | 5,000 | 10,000 | 20,000 | growth |
|---|---|---|---|---|---|
| fqa RS(n) | 12.00 | 17.33 | 21.67 | 22.33 | **1.9×** over 20× budget |

So the defensible statement is not "we capped at 1,000" but: **across five budgets spanning
20×, no configuration converged and the return per query collapsed, so the reported
figures are lower bounds and a larger budget would not change the conclusion.**

fqa is the sharpest case: from 10,000 to 20,000 queries — a doubling — the mean KB moves
21.67 → 22.33, two thirds of one constraint.

## A correction to how these rows were first quoted

The rows were initially given as fold 0: REAL-FM-4 `3 → 3 → 4 → 4 → 4` and arcade
`10 → 21 → 27 → 30 → 45`, read as "a 20× budget buys one constraint on one model and 4.5×
on the other". Both figures are fold 0, and by the aggregation convention settled the day
before — a cell is the mean over folds — neither is the cell value.

On fold means the picture is more uniform and less dramatic: 2.8× and 3.0×, not 1.2× and
4.5×. REAL-FM-4 fold 0 is its least responsive fold (3→4) while fold 1 goes 4→18; arcade
fold 0 is its most responsive (10→45) while fold 1 goes 11→21. Quoting fold 0 understated
one model and overstated the other, in opposite directions.

The conclusion survives and is easier to defend: **both models roughly triple across a 20×
budget, and neither converges at any of them.**

## busybox at cap 1,000

| cell | wall | queries | stop | learned | bias |
|---|---|---|---|---|---|
| 2-COV fold 0 | 2.238 h | 1,000 | `max_queries` | 5 | 6,635 |
| FF fold 0 | 2.289 h | 1,000 | `max_queries` | 9 | 6,635 |

≈ 8.1 s per query. For contrast, `example_only` on the same cells stops on
`pool_exhausted` after 53 and 195 queries with a single constraint learned.

Roughly 0.1% of the bias, at both query modes. On the largest knowledge base the iterative
baseline is not merely slower — it is barely learning, and the cap-sensitivity rows say
that is a property of the method's return per query rather than of the budget we chose.

## Estimating from one fold: when it is safe

The two busybox cells came out 2% apart while their example pools differ 19-fold (2-COV
has 14 examples, FF has 267). Both stop on `max_queries`, never on pool exhaustion, so
cost is the cap times the per-query price and the sampling barely participates.

arcade was the opposite: pool-bound, and an estimate extrapolated from RS(n) — the cell
with the largest pool and therefore the cheapest — missed 2-COV by 21×.

**The rule is the discriminator, not the outcome: extrapolate only within the same binding
constraint.** Cap-bound cells predict cap-bound cells; a pool-bound cell predicts nothing
outside its own pool size. That is what makes the next estimate safe rather than lucky.

For the record, the ~27 h figure first offered for these twelve folds was arrived at by
extrapolating from busybox RS(n), the cheapest cell, and landed near the measured 27.3 h.
A correct number from a wrong method is not a success and is not cited as one here.

## Unresolved

1. The cap-sensitivity probes cover RS(n) on three models. No 2-COV or FF cell has been
   swept across caps, and those are the cells where the pool is smallest.
2. busybox has no cap-sensitivity data at all; its 1,000-query figures are a single point.
