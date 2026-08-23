# Why ConGen beats condition A — the mechanism, tested

> **Corrected 2026-08-24, twice.** The first version rested on a counting artifact
> (`|NE| ∈ {0,1}`) and overclaimed. The premise is fixed below. The NE-form
> hypothesis was then settled from recorded raw-vs-reduced data and is **dead**
> (≤2 % effect, identical check counts). The mechanism is per-check cost, located
> in the checker by elimination — but the cause is still not named, and fqa
> remains unexplained.

Branch `feat/sosym-r1`, code commit `a0afe42`. Measured 2026-08-23 from 66 matched
`(kb, sampling, fold)` triples: ConGen partials in `data/results_sosym/congen/partials/`
against condition-A rows in `data/results_conmin/*_long.csv`. No new runs; analysis
only, during a gap while the sweep window worked.

## Result: the mechanism is per-check cost; the cause is undetermined

| kb | checks ratio | ms/check ConGen | ms/check condA | **per-check ratio** | **wall ratio** | \|E⁻\| = \|NE\| |
|---|---|---|---|---|---|---|
| REAL-FM-7 | 0.99 | 0.47 | 2.32 | **0.20** | **0.20** | 2.2 |
| fqa | 1.09 | 17.15 | 46.01 | **0.37** | **0.41** | 14.3 |
| arcade | 0.98 | 6.35 | 52.96 | **0.12** | **0.12** | 6.3 |
| REAL-FM-4 | 1.00 | 20.95 | 188.06 | **0.11** | **0.11** | 9.0 |

**The per-check ratio is the wall-clock ratio.** ConGen does the same amount of
checking and each check costs 3×–9× less. The speedup is entirely per-check cost.

## The QuickXplain hypothesis: half-refuted, not refuted

Premise confirmed: condition A does no QuickXplain minimization. `preprocessing_checks`
is **exactly 0** in every condition-A row of all four CSVs, while ConGen spends 18–213
checks in `shared_preprocessing_quickxplain_checks`. ConGen does *more* preprocessing,
not less.

**Correction to this report's original premise.** It claimed `n_ne ∈ {0, 1}` across all
66 folds and concluded that NE cannot vary per KB. That was a counting artifact.
`ne_constraints` is a **single string whose conjuncts are the NE**, so `len()` returns 1
no matter how many there are. Counting conjuncts instead:

| fold | \|E⁻\| | conjuncts | distinct |
|---|---|---|---|
| fqa rs_3n f0 | 35 | 35 | 15 |
| REAL-FM-4 rs_2n f0 | 38 | 38 | 10 |
| arcade rs_1n f0 | 4 | 4 | 2 |

**|NE| = |E⁻| exactly** — `generate_ne.py` appends one per testcase and drops nothing.
So NE *does* vary per KB, and that leg of the refutation is gone.

What survives is the second leg, and only in its narrow form:

- **QuickXplain does not reduce the check count.** Aggregate ratio 0.98–1.09. So the
  hypothesis fails in the "ConGen does less work" form.
- **It is not refuted in the "ConGen's work is cheaper" form.** NE conjuncts are
  scope-minimized to 1.2–2.1 literals against knowledge bases of 14–291 features, which
  is a much smaller formula and would plausibly make each check cheaper.

### Testing the cost form: it does not rank-order either

| kb | n_feat | mean NE width | shrink (feat/width) | wall ratio |
|---|---|---|---|---|
| REAL-FM-4 | 291 | 1.44 | 202× | 0.11 |
| fqa | 179 | 2.06 | 87× | **0.37** |
| arcade | 65 | 1.21 | 54× | 0.12 |
| REAL-FM-7 | 14 | 1.75 | 8× | 0.20 |

If scope shrinkage drove the per-check saving, fqa — second-highest shrinkage — should be
second-most sped up. It is the **least** sped up, by a factor of three. The ordering
fails on exactly the knowledge base that is anomalous under every other hypothesis too.

With four points and one clear outlier, this neither confirms nor refutes the cost form.
It does mean the cost form has no positive support here.

## The NE-form hypothesis, settled from recorded data — it is dead

The `negatives` column of `data/results_conmin/*_long.csv` already carries `raw` vs
`reduced` for conditions C and C∪S: the same `GenerateNE(minimize=...)` switch, at one
commit, one checker, one set of folds. That isolates NE form exactly, with no new runs.

Condition C, 18 runs per cell:

Condition C, all five knowledge bases:

| kb | runs/cell | wall raw/reduced | wall Δ | checks Δ |
|---|---|---|---|---|
| REAL-FM-7 | 18 | 0.9892 | −1.08 % | **0.00 %** |
| fqa | 18 | 0.9794 | −2.06 % | **0.00 %** |
| arcade | 18 | 0.9806 | −1.94 % | **0.00 %** |
| REAL-FM-4 | 18 | 0.9995 | −0.05 % | **0.00 %** |
| busybox | 9 | 1.0169 | **+1.69 %** | **0.00 %** |

Check counts are identical to the decimal on every knowledge base, so `minimize` does
exactly what it documents and nothing more.

