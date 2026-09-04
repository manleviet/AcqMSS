---
phase: 5
title: A4 base runner profiling+metrics
status: completed
priority: P1
effort: 1-2d
dependencies:
  - 1
---

# Phase 5: A4 — BaseRunner profiling + metric-extraction

## Overview
Extract `BaseRunner._run_with_profiling(...)` + a declarative metric-extraction map; runners declare WHICH metrics, not HOW to pull them. Collapses 150+ near-identical lines (tracemalloc + profiler-session + checker lifecycle + ~30-line metric blocks) cloned ConGen↔QuAcq, incl. the duplicate `random.Random(shuffle_seed).shuffle(task.set_c)`.

## Safety-net FIRST (untested module)
`conacq/runners/*` has no direct tests. BEFORE refactoring, write characterization tests for `ConGenRunner` and `QuAcqRunner` (run on a small FM, assert result metrics + KB shape). Only then refactor.

## Requirements
- Functional: one profiling+lifecycle path; runners supply a metric-key declaration; identical metric outputs.
- Non-functional: conacq-side (`conacq/runners/`); shuffle dedup; no metric value drift.

## Architecture
- `BaseRunner` with `_run_with_profiling()` owning tracemalloc + profiler session + checker lifecycle + shuffle.
- Declarative metric map: `{key: extractor}` so adding a metric is one edit, not two.

## Related Code Files (verified)
- Create: `conacq/runners/base_runner.py` (or extend existing base)
- Modify: `conacq/runners/congen_runner.py` (boilerplate :60-165; shuffle :162), `conacq/runners/quacq_runner.py` (:95-290; shuffle :243; last_task note :179)
- Create: `tests/test_runners_*.py` (safety-net)

## Implementation Steps
1. Write safety-net tests for both runners; run green.
2. Extract `BaseRunner._run_with_profiling()` + metric map.
3. Re-point ConGen/QuAcq runners to the base; dedup shuffle; declare metric keys.
4. `PYTHONPATH=. pytest tests/ -v` → green (safety-net tests prove no metric drift).

## Success Criteria
- [ ] Safety-net runner tests exist and pass
- [ ] One profiling+lifecycle path; runners only declare metric keys
- [ ] `shuffle(task.set_c)` defined once
- [ ] No metric value drift vs safety-net baseline
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **Split the safety-net assertion policy** (timing metrics are non-deterministic): pin EXACT values for deterministic COUNT metrics (`consistency_checks`, `n_mss`, `n_kb`, `acqmss_calls`, …) + KB shape; for `runtime_ms`/`memory_peak_mb`/`solver_time_ms` assert presence + type ONLY. Pinning timing → flaky red → pressure to weaken the count assertions too. State this explicitly so non-pinnable metrics can't be used as cover.
- **Metric-map shape constraint for C2 handoff:** keep the map as `{key: extractor}` and do NOT bake `PerformanceMetrics` field names into its shape, so C2 can swap the sink to `RunMetrics` without reworking the map.

## Risk Assessment
- Silent metric drift is the key danger — the safety-net tests (written first) are the guard; assert concrete metric values, not just presence.
