# Red-team: QuAcq-active fairness measurement (REAL-FM-7) — REFUTE attempt

Adversarial reproduction of `from-code-reviewer-to-cw-impl-260726-quacq-active-fairness-measurement.md`.
Independent re-run (glucose4, oracle max_q=5000) + independent semantic attribution. Verdict: the
measurement and its **branch-2** verdict **SURVIVE**. All 6 claims CONFIRMED; two caveats (reproducibility
gap; a latent cross-KB inflation path) that do NOT touch the REAL-FM-7 numbers.

Method: re-added the env-gated `_FAIRNESS_PROBE` hook to quacq.py (append-only, control-flow-inert),
one instrumented oracle run + one example-only run, then reverted (source now == HEAD, `git diff --quiet`
clean, no residue). Suite: **591 passed, 1 skipped** (108s). Solver pinned glucose4.

## C1 — Headline numbers: **CONFIRMED (exact)**
Reproduced to 4 dp:

| | reason | q | \|KB\| | sem P/R/F1 | desc P/R/F1 | clause P/R/F1 |
|---|---|---|---|---|---|---|
| QuAcq-active | no_query | 342 | 10 | 1.0/0.5/0.6667 | 0.30/0.2308/0.2609 | 1.0/0.5/0.6667 |
| example-only rs_1n | pool_exhausted | 23 | 1 | 1.0/0.0455/0.087 | 1.0/0.0769/0.1429 | — |

- accuracy=1.0 (tp/tn/fp/fn = 13/1/0/0). |C_T|=22 (set==list, no dup → recall denom unambiguous), |bias|=295.
- **score_named_kb used correctly**: verified in source — vocab-space P/R/F1 build `ConGenResultData(bg_clauses=[])`,
  so root is excluded from sem/clause/desc and only enters the delivered theory (exact-equiv+accuracy). No inflation.
- **Precision 1.0 is genuinely sound**: `unentailed_kb=0` → every one of the 11 KB clauses is entailed by C_T
  **alone** (the precision direction excludes BG), i.e. stricter than FM-entailment. Soundness holds a fortiori.
- Material gain real: active 0.667 vs example-only 0.087 = **7.66×**. Mechanistic cause visible: rs_1n has only
  **1 negative example** (|pos|=13,|neg|=1) → passive is neg-starved; active self-generates 342 queries.

## C2 — Probe non-perturbation: **CONFIRMED** (+ reproducibility caveat)
- Instrumentation is pure append gated on a module global; cannot alter `remaining_bias`/`learned_kb`/control flow.
  Instrumented run returned the identical clean headline (342 q, |KB|=10).
- Committed quacq.py has **zero** probe residue: pre-edit `hasattr(quacq,'_FAIRNESS_PROBE')=False` + grep empty;
  post-revert `git diff --quiet` clean, source grep clean.
- **CAVEAT (repro gap, LOW-MED):** the shipped `fairness_probe.py` references `quacq_mod._FAIRNESS_PROBE`, but
  **nothing in committed quacq.py reads it** — the drop-collection hook was reverted. So the C3 drop numbers are
  **not push-button reproducible** from committed artifacts; they require re-adding the revertible hook (as I did).
  The numbers are correct, but the repo alone won't regenerate them.

## C3 — Band-aid split (23=14 true+9 unlearnable, 7 net-missing): **CONFIRMED (exact)**
`total=23, TRUE(∈C_T)=14, unlearnable=9, empty_scope_adds=0, distinct-true=14, net-missing(clause)=7`.
- **(a) determinism cross-check = True**: re-prepared `describe` re-resolved the final KB (10 aids → 11 clauses)
  to a set identical to the runner's `kb_clauses` (11). `prepare_task` is pure/deterministic → aid→clause labels
  are aligned; no silent mislabel. (Proxy note: validates the final-KB subset; dropped aids share the same uniform
  mapping, so they inherit the alignment.)
- **(b) spot-checks hold**: true drops verified ∈ C_T — c1`[-1,2]&[-2,1]`, c9`[-7,5]`, c11`[-8,1]`, c15`[-9,10,11]`.
  "Unlearnable" drops verified ∉ C_T for **every** clause — c49`[-10,-1]`, c50`[-1,11]`, c69`[-5,2]`, c75`[-7,2]`,
  c78`[-8,2]`, c87`[-11,2]` (all any∈C_T=False). So "unlearnable" == correctly-excluded non-target bias constraint.
- **(c) net-missing is a valid loss floor**: independent SAT check — all 7 net-missing dropped-true clauses are also
  in `missed_sem` (KB-only unentailed C_T) → they are genuine KB-only recall losses, not re-entailed by the KB.

## C4 — "recall 0.50 is majority the band-aid": **CONFIRMED (and stronger than claimed)**
Decomposition of the 11 KB-only-missed C_T clauses (independent semantic reconstruction):
- **7/11 (64%)** are band-aid dropped-true (`dropped_true ∩ missed_sem = 7`). → majority, as claimed.
- The other **4** (`[-12,1],[-9,1],[-5,1],[1]`) are **root-implied**: entailed once the root unit `[1]` is asserted;
  they are absent only because the vocab contract sets bg=[] — NOT a band-aid effect and NOT unlearnable structure.
