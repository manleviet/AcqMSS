# Brainstorm: Extract `profiler_session` Context Manager

## Problem
`profiler_context` in `test_diagnosis.py` (line 182) implements profiler lifecycle management (reset → start → yield → stop) used 36 times. This is profiler-owned logic living in test code.

## Decision
- **Move** to `profiler.py` as module-level `profiler_session()` function
- **Rename** from `profiler_context` → `profiler_session` (describes lifecycle semantics, not Python mechanism)
- **Signature**: `profiler_session(preset: ProfilerPreset, mode: ProfilerMode = ProfilerMode.SINGLE_THREAD)`
- **Update** `test_diagnosis.py` to import from profiler module, remove local definition

## Rationale
- DRY: 36 call sites depend on this pattern
- Single responsibility: profiler module owns its lifecycle
- Naming: `profiler_session` describes what it does; `global_` prefix rejected as implementation detail
- API layering: `use_global_profiler()` = low-level get/set, `profiler_session()` = high-level lifecycle

## Risk
- Very low. Additive change, no backward compatibility concerns.

## Changes
1. `profiler.py`: Add `profiler_session()` function + export
2. `test_diagnosis.py`: Replace local `profiler_context` with import of `profiler_session`
