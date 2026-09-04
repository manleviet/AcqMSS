# Phase Implementation Report — C2 unified RunMetrics pipeline

## Executed Phase
- Phase: 15 — C2 unified RunMetrics pipeline
- Plan: /Users/manleviet/Development/GitHub/AcqMSS/plans/260621-1416-redesign-abc/
- Status: DONE_WITH_CONCERNS (one item split to follow-up — see below)

## Files Modified
| File | Change | Lines |
|------|--------|-------|
| `conacq/eval/performance_metrics.py` | Generic reducer + RunMetrics alias | 618 (was 652) |
| `conacq/eval/__init__.py` | Export RunMetrics | 158 (+2) |
| `tests/test_c2_runmetrics_safety_net.py` | New safety-net test file | 474 (new) |

## Tasks Completed

### Sub-step A — Generic reducer replacing _stat4×N (DONE)
- Replaced the 25× hand-unrolled `_stat4(…)` calls in `aggregate_metrics()` with a declarative `_METRIC_REGISTRY` list.
- Registry entries: `(extractor_fn, (mean_f, std_f, min_f, max_f), cast_int)`. `aggregate_metrics` iterates the registry in a loop, calling `setattr` on the `AggregatedPerformanceMetrics` instance.
- `AggregatedPerformanceMetrics` dataclass **unchanged** (all 70+ fields retained). `to_dict()` **unchanged**. On-disk key structure verified byte-identical against `data/results/congen/REAL-FM-7_rs_1n_cv_incremental.json`.
- `RunMetrics = PerformanceMetrics` alias added (communicates intent; same class, no new fields, no migration needed).

### Sub-step B — Safety-net + frozen-reference + from_json round-trip tests (DONE)
File: `tests/test_c2_runmetrics_safety_net.py` — 35 tests, all green.

Test classes:
- `TestFrozenReference`: pinned 2-run fixture, `_FROZEN_REFERENCE` dict capturing ALL `to_dict()` keys/values pre-refactor. Asserts key-for-key equality (float-tolerant), all named field values, int cast on min/max, QuAcq zero-default presence.
- `TestRunMetricsAlias`: identity, instantiation, `aggregate_metrics` acceptance.
- `TestFromJsonRoundTrip`: parametrized over all 19 `data/results/congen/*.json` (from_dict on each fold), 3-file round-trip `from_dict → to_dict`, single-fold `from_json`, missing `bg_clauses` default, enriched `[{id,description}]` format.
- `TestAggregateMetricsReproducibility`: determinism, single-run std=0, QuAcq+ConGen mixed.

### Sub-step C — EvaluationMetrics single-path analysis (DONE — SPLIT DECISION)
The spec's framing ("kb_comparator:163/:319 and accuracy:117 bypass compute_metrics()") is semantically incorrect for these sites:

| Site | Strategy | Can use compute_metrics()? |
|------|----------|---------------------------|
| `kb_comparator.py:163` | description-based (string sets) | NO — compute_metrics() takes clause tuple-sets, not description strings |
| `kb_comparator.py:224` | clause-based | YES — already routes through compute_metrics() (no change needed) |
| `kb_comparator.py:319` | semantic (SAT entailment counts) | NO — maps n_entailed integers; compute_metrics() inapplicable |
| `accuracy.py:117` | example-based accuracy | NO — TP/TN/FP/FN from SAT solver on examples; clause-set API doesn't apply |

**Conclusion**: there is already ONE construction path per strategy. The clause strategy (the only one compute_metrics() can serve) already uses it at line 224. The other three sites are genuinely different strategies — routing them through compute_metrics() would silently discard strategy-specific semantics. No change made; rationale documented.

## What was SPLIT (deferred to follow-up)

**Result-dataclass unification (`ConGenResult` / `ConGenResultData` / `ConGenRunResult`)** — deferred.

Reason: these three classes serve distinct abstraction levels:
- `ConGenResult` (algorithm): assumption-ID lists (int), no names/clauses
- `ConGenResultData` (disk loader): constraint name strings, on-disk JSON format
- `ConGenRunResult` (runner): extends `BaseRunResult` (BaseRunner metric-map dependency); adds profiler fields; produces `to_dict()` for the `performance` section of on-disk CVresult JSON

Merging them without changing on-disk format is non-trivial because `ConGenRunResult.to_dict()` produces `performance` sub-key that is DIFFERENT from `ConGenResultData.to_dict()` which produces `statistics` sub-key. A unification that kept both serialization shapes would require a divergent `to_dict()` dispatch — adding complexity rather than removing it. The frozen-format constraint blocks the simplest unification path. Splitting is the correct call per spec instruction ("if C2 balloons → SPLIT and report").

Follow-up: define a `UnifiedConGenResult` that holds both algorithm-level and runner-level fields, keeping `from_json`/`from_dict` as factory classmethods reading the on-disk format, with `BaseRunResult` inheritance preserved.

## Tests Status
- Type check (mypy): not run (project does not enforce mypy in CI per pyproject.toml)
- Unit tests: **552 passed, 0 warnings** (517 baseline + 35 new)
- Integration tests: N/A (no live FM runs required for this stage)
- Baseline confirmed: `uv run --no-sync pytest tests/ -q` → 517 passed before changes

## Pinned Values — Confirmed Unchanged
The 28 named-field assertions in the existing `test_evaluation.py::TestPerformanceMetrics` suite all pass unchanged. The frozen-reference test adds an additional full `to_dict()` key-for-key comparison. No pinned value was modified — only the implementation of the reducer changed.

## On-disk Format — Confirmed Frozen
- `AggregatedPerformanceMetrics.to_dict()` is bit-for-bit identical to prior implementation.
- `ConGenResultData.to_dict()` is unchanged.
- All 19 on-disk CV JSONs parse via `from_dict` + `from_json` without error.

## Issues Encountered
1. `progressive_evaluation.py:315-325` reference in spec is wrong (confirmed by read — 211 LOC, no `EvaluationMetrics` construction). Corrected as noted in Red-team adjustments.
2. Result-dataclass unification blocked by frozen-format constraint → split as instructed.

## Next Steps (follow-up sub-step)
- Define `UnifiedConGenResult` with dual serialization shape + `BaseRunResult` inheritance
- Wire `ConGenRunner` to emit `UnifiedConGenResult` while keeping `from_json`/`from_dict` backward-compatible
- Retire `ConGenResult` (algorithm-level) by making `ConGen.acquire()` return the unified type or a thin internal dataclass that is immediately consumed by the runner

---

**Status:** DONE_WITH_CONCERNS
**Summary:** Generic reducer implemented (no _stat4×N); RunMetrics alias published; 35 safety-net tests green covering frozen-reference, from_json round-trip on all 19 on-disk JSONs, enriched-format, and reproducibility. Full suite: 552 passed.
**Concerns:** Result-dataclass unification (ConGenResult/ConGenResultData/ConGenRunResult) deferred — frozen-format constraint makes safe unification non-trivial without a dedicated follow-up. EvaluationMetrics "single path" finding: clause-based path already routes through compute_metrics(); other 3 sites are different strategies, not duplicates.
