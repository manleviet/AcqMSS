# STAGE-B diagnosis — QuAcq true-constraint losses: GATE-B = STOP, duplicate/_narrow premise refuted

Read-only pop-tracer (env-gated TracingDict in quacq.py + `_narrow` trace in findc.py, **reverted** —
`git diff` vs HEAD empty, 0 residue). REAL-FM-7, glucose4, oracle max_q=5000. test_quacq 50p.
**No fix written.** GATE-B tripped: the Stage-B fix target is refuted by measurement.

## TL;DR
CW Impl's Stage-B hypothesis — "`_narrow_with_generator` drops a TRUE duplicate (160); duplicate
encodings kill the constraint" — is **empirically FALSE**. `_narrow` popped **0** constraints all run;
**0** true clauses died from all-duplicates-popped. **160 was pruned by `prune_rejecting`**, not by
discrimination. The real losses are elsewhere and are **not a small QuAcq-local fix**. STOP; re-decide.

## Pop-site distribution (274 total pops; the ground truth)
| pops | site | true-by-clause pops |
|---|---|---|
| **241** | `prune_rejecting` (sat_utils.py:41) | **5** |
| 23 | band-aid (quacq.py:263) | **14** |
| 10 | legit learn (quacq.py:249) | 10 |
| **0** | `_narrow_with_generator` (findc.py:135) | 0 |

## Answers to the three Stage-B questions
1. **Why does `_narrow` drop true 160?** — **It doesn't.** `_narrow_with_generator` pops = **0** across
   the run. The DiscriminatingGenerator is sound here: for semantically-identical `c_i,c_j` the SAT
   `BG + C_L[Y] + c_i + ¬c_j` is UNSAT → `generate` returns None → no pop (`discriminating_generator.py`
   `:57-69`). **160 (`(-1,2)`) was pruned by `prune_rejecting` (sat_utils.py:41).** My Stage-1
   inference ("160 removed by discrimination") was wrong — corrected here.
2. **Duplicate-awareness / fatal duplicate pops?** — **0 fatal.** Of 9 duplicate groups (all C_T-true),
   **none** had all encodings popped. Several LOST true clauses keep duplicate encodings **still in the
   bias, un-popped** — e.g. clause `(-2,1)`: aids **118 & 162 both remain**; `(-5,1)`: `126,180` remain.
   They are unlearned not because they were popped but because the run hit `no_query` convergence
   without ever querying them. **Duplicates are not the mechanism.**
3. **Cheapest correct break-point?** — None of the menu (i–iv) cleanly fixes the dominant loss (see
   below). (iv) is moot (0 `_narrow` pops); (i) duplicate-guarded pop is moot (0 fatal dups); (ii)
   "learn scope-derived on ⊥" **cannot recover** the loss — at ⊥ time `nrej=0` because the rejecting
   constraint was *already* popped upstream, so there is nothing to learn; (iii) attractor-skip only
   masks the spin, not the loss. The fix must be **upstream** (don't lose the constraint), which lands
   in `prune_rejecting` (shared + FindScope-adjacent, which CW Impl restricted) and/or the band-aid.

## The three ACTUAL loss mechanisms (none = the hypothesis)
1. **Band-aid collateral (quacq.py:263):** 14 true-by-clause dropped. Confirmed from the fairness pass.
2. **`prune_rejecting` (sat_utils.py:41):** dominant (241 pops); **5 true-by-clause pruned** (incl. 160,
   124, 140, 148). Called on positive full queries (quacq.py:218) AND positive **partial** queries
   (findscope.py:69). Caller attribution was blocked by the `@count_calls` decorator frame — not
   cleanly resolved. Some of these prunes are **legitimate** (see caveat); some may be a partial-query
   semantic-gap loss.
3. **Un-queryable at convergence:** true-clause encodings remain in the bias, never popped, never
   learned — `generate_from_sat` returned None (`no_query`) while they were still present. Likely
   redundant-given-KB (correct) or a query-generation gap.

## Critical caveat — "true-by-clause" OVERCOUNTS
The heuristic flags a bias constraint as "true" if ANY of its clauses ∈ C_T. But a constraint can hold
a C_T clause yet be **over-strong as a whole** → legitimately pruned. Example from the data: aid **116 =
`(-2,1) ∧ (-1,2)` = biconditional `interface↔jplug`**, almost certainly stronger than C_T's one-way
`interface→jplug` → its prune is CORRECT, not a loss. So the "5 prune / 14 band-aid true" counts are
**upper bounds** on real recall loss. The rigorous figure is the entailment-based **sem_recall = 0.50**
(precision 1.00), with **~7 clauses net-recoverable** (fairness red-team) — i.e. real, but bounded.

## GATE-B decision → STOP
- Stage-B's fix target (`_narrow`/duplicates) is refuted; implementing it fixes nothing.
- The dominant lever (`prune_rejecting`) is shared with the main loop and FindScope-adjacent — **outside
  the QuAcq-local box CW Impl drew**, and its correctness turns on partial-query pruning semantics.
- Whether ANY recall is recoverable by code (vs. the bias ceiling) is **unknown until** the prune/drop
  losses are entailment-classified (over-strong vs genuinely-target). This flips the decision between
  "fix" and "caveat" — so fixing now would be premature.

## Recommendation for CW Impl (next step, still read-only)
1. **Entailment-classify** the 5 prune + 14 band-aid true-by-clause losses: for each, is it C_T-entailed
   (genuine recall loss) or over-strong (legit removal)? Cheap, decisive. Bounds recoverable recall.
2. **If genuine losses dominate** → the fix is in `prune_rejecting`'s **partial-query** pruning
   (findscope.py:69 path) — CW Impl must decide whether to lift the "don't touch FindScope/prune"
   restriction, since that is where the recoverable recall actually leaks.
3. **If over-strong/legit dominate** → recall 0.50 is near the bias ceiling → **Option C (ship with the
   fairness caveat)** is the honest call; no code fix recovers meaningful recall.
4. The empty-scope companion (quacq.py:266-269) stays untouched (0× fired) — latent precision risk,
   settle before any sweep-wide precision claim.

## Guardrails status
Read-only; probes reverted (empty diff vs HEAD); no behavior change; no commit. A/C/C∪S/ConMin
untouched. Bias untouched. `.git/index.lock` still present (Viet-Man to clear) — did not block this
read-only work.

## Unresolved questions
1. Are the prune + band-aid true-by-clause losses genuinely C_T-target (recoverable) or over-strong
   (legit)? **Pivotal** — decides fix-vs-caveat. Needs the entailment pass (step 1 above).
2. Do the recoverable losses come from `prune_rejecting`'s **partial** path (findscope.py:69)? If yes,
   the fix is FindScope-adjacent — does CW Impl lift the restriction?
3. `_narrow_with_generator` is sound on duplicates here (0 wrong pops) — is that KB-general or REAL-FM-7-
   specific? (mechanism is general: `c_i≡c_j ⇒ UNSAT ⇒ None`.)
4. |B|=295 counts duplicated entries (9 dup groups / 18 aids on REAL-FM-7); effective version space <
   |B|. Reporting note for RUN.md/paper — not a bug.
