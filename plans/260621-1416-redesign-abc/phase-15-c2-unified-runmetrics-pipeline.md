---
phase: 15
title: C2 unified RunMetrics pipeline
status: completed
priority: P1
effort: 2-3d
dependencies:
  - 5
  - 11
---

# Phase 15: C2 — unified RunMetrics source of truth

## Overview
Collapse the metric god-module + scattered tracks into one `RunMetrics` source of truth flowing run→fold→aggregate. `aggregate_metrics` becomes a generic reducer over a metric registry — no 70-field `AggregatedPerformanceMetrics`, no `_stat4`×25. Folds the disjoint tracks (`BaseRunResult`→`PerformanceMetrics`→`AggregatedPerformanceMetrics`→`CrossValidationFoldResult` carrying both `EvaluationMetrics`+`PerformanceMetrics`+raw `profiler_data`) plus the divergent hand-built `EvaluationMetrics(` sites (kb_comparator/accuracy) that bypass `compute_metrics()` (the brief mislabeled this as `progressive_evaluation.py` — corrected below). Also unifies the overlapping result dataclasses (`ConGenResult`/`ConGenResultData`/`ConGenRunResult`).

## Safety-net
Covered by test_evaluation; before refactoring, assert it pins concrete aggregate values (mean/std/etc.). Add cases if aggregation branches are uncovered.

## Requirements
- Functional: one `RunMetrics` flowing through run→fold→aggregate; generic reducer over a registered metric set; all `EvaluationMetrics` built via one `compute_metrics()` path (no divergent hand-built sites in kb_comparator/accuracy); overlapping result dataclasses unified.
- Non-functional: identical aggregate outputs (mean/std/min/max) vs current; CSV/JSON/LaTeX exports unchanged in shape.

## Architecture
- `RunMetrics` dataclass + a metric registry `{name: reducer}`; `aggregate_metrics` iterates the registry instead of 30 hand-written `_stat4` calls.
- Single result type replacing `ConGenResult`/`ConGenResultData`/`ConGenRunResult`.

## Related Code Files (verified)
- Modify: `conacq/eval/performance_metrics.py` (652 LOC; `PerformanceMetrics`, `AggregatedPerformanceMetrics` 70 fields, `aggregate_metrics` + `_stat4`×25)
- Modify: the real `EvaluationMetrics(` construction sites — `conacq/eval/kb_comparator.py:163`+`:319`, `conacq/eval/accuracy.py:117` (route divergent hand-built metrics → `compute_metrics()` in `metrics.py:144`); `conacq/eval/cross_validation.py`/`folds.py` (fold carriers). NOTE: brief's `progressive_evaluation.py:315-325` is wrong (no `EvaluationMetrics(` there) — re-scout per Red-team adjustments.
- Modify/merge: `conacq/algorithms/acqmss/congen.py` (`ConGenResult` :36-44), `conacq/eval/result_loader.py` (`ConGenResultData` :14-33), runner `ConGenRunResult`
- Modify: A4 `BaseRunner` metric map to emit `RunMetrics`

## Implementation Steps
1. Pin current aggregate outputs in test_evaluation (safety-net values).
2. Define `RunMetrics` + metric registry + generic reducer; port `aggregate_metrics`.
3. Re-point run→fold→aggregate to `RunMetrics`; delete the 70-field dataclass + `_stat4`.
4. Route the divergent hand-built `EvaluationMetrics(` sites (kb_comparator.py:163/:319, accuracy.py:117) through `compute_metrics()` (metrics.py:144) — single construction path. (NOT progressive_evaluation — no EvaluationMetrics constructed there.)
5. Unify the 3 result dataclasses into one.
6. `PYTHONPATH=. pytest tests/ -v` → green (aggregates match pinned values).

## Success Criteria
- [x] One `RunMetrics` name; one generic reducer (no `_stat4`×N). 70-field `AggregatedPerformanceMetrics` KEPT — its field names ARE the frozen on-disk/export schema (freeze > "retire it").
- [x] `EvaluationMetrics`: clause path already routes through `compute_metrics`; kb_comparator/accuracy sites build from different inputs (descriptions/examples) — distinct strategies, not duplicates (validated).
- [x] `ConGenRunResult`/`ConGenResultData` unified into `UnifiedConGenResult` (Option A: one class, two serializers — `to_run_dict`/`to_statistics_dict` byte-identical; user-ratified 260622). `ConGenResult` (transient int-ID algorithm output) kept separate — pre-serialization stage.
- [x] Aggregate outputs identical to pinned baseline (frozen-ref @1e-12); exports byte-identical (19-file from_json round-trip + serializer byte-compare).
- [x] Full suite green (≥351)

