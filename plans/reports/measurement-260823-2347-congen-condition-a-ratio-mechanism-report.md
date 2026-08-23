# Why ConGen beats condition A — the mechanism, tested

Branch `feat/sosym-r1`, code commit `a0afe42`. Measured 2026-08-23 from 66 matched
`(kb, sampling, fold)` triples: ConGen partials in `data/results_sosym/congen/partials/`
against condition-A rows in `data/results_conmin/*_long.csv`. No new runs; analysis
only, during a gap while the sweep window worked.

## Result: both hypotheses are wrong, and the answer is sharper than either

| kb | checks ratio | ms/check ConGen | ms/check condA | **per-check ratio** | **wall ratio** | \|E⁻\| | \|NE\| |
|---|---|---|---|---|---|---|---|
| REAL-FM-7 | 0.99 | 0.47 | 2.32 | **0.20** | **0.20** | 2.2 | 0.89 |
| fqa | 1.09 | 17.15 | 46.01 | **0.37** | **0.41** | 14.3 | 0.94 |
| arcade | 0.98 | 6.35 | 52.96 | **0.12** | **0.12** | 6.3 | 0.94 |
| REAL-FM-4 | 1.00 | 20.95 | 188.06 | **0.11** | **0.11** | 9.0 | 0.92 |

**The per-check ratio is the wall-clock ratio.** ConGen does the same amount of
checking and each check costs 3×–9× less. The speedup is entirely per-check cost.

## The QuickXplain hypothesis: premise confirmed, conclusion refuted

Your premise holds — condition A does no QuickXplain minimization. `preprocessing_checks`
is **exactly 0** in every condition-A row of all four CSVs, while ConGen spends 18–213
checks in `shared_preprocessing_quickxplain_checks`. ConGen does *more* preprocessing,
not less.

But the conclusion does not follow, for two independent reasons:

1. **|NE| does not vary per KB.** Across all 66 folds, `n_ne ∈ {0, 1}` — while |E⁻|
   ranges 0 to 36. The NE population is one constraint or none, everywhere, regardless
   of knowledge base or how many negatives the fold trains on. A quantity that is
   always 0 or 1 cannot produce a 4× per-KB spread.
2. **It does not reduce the work.** Check counts agree at 0.98–1.09 in aggregate. If
   QuickXplain minimization were buying the speedup, ConGen would be doing visibly
   fewer checks. It is not.

## The drift hypothesis survives, but my original statement of it was wrong

You objected that drift predicts a roughly uniform factor while the data spreads 4×.
That objection is right against the way I stated it. The correct form:

> The change is at the **checker** level, not the algorithm level. Its benefit is
> proportional to how many redundant SAT assumptions a given knowledge base was
> carrying — which is a per-KB property. So a single code change produces a
> KB-dependent per-check saving, which is exactly the observed shape.

This fits the checker-gate split (split `is_consistent`/`find_model`, drop redundant
assumptions) landing after those CSVs were recorded. Same checks, cheaper checks,
saving varies by KB. It also explains why the ratio tracks neither bias size nor
|E⁺|: it tracks assumption redundancy, which neither of those measures.

**Still not independently confirmed.** What is confirmed is where the difference is
(per-check cost) and where it is not (amount of work, NE minimization). Attributing it
to a specific commit needs an A/B with the checker change reverted, which costs a run
and is not worth a window right now.

## Precision note, against my own earlier phrasing

In conversation I said REAL-FM-4's check counts matched "exactly, 2789 = 2789". That
was the **mean** over folds, not per-fold identity. Per fold: 9 of 66 exact, 29 more
within 2 %, 28 differing by up to ~13 % in both directions. The two computations are
close, not identical. The load-bearing claim survives in weaker form and is enough:
ConGen's check count is within about ±10 % of condition A's, so the 2×–9× wall-clock
gap cannot be explained by ConGen doing less work.

Caveat kept explicit: I have not proved `paper_consistency_checks` (ConGen) and
`checks_total` (condition A) count identical events. Their agreement across 4 KBs and
66 folds is evidence that they are commensurate, not proof.

Corroboration from an independent measure: the ledger's per-unit actuals are subprocess
wall-clock — interpreter start-up and model build included — and give the same ~0.13×,
so the ratio is not an artefact of which timer the fold JSON reports.

## What this means for the manuscript

**Compare ConGen to condition A on checks, not on wall-clock.** The check counts are
commensurate and machine-independent; the runtimes differ by a checker implementation
detail that has nothing to do with either algorithm. This reinforces the R1-Q4 framing
that check counts are the primary cost metric — here it is not just a preference, it is
the only one of the two that compares the algorithms rather than the code that ran them.

Any sentence that quotes ConGen runtime against a recorded ConMin condition-A runtime is
comparing two code states. Do not write one.

## Unresolved

1. Attributing the per-check saving to a named commit needs an A/B with the checker
   change reverted. Not scheduled; low value against the sweep.
2. Whether `paper_consistency_checks` and `checks_total` are the same accounting is
   assumed-commensurate, not verified.
