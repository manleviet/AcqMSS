# Documentation Update Report: A+B+C Redesign

**Date**: 2026-06-21  
**Branch**: feat/redesign-abc  
**Scope**: DOCS ONLY — reflect completed 18-stage architecture redesign  

## Files Updated

| File | Changes | Status |
|------|---------|--------|
| `docs/system-architecture.md` | Added explanation.api boundary section; added profiler package architecture; added SolverBackend port section; updated last-modified date | ✅ |
| `docs/codebase-summary.md` | Updated metrics (23K LOC, 115 files); B3 Oracle contract revised (4 abstract methods); file counts adjusted for redesign | ✅ |
| `docs/code-standards.md` | Updated last-modified date; added A+B+C redesign marker; rewrote Testing Strategy section to reflect pytest standardization + conftest.py + resource_paths.py; added Boundary Guard Rule section (B1 enforcement) | ✅ |
| `README.md` | Fixed ConGen example to use new API (.with_oracle() required; no last_task); fixed QuAcq example to show task-centric DI pattern; updated Project Structure to list profiler/, solver_backend.py, conftest.py, scripts/ | ✅ |
| `docs/project-roadmap.md` | Updated last-modified date to 2026-06-21; added Phase A+B+C section documenting all 18 stages, tier breakdown (A/B/C), key achievements, metrics, locked decisions | ✅ |

## Verification Against Code

**explanation/api.py __all__ verified**: All exported symbols match code:
- Task types ✅ (Task, DiagnosisTask, TestCaseTask, TaskInput, ModelProtocol, slice_assumptions)
- Profiler exports ✅ (Profiler, ProfilerProtocol, AbstractProfiler, measure_time, count_calls, get_global_profiler, profiler_session, ProfilerPreset)
- SolverBackend ✅ (Protocol import confirmed in api.py:89)
- Operation registry ✅ (get_operation_class, create_operation, registered_keys exports)

**Profiler package structure verified**:
- explanation/operations/algorithms/profiler/ exists ✅
- Submodules: protocol.py, core.py, decorators.py, registry.py, presets.py ✅

**Oracle contract verified**:
- conacq/oracle/base.py defines 4 abstract methods (is_valid, get_variables, complete_configuration, get_bg_data) ✅
- FeatureModelOracle/UserPromptOracle/CachedOracle all implement Oracle ABC ✅

**Builder.last_task removal verified**:
- ConGenModelBuilder.with_oracle() now called explicitly ✅
- No builder.last_task pattern in codebase ✅
- prepare_task(task_input, oracle) is the API ✅

**Boundary guard test exists**:
- tests/test_boundary_guard.py confirmed ✅

**pytest infrastructure verified**:
- tests/conftest.py exists ✅
- tests/resource_paths.py exists ✅
- pytest.mark.slow in pyproject.toml ✅

## Unverified Claims (flags)

None — all major architectural claims verified against live code on feat/redesign-abc.

## Token Efficiency

- Focused on essential files (5 doc files updated)
- Verified claims via targeted code inspection (no exhaustive scan)
- Concise descriptions per user style preference

## No Commits Made

Docs updated per instructions; no git commits (user to handle after review).

---

**Status**: Complete. All 5 doc files updated to reflect A+B+C redesign completion. Ready for review + PR merge.
