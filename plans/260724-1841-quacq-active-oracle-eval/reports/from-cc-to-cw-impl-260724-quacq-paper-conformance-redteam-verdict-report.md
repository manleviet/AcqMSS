# CC → CW Impl — QuAcq subsystem paper-conformance red-team + VERDICT

Audit vs Bessiere et al., "Constraint Acquisition via Partial Queries" (IJCAI 2013). Read-only +
instrumentation, **no source edits** (throwaway scratchpad scripts only); `PYTHONPATH=. pytest tests/ -q`
**green (576p/1s)**. 3 hostile reviewers (paper-conformance / FindScope-liveness / eval-construct-validity)
+ controller quantification. Findings independently re-derived — this **partially overturns** the earlier
KB=0 report's tentative mechanism (see §Correction).

## VERDICT (one line)
**The QuAcq baseline is CORRUPTED — NOT a faithful QuAcq in EITHER mode, NOT reportable as-is.** The
reported semantic F1 (0.01–0.07) is a mechanical artifact of FindC silently discarding **~74% of
negatives** (all "no bias candidate matches the FindScope scope"), caused by exists-completion
partial-query oracle semantics colliding with a binary-only bias; oracle mode additionally spins to
`max_queries` learning almost nothing, and example mode's cost metric is nondeterministic.

## Example-mode FindC drop-rate (the impact measure)
- Reviewer C, 12 folds: **48/65 = 73.85%** dropped (fqa/rs_3n 86%, arcade-game/rs_3n 75%,
  REAL-FM-7/2cov 43%, rs_3n 50%). **100% of drops = "no candidates with scope."**
- Controller, ff-fold across the 4 done KBs: REAL-FM-7 0% (learned 1), fqa 100% (0/2), arcade-game
  100% (0/1), REAL-FM-4 100% (0/4). Learned KB = 0 on 3 of 4.
- Result: delivered QuAcq theories are 0–2 constraints (occasionally up to 7, seed-dependent) → F1≈0
  is downstream of the discard, **not** a property of QuAcq.

## Root cause (converged across all 3 reviewers + controller probe)
1. **`FMOracle.is_valid` on a PARTIAL config = exists-completion / extension-SAT** — `is_consistent(FM
   constraints[all, incl. root-pinning] + assumptions for the assigned features only)`
   (`conacq/oracle/fm/oracle.py:102-105`). The paper's `ASK(e[R])` must answer *does e[R] violate a
   FULLY-ASSIGNED target constraint?* — a strictly weaker test. **Proven:** `is_valid({jplug:T, sdi:F,
   mdi:F}) = False` although no constraint fully inside `{jplug,sdi,mdi}` is violated (it's only
   unextendable via `jplug→interface→xor(sdi,mdi)`); paper semantics wants True.
2. → **FindScope systematically under-localizes** the scope to a SAT unsat-core (often a single
   mandatory/structural feature): straddling group constraints cause spurious "reject" (B), and
   root/forced variables are invariant so FindScope can't identify them (A).
3. **The bias is BINARY-ONLY** — arity dist REAL-FM-7 `{2:291,3:4}`, fqa `{2:387,…}`, arcade-game
   `{2:1737,…}`; **zero unary constraints** (C). So size-1 (and mismatched size-2) scopes match no bias
   constraint at all.
4. **FindC's `get_constraints_with_scope` requires `c_vars == scope` or `c_vars ⊆ scope`**
   (`quacq_model.py:74-76`) → the true candidate (whose scope ⊋ the under-localized scope, e.g.
   `{jplug,interface} ⊄ {interface}`) is excluded → **FindC = ⊥ (None)**.
5. **Liveness (oracle mode):** on FindC=⊥ the main loop (`quacq.py:246-252`) logs a warning but neither
   appends, pops, nor reports collapse → `generate_from_sat` deterministically re-proposes the same
   candidate → spin. Instrumented: c_id 288 proposed 18×, KB/bias frozen 17 iterations, `max_queries`.

## Consolidated findings (deduped; file:line · paper-step · severity · disposition)

