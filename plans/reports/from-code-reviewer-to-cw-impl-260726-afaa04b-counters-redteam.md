# Red-team `afaa04b` (permanent diagnostic counters) — VERDICT: PASS, no findings

Hostile, outcome-instrumented (a REAL end-to-end eval + --merge to /tmp, not a code read). Temp Task-2
probe is env-gated (`QUACQ_BA_AIDS`) → inert here, so this exercises the committed `afaa04b`. No code
changed by the review.

## Attacks run + results
| # | Attack | Result |
|---|---|---|
| A1 | Do the 5 columns actually reach the **merged** CSV? | **PASS** — all 5 present in `conmin_eval_long.csv` after a real eval + `--merge` |
| A2 | Are A/C/C∪S rows byte-identical (no leakage)? | **PASS** — A/C/C∪S carry the diag columns **BLANK**; only QuAcq/QuAcq-active are filled |
| A3 | Does `--merge` warn "stale schema" on the additive delta? | **PASS** — clean merge, 78 rows, no stale/conflict warning (ADDITIVE allowlist works) |
| A4 | Does `aggregate_cv` break on the new numeric columns? | **PASS** — cv CSV built (26 rows), no error |
| A5 | Do counters collide with an existing profiler/QUACQ_METRICS key? | **PASS** — none in metrics.py; new keys only |
| A6 | Does ConMin/AcqMSS ever hit the counter sites? | **PASS** — prune_rejecting/findscope/findc are QuAcq-only; 0 ConMin call sites |
| A7 | Determinism of the counters across hash seeds? | **PASS** — identical under PYTHONHASHSEED 0/1/7 + unset |
| A8 | Behavior change (control flow)? | **PASS** — REAL-FM-7 oracle KB=12/q=272 unchanged; increments are pure counts |
| A9 | Golden regression? | **PASS** — `diagnostics` not in `to_dict`; T11 golden untouched; 591 passed |

## Observed values (REAL-FM-7, merged CSV)
- **A / C / C∪S:** diag columns BLANK (correct).
- **QuAcq-active (oracle):** bandaid=10, findc_unconfirmed=10, empty_scope=0, prune partial/complete=133/102.
- **QuAcq (example-only):** bandaid=**0** (band-aid is `mode=='oracle'`-gated — correct), findc_unconfirmed=1,
  prune partial/complete=7/143.

## Self-refutation / nuance (not a defect)
Fix (iii)'s FindC "return None when unconfirmed" is **mode-agnostic**, so it also runs in example-only —
the counter shows `findc_unconfirmed=1` there. But example-only's learned KB was verified **byte-identical**
at `b40771c` (KB=1, q=23, sem-F1 0.087): whether FindC guesses or declines, the pool-based run converges
to the same KB. So the counter *reveals* a decline that does not change the outcome — a transparency gain,
not a behavior change. (Had it changed the KB, A9/the example-only guard would have caught it.)

## Verdict
`afaa04b` is **safe and correct**. The counters reach the CSV, are additive-clean through `--merge`,
survive `aggregate_cv`, don't touch A/C/C∪S/ConMin, are deterministic, and don't change any learner's
behavior. **GREEN — the sweep will record the fairness-disclosure numbers as intended.**

## Task-2 genuine-drop figures (band-aid drops: genuine-target G vs over-strong S; glucose4)
| KB | \|C_T\| | band-aid drops | G (genuine lost) | S (over-strong, legit) | R | reason | \|KB\| |
|---|---|---|---|---|---|---|---|
| REAL-FM-7 | 22 | 10 | **1** | 2 | 7 | no_query ✓ | 12 |
| arcade-game | 130 | 56 | **35** | 21 | 0 | timeout | 14 |
| REAL-FM-4 | 428 | 29 | **18** | 11 | 0 | timeout | 15 |
| fqa | 342 | 354 | **150** | 204 | 0 | max_queries | 6 |
| busybox-1.18.0 | — | — | **not measured** | — | — | — | — |

busybox not measured — prohibitively slow (|B|=6635, oracle-mode SAT per query too expensive for a
bounded run), per CW Impl's allowance. Genuine drops scale with KB size / non-convergence (the fix-iii
precision-for-recall trade); precision stays 1.0 on all (the drops are recall-only, never false learns).

## Status
Probe reverted; tree clean (`afaa04b` intact, 0 residue). Task 1 (counters) shipped + red-team PASS;
Task 2 (genuine-drop figures) complete. No further commits.

## Unresolved questions
1. Sweep budgets for the large KBs (fqa/arcade/REAL-FM-4 non-converged) — bump or accept non-converged?
   (CW Impl's earlier open item; unchanged.)
