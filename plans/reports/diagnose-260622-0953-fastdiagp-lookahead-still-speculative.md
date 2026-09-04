# FastDiagP speculative lookahead — STILL WIRED after R8 (verdict: (a) BENIGN)

**Date:** 2026-06-22 · **Branch:** `feat/redesign-abc` · **Mode:** diagnose-first (production byte-unchanged) · **Status: RESOLVED — (a) benign, new regression test added, suite 577→578 green.**

## Verdict
**(a) BENIGN.** R8 did NOT disconnect lookahead. FastDiagP's speculative lookahead is fully wired and FIRES on every fixture tested — including the small `smartwatch_inconsistent` the prior report measured as `speculative_submits=0`. That "0" was a **profiler-routing measurement artifact**, not a regression.

## Wiring trace (code intact)
`_fd` (fastdiagp.py:110) → `is_consistent_with_lookahead` (:135) → `lookahead` (:152) → `self.executor.submit(BwithC)` (:167). Executor = `MemoizingExecutor`. Path reachable & live:
- Serial: `ConsistencyChecker.submit` (checker.py:100) runs the CC inline → resolved Future.
- Parallel: `ProcessExecutor.submit` (executor.py:171) `apply_async` → real worker dispatch.
- `lookahead` level-0 submits the current node's CC (coalesces with the line-150 blocking check via `_pending`); deeper levels submit FUTURE-branch CCs = genuine speculation. Recursion (cases 1.x/2.x, :170-219) is intact.

Order matters and is correct: `lookahead(...)` dispatches all speculative submits FIRST, THEN line 150 blocks on the current CC → future-branch CCs overlap the blocking solve. FastDiagP keeps its reason to exist.

## Measurement (instrumented via monkeypatch in a throwaway probe — now deleted; production untouched)
Profiler routed into FastDiagP (the fix vs the artifact). 8-core host, `maxNumGenCC=4`.

| case | \|set_c\| | FastDiag CC | FDP-serial CC | FDP-parallel CC | lookahead_calls (serial) | ProcessExec async dispatches | deep spec submits |
|---|---|---|---|---|---|---|---|
| smartwatch (small) | 11 | — | 6 | 6 | **2** | — | 3 |
| prod_1_1.cnf +1 contradiction | 86 | 8 | 9 | 9 | 3 | 8 | 5 |
| prod_1_1.cnf +4 contradictions | 92 | 17 | 22 | 23 | 7 | 22 | 14 |
| linux.cnf +4 contradictions | 12083 | 24 | 28 | 30 | 9 | 29 | 18 |

Large/deep cases use a REAL FM CNF (`tests/resources/{prod_1_1,linux}.cnf`) made UNSAT by injecting `v ∧ ¬v` over-constraints (semantics-free, robust) → non-trivial diagnosis → deep recursion.

Three independent signals confirm genuine speculation (not a no-op):
1. **Overage vs non-speculative FastDiag:** FDP does strictly MORE CCs (linux 28 vs 24; prod-deep 22 vs 17). This is the classic FastDiagP CC-for-parallelism trade-off — present.
2. **Real async pool work:** `ProcessExecutor.submit` fired 29× on linux (independent counter).
3. **Async race visible:** parallel explores ~2× the lookahead nodes of serial (linux `lookahead_real` 82 vs 62) because speculative results land in cache asynchronously; serial fills cache synchronously and short-circuits earlier (`lookup_CC_ok` serial>parallel). Only possible if async speculation fires.

All diagnoses identical across FastDiag / FDP-serial / FDP-parallel in every case.

## Root cause of the prior `speculative_submits=0`
`FastDiagP.profiler` is set in `__init__`: `profiler_instance or get_global_profiler()`. The parity test builds `FastDiagP(MemoizingExecutor(checker, ps))` — **no `profiler_instance`** → FastDiagP's internal counters (`lookahead_calls`, `maxNumGenCC`, any added `speculative_submits`) route to the GLOBAL profiler, while the probe read the BENCHMARK profiler `ps` → 0. Reproduced exactly: my first run read `lookahead_calls=0` from `ps`; routing the profiler in → `lookahead_calls=2` on the SAME fixture. The prior probe almost certainly hit this; its `speculative_submits=0` is an artifact.

## Impact on the prior bounded-parity fix
The bounded-parity FIX (`|n_serial - n_parallel| <= 1`, commit `96d3e9e`) is **still correct** — diagnoses identical, and on `smartwatch` the gap is empirically 0 (±1 from `_pending` coalescing jitter). BUT its stated REASON ("speculation never fires, so it's not the mechanism") was based on the mis-measurement. Corrected reason: speculation DOES fire, but post-R8 the SAME FastDiagP code runs serial and parallel, so speculative CCs count EQUALLY in both → parity, regardless. The `_pending` coalescing race is a second, smaller effect.

## New regression tests (case (a) deliverable) — COMMITTED `24afc1b`
Shared helper `_assert_fastdiagp_lookahead_engages(cnf_path)` in `tests/test_executor.py`, exercised by TWO cross-fixture tests on distinct product-line CNFs:
- `test_fastdiagp_speculative_lookahead_engages_on_large_kb` → `prod_1_1.cnf` (`CNF_PROD`).
- `test_fastdiagp_speculative_lookahead_engages_on_second_kb` → `prod_4_1.cnf` (`CNF_PROD_4`).

Each guards the wiring a result-only test can't:
- `lookahead_calls > 0` (lookahead path reached — deterministic, serial).
- `maxNumGenCC > 1` → `n_FDP_serial > n_FastDiag` (speculative submits do real extra work; gated so a 2-core CI host, where `maxNumGenCC=1` structurally disables speculation, stays valid).
- diagnoses identical across FastDiag / FDP-serial / FDP-parallel.
A (b)-type regression (lookahead disconnected) → `lookahead_calls=0` + overage 0 → fails, while the diagnosis stays correct.

## Q1 RESOLVED — bounded-parity docstring corrected (no bound/assertion/fixture change)
`test_consistency_check_count_bounded_parity` docstring now states the `|serial - parallel| <= 1` bound is SMARTWATCH-SPECIFIC (in-flight `_pending` coalescing), NOT universal: on a large KB the parallel path explores a few more speculative branches and can exceed serial (measured `linux.cnf`: parallel − serial = **+2**). Corrected the prior wrong reason ("speculation never fires") → speculation DOES fire, but the same FastDiagP code runs both paths so speculative CCs count equally ⇒ parity; `_pending` coalescing is a small secondary effect. Assertion + smartwatch scope KEPT.

## Production untouched + commit
Commit `24afc1b` (test-only): `tests/test_executor.py` (+128/-15), `tests/resource_paths.py` (+5), `tests/resources/prod_4_1.cnf` (new fixture, now referenced). `explanation/` byte-unchanged vs HEAD. Probe deleted. No flamapy bump, no weakened assertion. **MERGE HELD — no PR opened** (awaiting your local `uv run pytest tests/ -v`). Green-gate: full suite **579 passed**; both lookahead tests stable.

## Unresolved questions
None. (Q1 resolved via docstring per your call; Q2 — synthetic `v ∧ ¬v` KEPT as a wiring canary, not FM semantics, per your call.)