| # | Finding | Location | Paper step | Sev | Disp |
|---|---------|----------|-----------|-----|------|
| RC-1 | Partial-query oracle = exists-completion, not "violates a fully-assigned constraint" — root of scope under-localization | oracle.py:102-105; findscope.py:64,72 | Alg 2 ASK(e_R) | **Crit** | Accept (proven) |
| RC-2 | FindC=⊥ makes zero progress → same query re-proposed → spin to max_queries, ~0 learned | quacq.py:246-252; query_provider.py:125-139 | Alg 1 L8-11 + monotone-progress | **Crit** | Accept |
| RC-3 | FindC `c_vars ⊆ scope` match excludes true candidate under under-localized scope → 0 candidates | quacq_model.py:74-76; findc.py:69-74 | Alg 3 L1 (scope equality) | **Crit** | Accept |
| RC-4 | ~74% of negatives discarded → passive F1 0.01–0.07 is a discard artifact, not faithful QuAcq | quacq.py:236-252; findc.py:69-74 | Alg 1 negative path | **Crit** | Accept (measured) |
| H-1 | "Collapse" (FindC=⊥ for a real scope) never detected/reported — masked as warning | quacq.py:251-252,260-262 | Alg 1 L10 | High | Accept |
| H-2 | example_only pool shuffled with seed=None → nondeterministic oracle_queries (committed data non-reproducible) | conmin_cv_evaluator.py:243; query_provider.py:60 | reproducibility | High | Accept |
| H-3 | "passive reference" mislabeled — discards pool labels, queries the LIVE FM oracle via FindScope/FindC | quacq_runner.py:284,305; quacq.py:211 | construct validity | High | Accept |
| H-4 | Root-pinned-in-BG vs candidate scope: `{jplug,interface}` candidates unmatchable to `{interface}` scope | task_preparation.py:126; quacq_model.py:59-78 | Alg 3 (mechanism) | High | Accept (facet of RC-1/3) |
| M-1 | Empty-scope oracle fallback appends `tested_c_id` unconditionally (latent unsound; oracle-mode only) | quacq.py:253-258 | none (no analog) | Med | Accept (latent) |
| M-2 | FindC two-sided narrowing incomplete — `is_valid=False` branch does no candidate pruning | findc.py:132-138 | Alg 3 L6-8 (line# uncertain) | Med | Accept (latent, masked) |
| M-3 | Phantom tests assert only type/bounds, never `KB>0` — the 0-KB failure ships green | test_quacq.py:235-238,299-302 | test quality | Med | Accept |
| M-4 | Delivered-theory accuracy/specificity asymmetry — QuAcq fallback=() vs ConMin ¬e⁻ (F1 columns UNAFFECTED) | conmin_cv_evaluator.py:256,293; conmin_slice_scorer.py:66-77 | eval parity | Med | Accept (accuracy cols only) |
| L-1 | Oracle queried past max_queries but uncounted (+1 divergence, bounded) | quacq.py:156-160; findscope.py:64 | query accounting | Low | Accept (minor) |

## Verified CORRECT (attacks refuted — recorded so they aren't re-litigated)
- **Positive-answer κ_B(e) narrowing is correct** (A-F5): `prune_rejecting` removes ALL constraints
  violated by a positive e, in BOTH modes (`quacq.py:217-218`, `sat_utils.py:36-42`). The "missing
  version-space narrowing" concern is **refuted** — narrowing is present and sound.
- **FindScope internals sound:** the `S2 = run(..., ask_query=len(S1)>0)` short-circuit is faithful to
  IJCAI'13; recursion terminates (strict subset each call); no remaining_bias mutation-during-iteration
  hazard (B refutes its own attacks 1/4/5).
- **Semantic-F1 scoring parity is clean** (C-F6/F5): learned KB resolves to real bias names via the same
  `KBComparator`/`ground_truth`/`root_clauses` as A/C/C∪S; sem/desc/clause F1 use `names` only with
  `bg_clauses=[]` and exclude fallbacks. F1≈0 is a genuine near-empty KB, **not** a scoring artifact.

## Bug vs design-limitation (the adjudication that matters for the paper)
- **Unambiguous BUGS** (fix independent of research intent): RC-2 liveness spin; H-2 seed=None
  nondeterminism; M-3 phantom tests.
- **Semantics/design defect** (RC-1 + RC-3 + H-4 + binary bias): whether "FM n-ary/mandatory constraints
  are un-acquirable by a binary-bias QuAcq with exists-completion partials" is a *bug* or an *expected
  limitation* is a **research-owner decision**. But the EFFECT is identical: QuAcq learns almost nothing,
  so the numbers are not a faithful QuAcq baseline **regardless of the label**.
- **Construct validity** (H-3): the condition called "passive reference" is actually pool-seeded ACTIVE
  learning against the live FM oracle — a naming/narrative problem for the paper even if learning worked.

## Correction to the earlier KB=0 report (intellectual honesty)
The prior `oracle-kb0-rootcause-report` proposed "e violates NON-bias constraints (weak BG)" as a
candidate cause. Reviewer A **overturns** that: `generate_from_sat` correctly returns e ∈ sol(C_L∪root)
violating a REAL bias constraint (116 = `{jplug,interface}`); the defect is the SCOPE-VARIABLE mismatch
(FindScope drops the pinned root; the bias keeps it), driven by RC-1. The earlier "FindScope
under-approximation" label is correct but its cause is the partial-oracle semantics (RC-1), not
FindScope's recursion logic (which is faithful).

## Recommendation (NO fix applied — CW Impl + CW Main decide)
1. **Do not report ANY current QuAcq number** (passive or active) as a QuAcq baseline. If a QuAcq column
   is required, it must be regenerated after RC-1 is resolved, or dropped/documented as a known
   limitation of binary-bias QuAcq on feature models.
2. Cheapest correctness rails if a fix is pursued: (a) RC-2 liveness — on FindC=⊥, retire/quarantine the
   candidate so the loop progresses + emit `collapse`; (b) H-2 — thread a fixed `shuffle_seed=fold_idx`.
   Neither makes QuAcq *learn* — that needs RC-1 (a paper-faithful partial-membership oracle, or
   restricting FindScope to bias-representable scopes).
3. Re-label the "passive reference" condition (H-3) regardless.

## Unresolved questions
1. **Is the target a binary constraint network?** If yes, FM mandatory/group (n-ary, root-adjacent)
   constraints are inherently un-acquirable by this bias — makes RC-1/H-4 an "expected limitation" to
   document, not a bug to fix. If the bias should be widened, RC-1 is a bug. (Research-owner call.)
2. **Does the paper even need a QuAcq baseline in *both* modes?** Example-mode is the ConGen-comparable
   one; if oracle/active is dropped (already NO-GO), only RC-1/RC-4/H-2/H-3 gate the example-mode number.
3. **Oracle-mode determinism:** reviewer A observed `n_kb=7` (seed 42) vs controller `n_kb=0` — an
   unexplained oracle-mode variation that also questions the earlier QuAcq-active "deterministic /
   fold-independent" assumption. Worth a dedicated check before any oracle-mode number is trusted.
4. Exact IJCAI'13 Algorithm 3 line numbers for two-sided FindC narrowing (M-2) — flagged uncertain by
   the reviewer; verify against the PDF before quoting in a fix.

_(No repo changes from this audit; scratchpad probe scripts are throwaway. The earlier red-team fixes on
`feat/conmin` remain uncommitted and are unrelated.)_
