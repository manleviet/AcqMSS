# AcqMSS redesign A+B+C — completion report

**Date:** 2026-06-21 → 22 · **Branch:** `feat/redesign-abc` (off `feat/phase-r-task-as-unit`) · **Plan:** `plans/260621-1416-redesign-abc/` (18/18 phases)
**Suite:** 352 → **568 passed** (+216 tests) · **Net:** 107 files, +7197 / −3870 LOC · **flamapy~=2.0.1 / py3.11 unchanged**

## Outcome
All 18 stages: delegate → independent-verify → code-review (PASS each) → green-gate → 1 commit/stage. 21 commits. Every global acceptance criterion met:
- `print()` = 0 in apps/conacq/explanation (interactive user_prompt excepted)
- 0 conacq→explanation deep/private imports — enforced by `tests/test_boundary_guard.py`
- sat4j op clones deleted; `_ASSUMPTION_PAIR_STRIDE` internal to explanation
- single seeded RNG (reproducibility tests); generic metric reducer (`_stat4`×25 → 1)
- on-disk JSON + CSV/LaTeX export formats FROZEN (verified byte-identical + 19-file from_json round-trip)
- framework changes isolated under `explanation/` for a clean future repo extraction

## Stage commits
A7 `1073c79` pytest infra · A1 `667855f` slicer · A2 `baf9e62` builder base · A3 `914c8d2` sat4j fold · A4 `8fb3219` BaseRunner · A6 `69d61b9` apps harness+atomic JSON · A5 `76a4835` logging
B2 `7ba0a1a` profiler package+Protocol · B3 `7ef33d8` Oracle contract · B4 `c1199c7` last_task removal+FMOracle purity · B1 `d47cbae` explanation.api + boundary guard
C5 `62e61d9` codec+seeded RNG · C7 `5fb96e5` labeler base + test_diagnosis→pytest · C1 `bbc413e` SolverBackend port · C2 `0d5ab08` metric reducer · C4 `34b3302` IO mixin · C3 `2f789a4` op registry · C6 `fda29d7` dead-code
(+ `20cb10e` pre-existing codec fix, separated)

## Deviations (3) — judgment calls, each validated by independent review
1. **C2 result-dataclass unification DEFERRED** (balloon-split). `ConGenResult`/`ConGenResultData`/`ConGenRunResult` have incompatible on-disk sub-key shapes (`statistics` vs `performance`); the frozen-format decision blocks the simple merge. Reducer (the main win) landed; unification needs a `UnifiedConGenResult` follow-up. The 70-field `AggregatedPerformanceMetrics` was KEPT — its field names ARE the frozen schema (plan's "retire it" conflicts with the freeze; freeze wins).
2. **C2 EvaluationMetrics single-path DECLINED** (validated not-duplication). kb_comparator:163/:319 + accuracy:117 build EvaluationMetrics from different inputs (description strings / semantic counts / example accept-reject) vs `compute_metrics`'s clause sets — same metric type, different inputs. Brief's `progressive_evaluation:315-325` was a phantom.
3. **C7 algorithm twins KEPT SEPARATE** (behavior-preservation > DRY). qx/qxtc + wipeoutr_fm/_t not merged: wipeoutr structurally different; qx/qxtc merge would force rewriting per-twin metric-key decorators → manual calls, risking the C2 metric contract on diagnosis-critical recursion. Labeler base = 2 shared methods (`identify_new_node_parameters` genuinely differs per labeler — verified).

## Known issue (pre-existing, not introduced)
`tests/test_executor.py::...::test_consistency_check_count_parity` — intermittent (~1/3) concurrency race in the parallel ProcessExecutor's `is_consistent_calls` counting. Passes in isolation; gate policy = re-run on sole failure. Deterministic fix is a candidate for a future executor pass.

## Unresolved questions (for user)
1. **C2 follow-up:** do the `UnifiedConGenResult` dataclass unification now (keep BaseRunResult inheritance + from_json reading existing format), or accept the reducer-only delivery? (Plan said "no deferral"; this is the one genuine balloon-split.)
2. **C7:** ratify keep-separate for qx/qxtc twins, or request the metric-decorator→manual merge?
3. **Merge:** open the single PR `feat/redesign-abc` → `main` now (plan cadence = 1 PR at end)?
4. Minor follow-ups noted in reviews: bias_generator.py 298 LOC (modularize?), dimacs_to_diag_pysat DIMACS-parse dedup, deterministic fix for the flaky parity test.