## Red-team adjustments (applied 260621) — most likely to go green hiding a regression
- **STALE REF CORRECTED:** the "5th inline EvaluationMetrics path" is NOT in `progressive_evaluation.py` (no `EvaluationMetrics(` constructed there — brief's `:315-325` is wrong). Real construction sites: `conacq/eval/kb_comparator.py:163` + `:319`, `conacq/eval/metrics.py:144`, `conacq/eval/accuracy.py:117`. RE-SCOUT the genuine duplicate vs `compute_metrics()` before pinning; "1 source of truth" acceptance targets these, not progressive_evaluation.
- **Frozen-reference pinning (was a 1-line safety-net):** BEFORE refactor, snapshot current `aggregate_metrics` output to a frozen reference dict (key→value); assert the new reducer reproduces it key-for-key (survives the API change because it compares CAPTURED numbers, not re-derived ones). When porting the 28 named-field assertions (`agg.runtime_mean_ms`, `agg.acqmss_calls_max`, `agg.findscope_calls_mean`, …) change ONLY access syntax, never the pinned values. **Byte-compare one real CSV/JSON export pre/post is MANDATORY** (not "where feasible").
- **Widen importer list for result-dataclass unification:** `congen.py`, `result_loader.py`, runner PLUS `conacq/algorithms/__init__.py`, `acqmss/__init__.py`, `runners/__init__.py`, `eval/__init__.py`, `kb_comparator.py` (:136/:193/:288), `congen_model.py`. KEEP `ConGenRunResult`'s `BaseRunResult` inheritance (A4 metric map depends on it). Add a `from_json`/`from_dict` round-trip test on an EXISTING on-disk CV JSON (`apps/run_congen.py:94` depends on that format).
- **Cross-check after C7:** include the per-algorithm runtime/call metrics (qx/qxtc, wipeoutr_fm/_t) in the pinned set — C7 must have preserved both key sets.

## Validate decisions (260621)
- **On-disk + export format FROZEN (user).** The result-dataclass unification is IN-MEMORY only. `ConGenResultData.from_json`/`from_dict` MUST still read existing `data/results/congen/*.json` unchanged; CSV/LaTeX exports (→ `paper/tables/results_tables.{tex,md}` via `apps/extract_results.py`) byte-identical. Keep serialized field names/shape on disk even if in-memory names change.
- **Mandatory regression tests:** (a) load each existing `data/results/congen/*.json` via `from_json` post-refactor → assert parses + equals; (b) byte-compare one `apps/extract_results.py` export pre/post.

## Disposition (260621) — FOR USER RATIFICATION at Phase C checkpoint
- **DONE + committed:** generic `_METRIC_REGISTRY` reducer replacing `_stat4`×25 (96/96 aggregate fields proven identical, frozen-ref reconstructed from git HEAD == new output at 1e-12); `RunMetrics` published; frozen on-disk/export format preserved (19-file from_json round-trip + byte-identical to_dict); 35 safety-net tests. Independent review = PASS.
- **DECLINED (validated correct, not a cut):** routing kb_comparator:163/:319 + accuracy:117 through `compute_metrics()` — they consume different inputs (description strings / semantic counts / example accept-reject) vs `compute_metrics`'s clause sets. Same metric *type*, different *inputs* → not duplication. The brief's `progressive_evaluation:315-325` was a phantom (no EvaluationMetrics there). Reviewer agreed.
- **70-field dataclass KEPT (required, not a miss):** the plan's "retire the 70-field `AggregatedPerformanceMetrics`" CONFLICTS with the user's later freeze decision — those field names ARE the frozen on-disk/export schema. Freeze wins.
- **DEFERRED — balloon-split (the one "no-deferral" tension):** unifying `ConGenResult`/`ConGenResultData`/`ConGenRunResult`. They serve 3 layers with incompatible on-disk sub-key shapes (`statistics` vs `performance`); the freeze blocks the simple merge. Reviewer agreed it's a legit split. **User: do the `UnifiedConGenResult` follow-up now (classmethod constructors reading existing on-disk format, keep BaseRunResult inheritance), or accept the reducer-only delivery?**

## Risk Assessment
- This is the largest-blast C item → if it balloons, SPLIT (e.g. reducer first, then dataclass unification, then progressive path) and report — do NOT cut.
- Aggregation numeric drift → the pinned safety-net values are the guard; compare exports byte-for-byte where feasible.
