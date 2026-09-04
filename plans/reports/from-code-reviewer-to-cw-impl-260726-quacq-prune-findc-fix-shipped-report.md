# QuAcq FINAL fix — SHIP (i)+(iii): sound partial prune + conservative FindC

Decision rule **branch 2** fired → shipped (i)+(iii). All hard guardrails pass. Fix staged; commit
blocked only by a stale `.git/HEAD.lock` (Viet-Man's concurrent commit) — see Housekeeping.

## Variants measured (REAL-FM-7, glucose4, oracle max_q=5000) — baseline sem 1.00/0.50/**0.667**
| variant | sem P/R/F1 | desc P/R/F1 | \|KB\| | q | example-only |
|---|---|---|---|---|---|
| (i) alone (paper-faithful partial prune) | 0.850 / 0.773 / 0.810 | 0.667/0.462/0.545 | 9 | 136 | unchanged ✓ |
| **(i)+(iii) — SHIPPED** | **1.000 / 0.727 / 0.842** | 0.250/0.231/0.240 | 12 | 272 | unchanged ✓ |

**Decision-rule trace:** Rule 1 (i-alone) → F1 0.810 ≥ 0.80 ✓ but precision 0.850 < 0.98 ✗ → fail.
**Rule 2 (i+iii) → F1 0.842 ≥ 0.80 ✓ AND precision 1.000 ≥ 0.98 ✓ → SHIP.**

## The fix (QuAcq-local, 3 files + golden)
- **(i)** `sat_utils.prune_rejecting` gains `include_bg` (default True). FindScope (`findscope.py:69`,
  partial assignments) now calls `include_bg=False` → prunes a candidate only when the partial fully
  assigns and falsifies one of its clauses (paper Alg-2 rule). Extension-SAT with BG had wrongly
  condemned 10 FM-entailed candidates on REAL-FM-7. The complete-assignment caller (`quacq.py:218`)
  keeps `include_bg=True` and is byte-identical (a complete BG-consistent positive gives the same
  verdict either way). FindScope's Alg-2 recursion is untouched.
- **(iii)** `findc.py`: when discrimination cannot narrow to a single candidate, return **None**
  (both the post-loop `_narrow` return and the run() fallback) instead of guessing `candidates[0]`.
  The guess could learn an over-strong constraint → precision <1.0. (Fix (i) alone recovers recall
  but exposes this — precision 1.00 in the old code was *load-bearing on the unsound prune*.)

## Canonical REAL-FM-7 numbers (paper-citable, glucose4)
- **QuAcq-active (oracle):** sem P/R/F1 = **1.000 / 0.727 / 0.842**; desc = 0.250 / 0.231 / 0.240;
  clause = 1.000 / 0.727 / 0.842; |KB| = 12; queries = 272; convergence = no_query.
- **QuAcq example-only:** 1.000 / 0.045 / 0.087 (byte-identical to before — it never hits the changed
  partial-prune outcome on this KB; verified, not assumed).
- Note the sem-vs-desc gap: precision is 1.000 by entailment (every learned constraint is C_T-entailed
  = sound) but desc-precision 0.250 (only 3/12 match a *named* target; 9 are entailed equivalents).
  Report both; sem is the soundness metric, desc the named-acquisition metric.

## Guardrail proofs (all pass)
- **A/C/C∪S/ConMin byte-identical:** the 3 changed files (findscope/findc/sat_utils) are imported
  ONLY by the quacq package — never by ConMin/acqmss/eval (grep-proven). Byte-identical by construction.
- **Determinism:** cross-process, `12|272|no_query` + identical KB hash under PYTHONHASHSEED 0/1/7 AND
  unset. The 3654c2b property survives. In-suite determinism test passes.
- **Suite:** `591 passed, 1 skipped` (green).
- **example-only unchanged:** verified (KB=1, q=23, sem-F1 0.087).
- **Golden re-baseline (old→new):** T11 `layer23_prepared_and_e2e.json` — **only `layer3.quacq`
  changed** (`layer2` + `layer3.congen_rs/ff` byte-identical, diff-guarded). And within quacq only
  `query_history` moved: `n_kb 0→0, n_queries 15→15, reason max_queries→max_queries` (the golden runs a
  low budget where KB=0 regardless; it is a determinism tripwire). queries/trace fixtures unchanged.
- **bias files untouched; ConGen `data/results/interactive/` untouched.**

## ConGen impact (flag only — NOT regenerated, per instruction)
ConGen shares FindScope/FindC/prune. On the committed golden fixtures its learned KB is **byte-identical**
(`layer3.congen_rs`/`congen_ff` unchanged after the fix) — evidence ConGen's REAL-FM-7 example numbers
do NOT move. A full ConGen regen across all KBs/modes was NOT run. **Heads-up for the SoSyM revision:**
ConGen's example-first path *could* shift on other KBs (both defects touched shared code); regenerate +
diff there before citing ConGen QuAcq-baseline numbers.

## Unresolved questions
1. Commit SHA pending — a stale `.git/HEAD.lock` (from a concurrent CW-Impl commit) blocks the write;
   the fix is staged. Clear with `! rm -f .git/HEAD.lock`, then the staged commit lands.
2. Empty-scope unverified append (`quacq.py:266-269`) is still latent (fired 0× here) — not in this
   cycle's scope; a separate small safety fix before a sweep-wide precision claim.
3. desc-precision 0.250: 9/12 learned are entailed-but-differently-named. Acceptable for a soundness
   (sem) claim; flag if the paper leads with the description metric.
4. ConGen full-regen decision (SoSyM) — when to run it.
