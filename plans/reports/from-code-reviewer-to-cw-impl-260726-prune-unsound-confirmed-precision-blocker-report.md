# QuAcq losses — Task 1/2/3: hypothesis CONFIRMED, clean fix recovers recall but hits a precision blocker

Read-only diagnosis + one implement/measure/revert cycle. All probes reverted; **tree clean** (git diff
vs HEAD empty), test_quacq 50p. pysat entailment; recall sanity = 0.500 == reported (method validated).
No fix committed (precision guardrail tripped). REAL-FM-7, glucose4, oracle max_q=5000.

## TL;DR
- **TASK 2 hypothesis HELD (measured):** `prune_rejecting` is **sound on complete** assignments
  (quacq:218 → 0 genuine-target prunes) and **UNSOUND on partial** assignments (findscope:69 → **10**
  genuine-target prunes). Exactly the extension-SAT defect class of the `is_valid` fix (cb28412), at
  the second call site that fix never reached — RT-1's flagged, never-run concern, now confirmed.
- **The clean paper-faithful fix works for recall:** removing the findscope:69 prune lifts sem-recall
  **0.50 → 0.773** (sem-F1 0.667 → **0.829**, desc-F1 0.261 → **0.636**), and halves queries (342 → 128,
  the spiral is gone).
- **BUT precision regresses 1.00 → 0.895** — the fix unmasks a *pre-existing* FindC precision bug
  (learns 2 over-strong clauses). Mandatory precision guardrail tripped → **not shippable as-is; reverted.**

## TASK 1 — entailment G/S/R classification (metric-aligned: C_T-alone entailment, BG excluded)
Sanity: pysat recall(KB⊨C_T) = 11/22 = **0.500** == fairness sem_recall (validates the classifier).
G = genuine-target (C_T-entailed, KB doesn't → recoverable). S = over-strong (C_T⊭c → removal correct).
R = redundant (already covered).

| pop-site | G | S | R | note |
|---|---|---|---|---|
| **prune-partial** (findscope:69) | **10** | 158 | 0 | unsound: 10 genuine losses |
| **prune-complete** (quacq:232) | **0** | 73 | 0 | sound |
| band-aid (quacq:277) | 13 | 6 | 4 | collateral drops |
| un-queryable (never popped) | 18 | 0 | 8 | still in bias at `no_query` |
| learn (quacq:263) | 0 | 0 | 10 | the 10 learned (correct) |

**Corrected recall ceiling** (recover all G) = **0.955 (21/22)**, not the fairness red-team's 0.818 —
that number **understated** it. The prior "band-aid drops 14 true" caveat **overcounted**: of the 23
band-aid drops only **13 are genuine** (6 over-strong, 4 redundant). Use the corrected figures in any
caveat.

## TASK 2 — hypothesis test: partial-prune unsoundness
`prune-partial G=10, prune-complete G=0`. **HYPOTHESIS HELD.** A sound prune never removes a
genuine-target constraint; the partial path removes 10, the complete path removes 0. The partial call
receives `e[R]` and `checker.is_consistent(root + partial + c)` is **extension-SAT** — it condemns
FM-entailed candidates whose scope `e[R]` does not fully assign, which the paper's "only a
fully-assigned clause can condemn" rule forbids. **Blast radius / effort:** the prune call at
findscope:69 is QuAcq-local (ConMin never touches it — verified). Option (ii) = delete the call = ~4
lines. Option (i) = fully-assigned guard = ~10-15 lines + a scope lookup into `prune_rejecting`.

## TASK 3 — implemented option (ii), measured, REVERTED
**Fix (option ii):** removed the non-paper prune at findscope:69 (paper's FindScope is pure scope
search, never narrows the bias); dropped now-dead FindScope params (checker/assignment_map/
root_assumption); rewrote the stale band-aid comment (no longer blames FindScope); added the empty-scope
**verified-append** companion. QuAcq-local, 2 files, <50 lines.

| REAL-FM-7 oracle | before | after (option ii) |
|---|---|---|
| sem P / R / F1 | 1.000 / 0.500 / 0.667 | **0.895** / **0.773** / **0.829** |
| desc P / R / F1 | 0.300 / 0.231 / 0.261 | 0.778 / 0.538 / 0.636 |
| \|KB\|, queries, reason | 10, 342, no_query | 9, **128**, no_query |
| example-only (guard) | 1.00/0.045/0.087 | **unchanged** ✓ |

**Precision regression root — NOT the fix's target, a masked FindC bug:** the 2 over-strong learned
clauses are `(-5,7)` and `(-12,14)`. Empty-scope companion fired **0×** (innocent). They are learned by
**FindC's "return first unconfirmed candidate" fallback** (`findc.py:106`, and `_narrow` returning
`candidates[0]` with >1 left): when discrimination cannot narrow to a single candidate, FindC **guesses**
— and can guess an over-strong one. The unsound prune had been *coincidentally* culling those candidates
before FindC saw them, so precision looked like 1.00. This is exactly the guardrail's warning ("precision
is 1.00 partly because the spiral discards aggressively").

## Where this leaves us (time-box)
The prune IS unsound and removing it IS correct + recovers large recall — but it cannot ship alone
because it exposes a latent FindC precision bug. Two paths (CW Impl decides — I did not open a 4th line):

1. **Option (i)** — the fully-assigned-clause prune rule — is the one remaining authorized fix that
   *might* give recall↑ AND precision=1.00: it keeps the SOUND over-strong culls (which protect
   precision) while dropping only the 10 unsound partial prunes. **Untested** — its precision outcome
   depends on whether the `(-5,7)`/`(-12,14)` culls were fully-assigned prunes (kept) or extension-based
   (dropped). One implement+measure cycle would settle it.
2. **Option C (time-box default)** — ship QuAcq-active with the **corrected** caveat: sem-recall 0.50 is
   depressed by an unsound partial-query prune (findscope:69); a paper-faithful fix reaches 0.773
   (ceiling 0.955) but is blocked by a separate FindC precision weakness; report recall as a lower
   bound, solver = glucose4. Do NOT repeat the overcounted "14 true" figure — the honest count is 13
   genuine band-aid + 10 genuine prune-partial losses.

## Guardrails status
Read-only outcome (fix reverted). Tree clean (empty diff vs HEAD). example-only proven unchanged.
A/C/C∪S/ConMin/bias untouched throughout (FindScope/FindC/prune are QuAcq-only). No commit.

## Unresolved questions
1. Does option (i) preserve precision? (depends on fully-assigned-vs-extension provenance of the
   over-strong culls — one measurement settles it.) **This is the pivotal open question if a fix is wanted.**
2. The FindC "return-first-unconfirmed" precision bug (`findc.py:106`) is **pre-existing and independent**
   — it affects ConGen's QuAcq path too. Fix separately, or accept guess-heuristic? (A soundness-first
   variant returns None when unconfirmed → precision 1.0, possibly lower recall.)
3. CW Impl decision: attempt option (i), or ship Option C with the corrected caveat?
4. ConGen impact: ConGen's example-first numbers would change if this ships (shared FindScope prune) —
   flagged, not regenerated.
