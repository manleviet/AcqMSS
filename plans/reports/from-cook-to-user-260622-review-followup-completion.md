# Review follow-up round — completion (A+B+C redesign)

**Date:** 2026-06-22 · **Branch:** `feat/redesign-abc` · **Suite:** 568 → **577 passed** (+9) · **Status: DONE — HELD before merge per user.**

Handled the post-review items (1)+(2)+(4)+(5). Each: green-gated, framework-isolated, on-disk/export format frozen (byte-identical), no weakened assertions, 1 commit/item.

## Done + committed (this round)
| Item | Commit | Result |
|------|--------|--------|
| (1) C2 — close the deferral: `UnifiedConGenResult` | `71c1511` | One class merges ConGenRunResult+ConGenResultData (Option A: `to_run_dict`/`to_statistics_dict` two serializers, byte-identical; from_json/from_dict factories; BaseRunResult kept). `ConGenResult` stays transient (int-ID pre-serialization). |
| (2) C7 — ratify twins-separate | `5afff52` | Each twin (qx/qxtc, wipeoutr_fm/_t) gets a cross-ref docstring stating the reason (different loop/recursion + distinct metric-key decorators). Plan C7 acceptance → "documented intentional-separate". |
| (4a) A2 — two-tier builder | `7789a67` | `AbstractModelBuilder` (universal: with_negation + abstract build) → `OracleBiasModelBuilder` (bias/oracle + from_bias/with_oracle + negation build). Diagnosis builder no longer carries unused bias/oracle fields. `explanation.api` exports `OracleBiasModelBuilder`. |
| (4b) B4 Low-1 — base_set_c field | `a909601` | Declared `base_set_c: Optional[List]` on `DiagnosisTask`; removed the 3 `# type: ignore[attr-defined]`. |
| (4c) nits | (in C2/earlier) | performance_metrics `Dict` import + RunMetrics comment already clean; test_assumption_slicer `_base_set_c` comments already fixed. |

## (3) MERGE — HELD (not opened)
All A+B+C + this round are committed on `feat/redesign-abc`, green (577). PR **not** opened — per your sequence: you run the full suite locally (`uv run pytest tests/ -v`, confirm 577 + the flaky test), then I open the single PR → main.

## (5) Flaky `test_consistency_check_count_parity` — FIXED (commit `96d3e9e`, test-only)
Re-measured (170 runs) and CORRECTED my earlier root cause: parallel does ≤ serial (by ≤1), not ≥ — the parallel pool's in-flight `_pending` dedup coalesces one concurrent duplicate CC (correct, diagnoses identical); speculation never fires on this fixture (speculative_submits=0). Fix = bounded parity `abs(n_serial - n_parallel) <= 1` (Option 1, corrected direction), renamed `*_bounded_parity`, documented. Not a weakening (corrects a wrong invariant; still catches double-count). Production `fastdiagp.py` untouched (the probe metric was reverted). Verified non-flaky: 30× isolated + 3× full-suite under load + 170 char runs, 0 failures. Detail: `from-cook-to-user-260622-flaky-parity-test-followup.md`.

## Verification
577 passed; boundary guard green; 0 conacq→explanation deep imports; 0 base_set_c type:ignore; result aliases reframed as intent-revealing (the one unified class). Plan C2 + C7 acceptance updated.

## Unresolved questions
1. ~~Flaky parity test~~ — RESOLVED (bounded parity `|gap|<=1`; my earlier direction was wrong, corrected after 170-run measurement). Decided in-band: symmetric bound is the empirically-correct, fixture-robust form of your Option-1 intent.
2. Result-class aliases: KEPT `ConGenRunResult`/`ConGenResultData` as intent-revealing names for the single `UnifiedConGenResult` (you ratified GIỮ NGUYÊN). No change.
3. **MERGE — HELD.** All committed + green (577, suite run 3× clean). Ready to open the single PR `feat/redesign-abc → main` whenever you give the signal after running `uv run pytest tests/ -v` locally.
