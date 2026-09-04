---
phase: 8
title: B2 profiler protocol + physical split
status: completed
priority: P1
effort: 2d
dependencies:
  - 1
  - 7
---

# Phase 8: B2 — Profiler Protocol + physical split

## Overview
`profiler.py` is 1150 LOC, 34 import sites, ≥6 concerns. Introduce a `Profiler` Protocol (`record`/`increment`/`timer`/`snapshot`) as the dependency type everywhere, AND physically split the implementation into submodules. (Both, per decision — was open-question Q3, resolved: physical split now since C is in scope.) Do BEFORE B1 so the public surface exports the Protocol, not the module.

## Safety-net
`tests/test_profiler.py` exists (good). Before splitting, ensure it covers the public behaviors being moved; add cases for any concern lacking coverage (CSV export, registry, timer). Note: hardcoded `/tmp/profiler_test.csv` :413 → move to tmp_path fixture.

## Requirements
- Functional: a `Profiler` Protocol; all consumers typed against it; implementation behind the Protocol split into `metrics-core` / `reporting` / `multiprocessing` / `registry`.
- Non-functional: Protocol is a type, not a wrapper object (no per-call allocation on hot path); framework-isolated.

## Architecture
- `explanation/operations/algorithms/profiler/` package: `protocol.py` (Protocol), `core.py` (counter/timer/gauge stores + lifecycle), `reporting.py` (CSV + console), `registry.py` (singleton/global registry), `multiprocessing.py` (mp semantics), `__init__.py` re-export.
- Consumers import the Protocol type; the concrete profiler stays the default implementation.

## Related Code Files (verified)
- Split: `explanation/operations/algorithms/profiler.py` (1150 LOC) → package
- Modify: 34 import sites across apps/conacq/explanation (re-point to Protocol type / new package path)
- Modify: `tests/test_profiler.py` (tmp_path fixture; concern coverage)

## Implementation Steps
1. Strengthen test_profiler coverage; fix the /tmp path to tmp_path.
2. Define `Profiler` Protocol; extract submodules one concern at a time, re-running suite after each.
3. Re-point import sites to Protocol type + new paths.
4. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] `Profiler` Protocol exists; consumers typed against it
- [ ] profiler split into ≥4 submodules; no single 1150-LOC file
- [ ] 34 import sites re-pointed; suite green
- [ ] test_profiler uses tmp_path; covers core/reporting/registry
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **Hard re-export success criterion (green-gate):** `profiler/__init__.py` must re-export EVERY symbol imported across the 34 sites + 4 test files — `get_global_profiler`, `use_global_profiler`, `profiler_session`, `ProfilerPreset`, `AbstractProfiler`, `measure_time`, `count_calls`, … Grep the old import surface; assert each still resolves at this stage's end.
- **Profiler vs AbstractProfiler naming:** if the public Protocol is named `Profiler`, KEEP `AbstractProfiler` (live import at `fm_oracle.py:18`) re-exported until B1 redirects it to the surface.
- **test_diagnosis (SEQ-1):** update its profiler imports (`tests/test_diagnosis.py:34`) in-stage if the split moves them.

## Risk Assessment
- Wide blast radius (34 sites) → split incrementally, keep `__init__` re-exports stable until B1 redirects them to the surface.
- Hot-path allocation regression → verify the Protocol stays a typing construct, no wrapper instances per call.
