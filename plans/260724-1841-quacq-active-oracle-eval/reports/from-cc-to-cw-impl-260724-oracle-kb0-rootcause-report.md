# CC → CW Impl — Root cause: oracle-mode QuAcq learns KB=0 (REAL-FM-7)

Read-only diagnosis (no source edits; suite green). Instrumented one oracle-mode
`learn(max_queries=200)` on REAL-FM-7 via runtime monkeypatch + the loop's existing DEBUG logs.
**No fix applied — reporting the breaking stage for CW Impl/CW Main to decide.**

## Verdict: hypothesis REFUTED. The break is NOT the generator — it is the FindScope→FindC handoff, amplified by a learn-loop liveness bug.

The hypothesis was "generator makes oracle-VALID configs → never rejected → never learns." The
data shows the **opposite**: every query is rejected, learning is attempted every time, and it
fails downstream.

## Instrumented run (max_queries=200)
```
reason=max_queries  n_queries=200  n_kb=0
MAIN-LOOP ANSWERS:   valid=0   invalid=34          # every query REJECTED (not valid)
VALID PATH (prune):  prune_calls=0                 # never taken (0 valid answers)
INVALID PATH:        added=0  findc_none=34  empty_scope=0
FINDC None-path:     no_candidates_with_scope=34   # FindC returns None because 0 candidates
tested c_id:         116, 116, 116 … (34/34, distinct=1)   # STUCK on one constraint
scope handed to FindC: ['interface'] → candidates=0        # every iteration
constraint 116 vars = {interface, jplug}
```

## The failure chain (each step evidenced)
1. **Generator OK (discriminating, deterministic).** `generate_from_sat` (query_provider.py:125-139)
   returns a config satisfying `KB∪BG` but violating candidate **116** (`{interface, jplug}`). No
   RNG — it enumerates `remaining_bias` in insertion order and returns the first SAT candidate →
   **deterministic**, no seed involved (Q4: oracle mode is reproducible *without* a seed).
2. **Oracle OK (rejects every query).** All 34 main-loop queries → `invalid`. So the loop enters
   the learning branch every iteration. (FMOracle partial-config semantics verified CORRECT —
   `is_valid({})`=True, `is_valid({interface:True})`=True = "exists a valid completion", exactly
   what FindScope needs. **Not** the cause.)
3. **FindScope UNDER-APPROXIMATES the scope.** For the 116-violating example it returns
   **`{interface}`** — missing `jplug` — every iteration (findscope.py:40-87, binary search over
   `oracle.is_valid` on partial configs).
4. **FindC finds no candidate → None (34/34).** `get_constraints_with_scope` (quacq_model.py:59)
   matches a bias constraint only if `c_vars == scope` or `c_vars ⊆ scope`. `{interface, jplug} ⊄
   {interface}` → **0 candidates** → FindC returns None at findc.py:73 (`no_candidates_with_scope`),
   before any narrowing.
5. **Liveness bug in the learn loop (the amplifier).** On FindC-None (quacq.py:236-237) the loop
   logs a warning but does **NOT** pop the tested constraint from `remaining_bias` and does NOT
   append (the pop at quacq.py:234 only runs when `c_id is not None`). `remaining_bias` is unchanged.
6. **Infinite deterministic retry.** Next iteration `generate_from_sat` returns the **same** first
   candidate 116 → same query → same rejection → same `{interface}` scope → same None → repeat until
   `max_queries`. **A single un-isolable constraint starves all 294 others; KB stays 0.**

## Two candidate deeper causes (for the fix decision — not disambiguated here)
- **(a) FindScope truncation.** The Algorithm-2 binary search (findscope.py:84-85, the
  `ask_query=len(S1)>0` short-circuit on the second half) can drop a variable when the violated
  constraint straddles both partitions → returns `{interface}` instead of `{interface, jplug}`.
- **(b) Over-determined negative examples from a minimal BG.** `BG = 1 root clause only`
  (`get_root_clauses()` → 1). The discriminating query satisfies only `root + ¬116`, so it may
  violate MANY true FM constraints at once, not just 116. FindScope then localizes to whatever the
  smallest violation is (here a subset that no bias constraint matches). In the paper, the query
  should satisfy KB∪BG and violate *only* the candidate — a richer BG would make examples
  cleanly localizable.

Both plausibly co-occur; (b) makes (a) more likely to bite. Either way the breaking stage is the
**FindScope→FindC scope handoff**, and the learn-loop **no-progress-on-None** turns one failure into
total stall.

## Answers to the four questions
1. **valid vs invalid:** 0 valid / 34 invalid — every query rejected.
2. **FindScope/FindC + append:** FindScope runs (non-empty scope, `empty_scope=0`); FindC runs but
   returns None **34/34** (`no_candidates_with_scope`); **0 constraints appended**.
3. **discriminating vs oracle-valid:** the generator IS discriminating and correct; the failure is
   downstream (scope localization + candidate matching).
4. **seed/determinism:** deterministic, **no seed** — the same candidate 116 is retried every
   iteration (SAT enumeration over fixed bias order), which is why it reproducibly stalls.

## Is a fix worth it? (CW Impl + CW Main call — no fix made)
- The paper reports **example-mode** QuAcq (matches ConGen's fixed example set), which does not use
  this SAT/oracle path — so oracle-mode may be **optional**. QuAcq-active is already gated NO-GO and
  headed to "informational."
- If a fix IS wanted, the **cheapest** correctness lever is the learn-loop liveness bug (step 5):
  on FindC-None, pop/skip the un-isolable constraint so the loop progresses to the other 294. That
  alone would stop the stall (KB would still be under-learned via the FindScope issue, but no longer
  0-and-stuck). A proper fix also needs FindScope scope correctness and/or a richer BG (cause a/b).

## Unresolved questions
1. Which of (a) FindScope truncation vs (b) minimal-BG over-determination dominates? Confirming
   needs a trace of the FindScope recursion on the 116 example (another read-only pass) — do CW want it?
2. Given the paper uses example-mode, does CW Main want oracle-mode fixed at all, or documented as a
   known limitation and QuAcq-active reported informational?

_(Diagnosis added no repo changes; the throwaway script lives in the session scratchpad. The
earlier red-team fixes remain uncommitted and are unrelated to this investigation.)_
