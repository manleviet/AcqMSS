# STAGE-1 diagnosis — "FindScope multi-violation" (#2): GATE = STOP, premise refuted

Read-only instrumentation (env-gated probes in quacq.py + findc.py, **reverted** — `git diff` vs HEAD
empty, 0 residue). REAL-FM-7, glucose4, oracle max_q=5000. test_quacq 50p. **No fix written.**

## TL;DR (decision-relevant)
**The hypothesis "FindScope mislocalizes multi-violation queries" is FALSE.** Measured: FindScope
returns a **valid single-constraint scope in 23/23** band-aid drops (0 hybrids, 0 partials, 0 foreign).
The real failure is a **band-aid-induced death spiral** downstream of FindScope. So a FindScope rewrite
would fix nothing. **Do NOT authorize the FindScope fix as scoped — the target is wrong. STOP.**

## What actually happens (measured, drop#0, identical for 22/23)
- The generated query `e` violates C_T clause `(-1,2)` = **`interface → jplug`**. Zero root/BG clauses
  violated (not a background leak).
- That clause is encoded by **two duplicate bias constraints, aids 116 & 160**. Both are **already
  popped** from `remaining_bias`, **unlearned**:
  - **116 popped by the band-aid** (`quacq.py:263`) — it appears as a dropped `tested_c_id`.
  - **160 popped by FindC's `_narrow_with_generator`** (`findc.py:135` `remaining_bias.pop(c_j)`) — it
    is *not* in the drop list, so discrimination removed it.
- FindScope (FM oracle) correctly re-localizes scope `(interface, jplug)` every time it recurs → an
  **attractor** (21/23 drops are this scope).
- FindC gets the surviving candidates `[118,162,164]` (other relations), **none reject `e`** →
  `nrej=0` (22/23) → ⊥ → band-aid drops the current *unrelated* `tested_c_id` (another true
  constraint) as collateral → **cascade of 22 more true-constraint drops.**

FindC ⊥ breakdown: **22/23 = `no_rejecting` (nrej=0)**, 1/23 = `no_candidates`. In every case a true
C_T constraint provably existed at the scope but had been removed.

## Answers to the three STAGE-1 questions
1. **Where does our recursion deviate from the paper?** — **Nowhere material.** `findscope.py`
   faithfully implements IJCAI-2013 Alg 2: the split (`:79-81`), R/Y bookkeeping, the `ask_query`
   guard, the S1/S2 recursion (`:84-85`, `R∪Y1,Y2,true` / `R∪S1,Y1,S1≠∅`), and the `return []`-on-
   inconsistent branch (`:72-73`) all match. Verified by output: returned scopes are real
   single-constraint scopes, and `e` genuinely violates a target constraint at each. The
   `prune_rejecting` side-effect (`:69`) is **not** implicated — the drops fail in FindC's rejection
   filter, not in FindScope pruning.
2. **Small/local correction or structural?** — The FindScope change is a **non-issue (nothing to fix
   there).** The real defect is a **correctness/design problem in QuAcq oracle-mode's failure loop**
   spanning THREE components: (a) `generate_from_sat` keeps re-proposing queries that violate a
   constraint that was removed-but-not-learned; (b) `_narrow_with_generator` removed a true duplicate
   encoding (160); (c) the band-aid pops true constraints (116) as collateral and has no way to learn
   the confirmed-violated scope. **This is structural, NOT small/local.** Estimate: a design decision +
   multi-file change (query-gen ∪ FindC discrimination ∪ band-aid) + re-baseline. Not a few lines.
3. **Interaction with `prune_rejecting` (RT-1)?** — None observed on the drops. The prune runs inside
   FindScope on *positive* partial queries; the death spiral is entirely in FindC's negative-side
   rejection filter + the two pop sites. `prune_rejecting` can stay as-is for this fix.

## Two real, distinct defects (both feed the spiral)
1. **HIGH — duplicate encodings + discrimination removes a TRUE constraint.** Bias has ≥2 aids for the
   same clause (116, 160 = `(-1,2)`). `_narrow_with_generator` (`findc.py:117-144`) popped the true
   160 while keeping false candidates. A discrimination/`is_valid` fault that removes a true constraint
   is a soundness-of-search bug, independent of the band-aid.
2. **HIGH — band-aid pops true constraints as collateral, unrecoverable.** `quacq.py:262-263` drops
   `tested_c_id` on any ⊥, including when the ⊥ is caused by an *already-removed* constraint at a
   *different* scope. Once a true constraint leaves the bias unlearned, `generate_from_sat` loops on it
   forever → the attractor.

## Companion item (red-team MED) — still stands
`quacq.py:266-269` empty-scope branch appends `tested_c_id` **unverified**. Fired **0× on REAL-FM-7**
(empty scope never occurred here), so untested. Still a latent precision-inflation path; settle before
any sweep-wide precision claim. Not implicated in today's drops.

## GATE recommendation → STOP; re-scope before any code
The `#2` task as written ("fix FindScope multi-violation localization") would touch the wrong file. CW
Impl should decide the re-scoped target (deadline 2026-07-28):
- **Option A — fix the search loop (structural).** Decide oracle-mode behavior when FindC ⊥ at an
  oracle-confirmed-violated scope: e.g. learn the scope-derived constraint instead of dropping an
  unrelated candidate; and/or make `generate_from_sat` exclude a confirmed-violated-but-unlearnable
  scope so it stops looping. Fixes the spiral at the root. Most work; re-baselines all QuAcq numbers.
- **Option B — investigate the duplicate-encoding discrimination bug first (narrower).** Why does
  `_narrow_with_generator` drop a true duplicate (160)? That may be a more local FindC fix and could
  break the spiral on its own. Recommend a short read-only diagnosis of `_narrow_with_generator` +
  `DiscriminatingGenerator` before committing to Option A.
- **Option C — report QuAcq-active with the caveat (from the fairness gate)** and defer the fix.

Recommendation: **B then A.** Do the narrow FindC/discrimination diagnosis first (cheap, may localize
the fix), then decide the structural loop change. **Do not touch FindScope.**

## Guardrails status
Read-only; probes reverted (empty diff vs HEAD); no behavior change; no commit (Stage 1). A/C/C∪S/ConMin
untouched (FindScope/FindC are QuAcq-only — will still need byte-identity proof if/when Stage 2 lands).

## Unresolved questions
1. **Blocker (ops):** a stale `.git/index.lock` is present (a crashed/parallel git process); I cannot
   remove it (hook-protected). Clear it before any commit: type `! rm -f .git/index.lock` in the prompt.
2. Which re-scoped option (A/B/C)? Recommend B→A. The prompt's FindScope target is refuted.
3. Where do the duplicate encodings (116 & 160 for one clause) come from — bias generation, or expected
   redundancy? If the bias is de-duplicated, does the spiral shrink? (Cheap to test.)
4. ConGen impact: ConGen shares this QuAcq path, so its baseline is distorted by the SAME spiral, not by
   FindScope. The SoSyM heads-up should name the FindC/band-aid loop, not FindScope.
5. Is the attractor KB-specific (REAL-FM-7's `interface-jplug` duplicate) or general? Unverified on
   other KBs (measured REAL-FM-7 only).