**State the range, not the direction.** Wall-clock differences span **−2.06 % to +1.69 %**
and busybox — the one that matters — reverses sign. It is noise-level either way, and no
claim about which form is faster is supported. busybox also has half the runs per cell.

**NE form changes neither the amount of work nor the cost of it.** A ≤2.1 % effect cannot
account for a 2×–9× gap, so the scope-minimization channel is closed, including the
version of it that survived the check-count argument.

### And NE is eliminated in every form, not just this one

The remaining caveat — that this is ConMin's condition C rather than ConGen — does not
bite, for a reason stronger than the raw-vs-reduced measurement. Condition A carries
`negatives = n/a`: it does **no** NE encoding at all, while ConGen carries |E⁻| conjuncts
in every check. Extra clauses make checks more expensive, so NE *presence* predicts ConGen
should be **slower** than A. It is 8× faster. The hypothesis points the wrong way, so NE is
eliminated whatever its form — minimized, raw, or absent.

> Hub correction arising from this, being made on the Cowork side: §7 C10 describes
> condition A as running "on raw negatives". It does not — `negatives = n/a`, no NE
> encoding. The calibration reference is clean, but for this reason rather than the one
> originally given.

## The drift hypothesis: now the only candidate left standing

Your objection — drift predicts a roughly uniform factor while the data spreads 4× — is
right against the way I first stated it. The repairable form is that the change is at the
**checker** level, so its benefit is proportional to how many redundant SAT assumptions a
knowledge base was carrying, which is a per-KB property. That fits the checker-gate split
(split `is_consistent`/`find_model`, drop redundant assumptions) landing after those CSVs
were recorded.

But it is a story, not a finding, and it is in exactly the same position as the scope
form of your hypothesis: it predicts a per-KB spread without predicting *this* spread, and
I have no measurement of per-KB assumption redundancy to test it against. It survives only
in the sense that nothing here rules it out.

**It is now the only candidate left, by elimination rather than by evidence.** NE form is
excluded above; check count is excluded by the parity result. What remains is that a check
costs less than it used to, for a reason located in the checker.

**It still does not explain fqa** on any quantity measured here — fqa is the least sped up
(0.37×) while sitting mid-pack on bias size, |E⁺|, |E⁻| and NE scope shrinkage.

### The one quantity where fqa is not mid-pack

Clause-expansion factor — CNF clauses per bias constraint, from `tab:fm_summary`:

| kb | clauses / \|B\| | expansion | wall ratio |
|---|---|---|---|
| fqa | 932 / 459 | **2.03** | 0.37 |
| arcade | 1,960 / 1,755 | 1.12 | 0.12 |
| REAL-FM-7 | 314 / 295 | 1.06 | 0.20 |

These are the same 1.06 / 1.12 / 2.03 figures verified independently on 2026-08-23 for the
semantic-precision denominator work, so they are not fitted to this question.

**Not a clean rank-order, and it should not be sold as one.** REAL-FM-7 is second-least
sped up at 0.20× while sitting *last* on expansion. This explains the outlier, not the
ordering.

What makes it worth following: it connects to the checker story. If the saving comes from
dropping redundant SAT assumptions, then the saving per bias constraint should depend on
how many clauses that constraint expands into — and fqa expands nearly twice as hard as
anyone else. That is where to look. Low priority; the cause being open blocks nothing.

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

## What this means for the manuscript — nothing directly

Correcting my earlier overreach: **no ConGen-versus-condition-A comparison enters the
manuscript in either unit.** Condition A is ConMin's condition, ConMin is unpublished, and
SoSyM cannot cite it. This report is an internal validation device and a schedule input,
not a source of paper text.

The methodological point it illustrates — that checks are machine-independent and
wall-clock is not — is already the settled design for the paper's own cost reporting
(hub §7 C10 decision 3; Table 9 reports both units per phase, checks for the published
bounds and solver calls for what the machine does). This finding strengthens the case for
that design. It does not add a comparison.

## Unresolved

1. **The cause of the per-check saving is open**, though now narrowed to the checker by
   elimination. Settling it needs an A/B with the checker change reverted. Not scheduled.
   A direct ConGen `minimize=False` run would remove the "different algorithm" caveat on
   the raw-vs-reduced result; ConGen does not plumb `minimize` today, so it needs a
   throwaway harness rather than a library change. Low value now that the effect is
   measured at ≤2 %.
2. Whether `paper_consistency_checks` and `checks_total` are the same accounting is
   assumed-commensurate, not verified.
3. **`len(fold['ne_constraints'])` is a trap** — it returns 1 regardless of |E⁻|, because
   the NE live as conjuncts inside one string. Anything reporting an NE count or KB
   composition must count conjuncts, or the field should become a list of NE descriptions
   with the join left to the renderer. This report was written off that trap once already;
   a paper table stating how many NE entered the KB would go wrong the same silent way.
4. **The conjuncts are not deduplicated** — REAL-FM-4 rs_2n fold 0 carries 38 conjuncts of
   which 10 are distinct, repeating `NOT(eShop = false)` many times. Semantically
   idempotent, so not a correctness problem, but a "distinct NE" count taken from the
   string would also be wrong. Neither item is urgent.
