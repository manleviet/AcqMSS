# Red-team `b40771c` + cross-KB precision gate — VERDICT: GREEN for soundness, report per-KB

Read-only + instrumentation (quacq pop/empty-scope tracer, env-gated, **reverted** — tree clean, b40771c
intact). Outcome-instrumented (measured pops/appends/precision, not narrative). REAL-FM-7 + fqa +
arcade-game; glucose4; oracle max_q=5000. No busybox. No code fix needed.

## One-line verdict
**`b40771c` is precision-safe across KBs → GREEN for the full sweep on soundness.** The fix does not need
changing. **Two non-code caveats** for the paper: (a) report per-KB — the REAL-FM-7 "0.848 vs 0.842
near-tie" is NOT representative; (b) fqa/arcade QuAcq-active are **non-converged** and near-empty, partly
because our band-aid drops genuine-target constraints on large KBs.

## Cross-KB gate table (QuAcq-active oracle, glucose4)
| KB | \|C_T\| | precision (R1) | recall | sem-F1 | desc-F1 | reason | breakers | band-aid genuine (R2) | empty-scope false (R1b) |
|---|---|---|---|---|---|---|---|---|---|
| REAL-FM-7 | 22 | **1.000** | 0.727 | 0.842 | 0.240 | no_query ✓ | 0 | 1 | 0 |
| fqa | 342 | **1.000** | 0.032 | 0.062 | — | max_queries | 0 | **150** | 0 |
| arcade-game | 130 | **1.000** | 0.192 | 0.323 | 0.262 | timeout† | 0 | 35 | 0 |

† arcade hit my script's 600s wall-clock at q=1130; the eval config's `quacq_active_timeout_s=400` would
truncate it *sooner* → non-converged in the real sweep regardless. fqa's max_queries=5000 is the eval
default → also non-converged in the sweep.

## Findings
**R1 — cross-KB precision: PASS (GREEN).** precision = **1.000** on all three KBs; **0 over-strong
learned clauses** anywhere. I actively tried to break it on the two larger, harder KBs and could not —
fix (iii)'s "learn only confirmed constraints" holds. sem-precision 1.000 = every learned clause is
C_T-entailed (sound).

**R1b — empty-scope unverified append: PASS.** Fired **0×** on all three KBs → the latent false-append
path (`quacq.py:266-269`) never triggered; 0 false constraints appended. (Still latent for other KBs;
unchanged from before — a separate small safety fix, not gating.)

**R2 — did (iii) shift losses into the band-aid? CONFIRMED, and it scales with KB size — but it is a
RECALL trade, not a soundness bug.** Genuine-target band-aid drops: **1 / 150 / 35** (REAL-FM-7 / fqa /
arcade). On REAL-FM-7 the fix *reduced* band-aid reliance (1 vs 13 pre-fix); on large KBs, FindC returns
None far more often (discrimination can't confirm among many candidates) → the band-aid drops many
genuine-target constraints → recall collapses (fqa 0.032). **These are precisely the constraints (iii)
declines to guess** — keeping them would require the old guess-heuristic that broke precision. So this is
the accepted precision-over-recall trade (Rule 2), realized at scale, not a regression to fix.

**R3 — `include_bg=False` edge cases: CLEAN.** `if partial:` guard (findscope.py:68) blocks any prune on
an empty partial. **0 unit clauses** and **0 clauses referencing the root literal** on either KB (root id
28/488 sits above the max feature-var 14/179), so the "root-in-clause" and "unit-clause" cases do not
occur; and even if they did, the fully-assigned rule (`assignment + constraint` UNSAT ⟺ a fully-assigned
clause is falsified) handles them correctly. No accidental never-prune / always-prune.

## What this means for the headline (the reason CW Impl asked)
- **Direction holds and strengthens:** ConMin ≥ QuAcq-active everywhere; the gap widens on large KBs
  (fqa QuAcq-active F1 0.062, arcade 0.323 — ConMin will dominate). The paper's thesis is safe.
- **The REAL-FM-7 near-tie is an artifact of a small KB** where QuAcq-active happens to do well
  (0.842). Do NOT present it as the typical case. Lead with the per-KB table; on large KBs QuAcq-active
  is weak AND non-converged.
- **Fairness note (unchanged trade):** QuAcq-active's low large-KB recall is *partly our band-aid*
  (150/35 genuine drops), not purely QuAcq's inherent limit. Report QuAcq-active honestly as a
  precision-1.0 but low-recall, often-non-converged baseline; don't overstate ConMin's margin as if
  QuAcq were fully tuned.

## Guardrails
Read-only review; probe reverted (tree clean, b40771c the only change). No byte-identity/determinism
risk (no code changed). All eval runs to /tmp; committed `data/results_conmin/*.json` untouched; bias +
ConGen `data/results/interactive/` untouched.

## Unresolved questions (CW Impl decides — none block soundness)
1. **Budgets for the sweep:** fqa (max_queries at 5000) and arcade (timeout) are non-converged. Bump
   `quacq_active_max_queries` / `_timeout_s` for them, or report as non-converged? NB even with more
   budget the band-aid genuine drops are permanent → recall stays capped; bigger budget mainly changes
   the convergence label, not the ceiling.
2. **Is a band-aid-capped QuAcq-active a fair baseline** on large KBs, or note the cap explicitly in the
   paper? (Precision is sound either way.)
3. Empty-scope unverified append (`quacq.py:266-269`) still latent (0× on these 3 KBs) — small safety
   fix before any KB where it fires; not gating this sweep.
