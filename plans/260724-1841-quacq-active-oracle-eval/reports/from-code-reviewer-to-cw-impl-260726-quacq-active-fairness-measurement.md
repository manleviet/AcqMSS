# QuAcq-active fairness measurement — REAL-FM-7 (GATED, no sweep)

Measure-only. quacq.py band-aid probe was env-gated + **reverted** (tree clean); no behavior change;
591p/1s green; solver pinned glucose4 (commit `28509ad`). Determinism cross-check on the probe's
aid→clause resolution = **True** (re-prepared describe reproduces the runner's kb_clauses exactly).

## Numbers (REAL-FM-7, glucose4, oracle max_queries=5000; |C_T|=22, |bias|=295)

| Condition | reason | queries | \|KB\| | sem P/R/F1 | desc P/R/F1 |
|---|---|---|---|---|---|
| **QuAcq-active** (oracle) | no_query | 342 | 10 | **1.00 / 0.50 / 0.667** | 0.30 / 0.23 / 0.261 |
| QuAcq example-only (rs_1n) | pool_exhausted | 23 | 1 | 1.00 / 0.045 / 0.087 | 1.00 / 0.077 / 0.143 |
| ConMin A (from prompt) | — | — | — | ~0.566 | — |

- **Material gain: YES.** QuAcq-active sem-F1 **0.667 ≫ example-only 0.087 (~7.7×)**, and even **>
  A's 0.566** on this KB. Active is NOT data-starved — self-generated queries recover real structure.
- **Sound:** sem/clause precision = **1.00** — every learned constraint is FM-entailed.
- **Recall capped at 0.50** (11/22 C_T clauses not entailed). desc precision 0.30 = only 3/10 learned
  match a *named* target; the other 7 are FM-entailed equivalents (sem sees them, desc doesn't) — the
  sem-vs-desc gap noted in the liveness red-team (L-3).

## Band-aid firing (FindC=⊥ drops `tested_c_id`)

| | count |
|---|---|
| total drops | **23** |
| — TRUE (clause ∈ C_T) | **14**  ← true, bias-representable constraints dropped |
| — genuinely unlearnable | 9 |
| empty-scope appends | 0 |
| distinct TRUE clauses dropped | 14 |
| — of those, **net-missing from final KB** | **7** |

Sample true drops: `c1 (-1,2)&(-2,1)`, `c9 (-7,5)`, `c11 (-8,1)`, `c15 (-9,10,11)&…` — ordinary binary
/ ternary FM constraints, all representable in the bias.

## Fairness verdict → GATE = branch 2 ("band-aid drops TRUE constraints")
- Gate test A (active ≫ example-only): **PASS**.
- Gate test B (band-aid drops few/no true): **FAIL** — 14/23 drops are true; ≥7 true clauses net-lost.
- ⇒ QuAcq-active's recall (0.50) is **majority our artifact**, not genuinely-unlearnable structure.
  9/23 drops are fair; the dominant identified cause of the missed recall is the band-aid dropping
  true, bias-representable constraints (FindScope multi-violation mislocalization).

**Consequence for the comparison (the reason this matters):** the band-aid makes QuAcq-active look
*worse* than it is → a "ConMin ≫ QuAcq-active" claim would be **unfair (understates QuAcq)**. Concretely
on REAL-FM-7, QuAcq-active (0.667) already ties/beats ConMin-A (0.566) **despite** the cap; with the
proper FindScope fix its recall could plausibly rise toward ~0.8 (sem-F1 → ~0.85), widening the gap
*in QuAcq's favor*. Reporting it as-is is not a fair active baseline.

## CW Impl decision (no sweep until chosen)
1. **Fix FindScope multi-violation localization** — removes the band-aid's true-drops, recovers recall;
   changes all QuAcq numbers (re-baseline). Highest-fidelity, most work. → this is the "#2" task.
2. **Report with an explicit caveat** — publish QuAcq-active as a *lower bound* ("recall floor; the
   liveness band-aid drops 14/23 localized candidates, ≥7 true → true recall ≥ measured"). Cheapest;
   honest; keeps the sweep unblocked.
3. **Drop QuAcq-active** as a reported column — weakest scientifically (it's already a strong baseline).

Recommendation: **1 if the paper leans on a QuAcq-active number; else 2.** Not 3 — the baseline is real
and strong. Either way, precision is sound (1.0), so no soundness risk in what's learned.

## Unresolved questions
1. Is the 14-true-drop / recall-0.5 pattern KB-general? Measured only on REAL-FM-7 (the mechanism —
   FindScope multi-violation mislocalization — is KB-general, but magnitude unverified on fqa/arcade/RE4).
2. If option 1 (FindScope fix): before or after the other 4 KBs' example-only/A baselines are frozen?
3. If option 2 (caveat): report sem (0.667) or desc (0.261) as the headline QuAcq-active number? (sem =
   entailment quality; desc = named-acquisition — the stricter acquisition claim.)