- Under real FM semantics (KB∪BG): only **5** clauses genuinely missed, and **5/5 (100%)** are band-aid dropped-true
  (`[-9,10,11],[-4,2],[-3,2],[-2,3,4],[-1,2]`). Recall WITH BG = 0.7727.
- The 9 unlearnable drops cost **0** recall. Of the 11 missed, only 2 are n-ary (`[-9,10,11],[-2,3,4]`) and **both are
  band-aid dropped-true** bias constraints (c15/c16, c3/c4) → bias-representable/recoverable, not an independent
  "n-ary never-in-bias" cause. FindC-other-failure ≡ the band-aid path itself. Attribution to the band-aid holds.

## C5 — Counterfactual "~0.8 with FindScope fix": **CONFIRMED as defensible upper bound** (not a prediction)
- Exact KB-only recall **ceiling** if all 7 net-missing dropped-true are recovered: (11+7)/22 = **18/22 = 0.818**.
  The 4 remaining are root-implied → forever missed by the KB-only (bg=[]) measure. So 0.82 is a hard ceiling; "~0.8"
  is grounded, not hand-wavy. sem-F1 ceiling at P=1.0,R=0.818 → **0.90**; report's "~0.85" is conservative vs that.
- Still a **ceiling, not an outcome**: assumes the (non-existent) FindScope fix recovers all 7 with zero precision
  loss. Report hedges ("could plausibly rise toward") → acceptable. Recommend wording it explicitly as an UPPER BOUND.

## C6 — Fairness framing/direction: **CONFIRMED**
- Reproduced: QuAcq-active sem-F1 **0.667 > A 0.566** on REAL-FM-7 — already ties/beats ConMin-A despite the cap.
- Band-aid can **only depress** QuAcq: it pops candidates from `remaining_bias`, never adds to `learned_kb`. Precision
  stays 1.0 (`unentailed_kb=0`). ⇒ reporting as-is **understates** QuAcq, so "ConMin ≫ QuAcq-active" would be unfair to
  QuAcq — direction correct.
- **LATENT inflation path (not on this KB):** the empty-scope branch (quacq.py 266-269) appends `tested_c_id` to the KB
  **without FindC verification**. If it fired with `tested_c_id ∉ C_T` it would inject a false constraint → precision<1.
  Fired **0×** on REAL-FM-7 (`empty_scope_adds=0`), so no effect here; magnitude unverified on other KBs.

## Severity-ranked
1. **HIGH (eval fidelity, known):** band-aid drops ≥5–7 true bias-representable clauses → depresses QuAcq recall ~0.27–0.32
   on this KB. Deliberate, in-code-documented liveness tradeoff, not a hidden bug — but it materially biases the reported
   active baseline downward. Drives the branch-2 verdict. → fix FindScope (option 1) or report as an explicit lower bound.
2. **MEDIUM (latent):** empty-scope unverified KB append (quacq.py 266-269) is a precision-inflation risk on KBs where it
   fires (0× here). Worth measuring before the sweep, since it undercuts the "precision always sound" claim off REAL-FM-7.
3. **MEDIUM (comms):** headline ambiguity — sem 0.667 vs desc 0.261 is a 2.5× spread; desc P=0.30 because 7/10 learned
   constraints are FM-equivalent to targets under different bias names (sem sees them, desc doesn't). Pick + justify one.
4. **LOW-MED (repro):** C3 numbers need the reverted hook to regenerate; not reproducible from committed repo alone.

## Bottom line
Nothing refuted. Every headline number reproduced exactly; the band-aid true/unlearnable split, the 7-clause net loss,
and the "majority-artifact" attribution are all independently confirmed — and under FM semantics the band-aid accounts
for 100% (5/5) of the genuine recall loss, strengthening the report. Branch-2 GATE (band-aid drops TRUE constraints)
stands. Recommendation 1-or-2 is sound.

## Unresolved questions
1. **Query-budget fairness (out of scope, flagged):** active spends 342 membership queries vs A's 14 examples. The band-aid
   axis is settled, but active-vs-passive on equal information budget is a separate, unaddressed fairness axis.
2. **Empty-scope append (quacq.py 266-269):** does it fire on fqa/arcade/REAL-FM-4/busybox, and with `tested_c_id ∉ C_T`?
   If yes, precision <1 there → the "sound" claim is REAL-FM-7-local. Cheap to add to the sweep instrumentation.
3. **KB-generality of the 14-true/0.5 pattern:** measured only on REAL-FM-7 (per speed discipline). Mechanism is KB-general;
   magnitude is not.
4. Headline choice sem(0.667) vs desc(0.261) — report's own open Q3; unresolved.

Status: DONE
Summary: Independent re-run reproduced every headline number exactly and the band-aid split (14 true / 9 unlearnable / 7
net-missing); the branch-2 "band-aid depresses QuAcq recall" verdict survives and is strengthened (5/5 genuine recall loss
is the band-aid under FM semantics). Tree reverted clean; suite 591p/1s green.
Concerns/Blockers: C3 not reproducible from the committed repo without re-adding the reverted hook; latent unverified
empty-scope KB-append (0× on REAL-FM-7) could inflate precision on other KBs — verify before the sweep.
