# The example_first spin: measurement, fix, and a withdrawn direction

Branch `feat/sosym-r1`, code commit `daa7226`. Measured 2026-08-24.
Suite **675 passed, 1 skipped**; flamapy-fm / -fw / -sat `2.6.0.dev4`, canonical
`../explanation` editable. `git status --porcelain data/results/` empty throughout.

## The defect

`generate_from_sat` returns the first candidate in `remaining_bias` yielding a model.
When FindC cannot isolate a constraint for that query, nothing leaves
`remaining_bias` — the band-aid that would drop it is scoped to oracle mode — so the
next call starts at the same candidate and returns the identical query. `quacq.py:257`
documents this and states example_first's SAT fallback is not covered.

**The reading it destroyed.** arcade's KB was set-identical at caps 1,000 / 2,000 /
5,000, which reads as saturation. Its last novel query is at index **1,023**. The cap
at which it "saturated" is the index at which the spin began. The KB table could not
have shown this; only the query stream could.

## Measurement, pre-fix, cap 5,000

| kb | fold | distinct | last novel query | queries after it |
|---|---|---|---|---|
| arcade | 0 | 218 | 227 | 4,773 |
| arcade | 1 | 316 | 318 | 4,682 |
| arcade | 2 | 556 | **1,023** | 3,977 |
| fqa | 0 | 103 | 103 | 4,897 |
| fqa | 1 | 609 | 641 | 4,359 |
| fqa | 2 | 278 | 4,637 | 363 |

**State the defect as when novelty stopped, not as a repeat fraction.** A healthy run
repeats 60–70 % — FindScope narrows and FindC discriminates by re-querying. An earlier
version of this analysis, and N12's first draft, used the repeat fraction and thereby
overstated the defect.

## The fix

Skip a candidate whose query has already been proposed; move to the next. It does
**not** drop the candidate from `remaining_bias` — that is the oracle band-aid, which
the code itself calls "a recall trade-off … the dropped candidate may be a TRUE,
bias-representable constraint". The candidate stays askable and becomes reachable
again once `learned_kb` grows, since `learned_kb` is part of the assumption set and a
different set yields a different model. Terminates: `remaining_bias` is finite and each
call either returns a query never returned before or exhausts the list.

### Verification, four gates

| gate | result |
|---|---|
| example_only untouched | **PASS** — queries, KB sizes, constraint sets, stop reasons identical on fqa and arcade at caps 1,000 and 5,000 |
| spin removed | **PASS** — last novel query moves from 103–1,023 to **4,990–5,000** |
| recall impact, measured | **PASS, and it gains** — fqa 2→16, 14→18, 5→18; arcade 10→45, 12→21, 22→32 |
| suite | 675 passed, 1 skipped, unchanged |

example_only's immunity is structural, not incidental: it dispatches to
`generate_from_pool`, whose body (AST-checked) never calls `generate_from_sat`; the
pool index only increments, so a query cannot be re-proposed; and no discriminating
generator is constructed for that mode.

## ⛔ Withdrawn: the Table 14 direction

I compared post-fix QuAcq `n_kb` (16–45) against ConGen's (125–184), computed a ratio,
and reported that Table 14 "does not look like inverting". **That inference is not
available and the comparison is withdrawn.**

The paper's own Table 10 refutes it. On these same knowledge bases under these same
runs, arcade's *identical* KB scores `.275` on description and `.525` on semantics — a
factor of 1.9 from the choice of metric alone. That divergence is why the semantic tier
exists.

Counts bound nothing in either direction. Recall is entailment-based, so a compact KB
can entail a large target theory and QuAcq's 16–45 does not cap its recall. A large KB
can be redundant, so ConGen's 125–184 does not floor its precision. "Size is not
structure" was the right caveat and it is stronger than I stated: the comparison is not
merely uninformative, it invites an inference the paper argues against elsewhere.

Also corrected: I described the ratio as "an order of magnitude". Measured, it is
**3.82× to 8.76×** (fqa 8.19 / 7.56 / 6.94; arcade 3.82 / 8.76 / 5.34).

**What survives:** the fix strengthened the baseline substantially. Magnitude in
structural terms is unknown until the semantic scorer runs. No direction on Table 14
is reported.

## Recorded, not explained

busybox shows **no spin at 854 features** — 2 FindC-no-constraint warnings, both on
distinct scopes — while both small KBs spun at 89–98 % of budget. If the pattern holds
it belongs in N12 as an observation. No theory offered.

## Void

The entire pre-fix cap probe, and all cost numbers from the pre-fix probes: every cell
priced a loop. Their **recall baselines remain valid** and are the pre/post table above.
Labelled pre-patch, cost-void.

## Open

1. **Where does learning stop?** Post-fix runs still produce novelty at ~4,990 of
   5,000, so 16–45 is a lower bound that rises with budget. Tonight's phase 2a runs fqa
   to 20,000. Until it lands, the cap question is bounded, not answered.
2. **The cap decision** is downstream of (1) and of the semantic scorer.
3. **A5 exact-equivalence** (added to the ConGen branch) is queued behind the cap work.
