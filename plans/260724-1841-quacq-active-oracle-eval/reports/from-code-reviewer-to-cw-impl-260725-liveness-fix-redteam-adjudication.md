# Code Red-Team Adjudication — QuAcq oracle-mode liveness fix (1718a99)

2 hostile reviewers (soundness/recall; guardrail/regression/test) + controller verification. Read-only;
all runs to /tmp; suite green (590p/1s). Corrections committed in **312b7b1**.

## Verdict
The liveness fix **achieves its goal** — oracle mode now terminates (monotone progress, converges via
no_query, no spin) and learns a non-empty KB; strictly dominates the pre-fix KB=0. **NOT a regression.**
But the red-team **overturns two claims I made in 1718a99** ("deterministic", "un-representable in binary
bias") and shows the *result* is not yet paper-ready. None of the deeper issues are in fix (b)'s scope
(the prompt forbade touching FindScope/FindC beyond the pop) — they are gate-blocking for the paper.

## Confirmed by controller (my earlier claims were wrong)
- **Non-determinism ACROSS processes (Critical, R1-F1):** default `PYTHONHASHSEED` → KB ∈ {6,10},
  queries ∈ {342,353,474,968}, F1 ∈ {0.625,0.667}; **`PYTHONHASHSEED=0` pinned → identical (KB=10,
  q=353).** My "deterministic (3×)" ran in ONE process = one seed. Root: FindScope/FindC string-set
  iteration is hash-order-dependent (pre-existing; fix (b) merely surfaced it by making learning happen).
- **The drop discards TRUE constraints (High, R1-F2):** of 24 FindC=⊥ drops, ~15 carry a ground-truth
  C_T clause; KB entails 10/22 clauses, KB+dropped-true entails 18/22 → the drop alone costs ~8 clauses
  (sem_r ~0.45 vs ~0.82 achievable). So recall is **bug-capped (FindScope mislocalization), not
  bias-capped** — my "un-representable in binary bias" rationale is refuted.

## Findings (deduped; all Accept)

| # | Finding | Sev | Disposition |
|---|---------|-----|-------------|
| L-1 | Non-deterministic across processes (hash seed) → KB/F1/queries vary; one seed learns an UNSOUND constraint (precision <1.0) | **Crit** | Report → needs PYTHONHASHSEED pin + canonicalized (sorted) string-set iteration in FindScope/FindC (separate task, out of fix-b scope) |
| L-2 | Drop discards ~8 true binary constraints via FindScope multi-violation mislocalization → recall bug-capped | **High** | Report → proper fix is FindScope localization; comment corrected to name it a recall trade-off |
| L-3 | Reported sem F1 0.667 is the rosiest metric — description F1 = 0.261 (3/10 learned are named FM constraints; 7 are FM-entailed redundancies) | Med-High | Report → publish sem AND desc P/R/F1; lead with desc for an acquisition claim |
| G-3 | Commit rationale wrong for `example_first` — its SAT fallback (`generate()`) shares the spin, NOT covered (gated to oracle) | Med | **Fixed comment** (312b7b1); example_first behavior byte-identical (not extended); decide if it's a reportable mode |
| G-1 | Progress test loose (`n_kb>0` passes a 90% collapse); T11 golden is spin-blind (it IS the spin snapshot) | Med | **Fixed** — floor `n_kb>=5` (tolerant of hash variance 6–10); T11 golden left as a low-budget determinism tripwire |
| L-5/G-4 | Sibling asymmetry: empty-scope APPENDS tested_c_id, FindC=⊥ DROPS it (precision risk) — dormant on REAL-FM-7 (empty-scope fired 0×) | Med | Report → make the two branches consistent (separate) |
| L-4 | Sub-budget partial KBs (max_queries) scored into the headline F1 on other KBs | Med | Already mitigated by H-3 aggregate exclusion; size max_queries per KB so no_query is guaranteed |
| G-5 | QuAcq-active CV `mean ± 0.000` overstates robustness (fold-independent single value) | Low | Report (same as prior H-1) |

## Refuted / verified SAFE (both reviewers, controller)
- **Example-mode byte-identical (the core guardrail):** R2 single-variable diff vs parent — example_only
  (`n_kb=8, pool_exhausted`) AND example_first (`n_kb=8, max_queries`) byte-identical (KB + full
  query-history hash + n_queries + reason). Controller: example-only sem-F1 = 0.0786 unchanged.
- **Termination is sound:** monotone progress confirmed (|remaining_bias| strictly decreases every
  FindC=⊥ iteration, 295→26); the spin is genuinely gone (spin sub-claim refuted by both reviewers).
- No mutation-during-iteration hazard; eval path self-consistent (QuAcq-active rows now no_query, KB=10,
  included in aggregate — not excluded as max_queries).

## Corrections committed (312b7b1)
Comment: drop is a liveness band-aid (recall trade-off via FindScope mislocalization), not
"un-representable"; example_first SAT-fallback noted as uncovered. Progress test: floor `n_kb>=5`.

## Honest re-statement of the gate result (I over-claimed before)
Prior response called this "overturns NO-GO / strong 0.667 / deterministic." **Corrected:** fix (b)
fixes the liveness spin (oracle mode terminates + learns — real progress), and the result is *promising*
(sem precision high, sem F1 ~0.63–0.67 on REAL-FM-7), but it is **fragile**: non-deterministic across
processes, recall bug-capped at ~0.45 (vs ~0.82 achievable) by a FindScope localization bug the drop
masks, and 0.667 is the most favorable of three metrics (desc F1 = 0.261).

## Gate recommendation (CW Impl / CW Main)
Before any sweep or paper cite, decide:
1. **Determinism** — pin `PYTHONHASHSEED` in the eval harness and/or canonicalize FindScope/FindC
   string-set iteration; otherwise the QuAcq-active number is one non-reproducible draw.
2. **Recall** — fix FindScope multi-violation localization (recovers ~0.45→~0.82 sem-recall) vs accept
   the drop's lower recall. This is where the real QuAcq quality lives.
3. **Metric** — report sem AND description P/R/F1; the description metric (0.261) is the honest
   acquisition-quality number.
All three are separate tasks (out of fix-b's minimal scope). Fix (b) itself is done and correct-for-liveness.

## Unresolved questions
1. Which seed/solver produced any QuAcq-active number intended for the paper? (0.667 is PYTHONHASHSEED=0
   / the value varies otherwise.)
2. Is `example_first` a reportable eval mode? If yes, its un-fixed SAT-phase spin needs a decision.
3. Fix FindScope localization (raises recall, changes all QuAcq numbers) before the sweep, or after?
