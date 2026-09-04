# Flaky `test_consistency_check_count_parity` — RESOLVED (with root-cause correction)

**Date:** 2026-06-22 · **Branch:** `feat/redesign-abc` · **Status: FIXED** (commit `96d3e9e`). Production code untouched — test-only fix.

## Correction to my earlier analysis
My first follow-up hypothesised the parallel path does *more* CCs than serial (uncoalesced speculative overage → `n_parallel >= n_serial`, bound by speculative submits). **That was wrong.** Empirical measurement (170 runs) disproved it:
- `n_serial` = 6 (deterministic); `n_parallel` ∈ {5, 6}.
- gap `serial - parallel` ∈ {0: ~93%, 1: ~7%}, **max |gap| = 1**, never the other direction.
- `speculative_submits` / `lookahead_calls` = **0** on this fixture (smartwatch_inconsistent) — speculation never fires here, so it is NOT the mechanism and cannot be the bound.

## Real root cause
The parallel path occasionally does *one FEWER* check, not one more. `MemoizingExecutor.is_consistent` (`executor.py:232-241`) coalesces a concurrently-arriving duplicate CC onto an in-flight `_pending` future instead of re-solving it. Under the async worker pool's timing this fires ~7% of the time for one CC; the serial path (synchronous) counts that CC separately. This is **correct coalescing, not a lost result** — the diagnoses are identical (`test_fastdiagp_serial_vs_process_identical` proves it). The original `n_serial == n_parallel` assertion was simply too strict.

## Fix (Option 1, corrected direction)
Invariant `n_serial == n_parallel` → **bounded parity `abs(n_serial - n_parallel) <= 1`** (+ both > 0; solver_time checks unchanged). Test renamed `test_consistency_check_count_bounded_parity`; docstring + inline comment state the technical reason (in-flight coalescing window), no plan refs.
- Not a weakening: it corrects a wrong invariant. The bound still catches the regressions the test guards — a double-count bug roughly doubles the parallel count (gap ≫ 1); a lost-result bug changes the diagnosis (caught elsewhere).
- The added `speculative_submits` metric probe (used only to disprove the speculation hypothesis) was **reverted** — production `fastdiagp.py` is unchanged.

## Non-flaky verification (per request: many runs under load)
30× isolated + **3× full-suite under contention** (where the original `==` failed ~1/3) + 170 characterization runs → **0 failures**. Full suite 577 passed each run.

## Unresolved questions
None. (Direction correction noted above — empirically settled at 170 runs; the symmetric `|gap|<=1` is direction-agnostic and fixture-robust, so it holds regardless of which way the coalescing jitter goes.)
