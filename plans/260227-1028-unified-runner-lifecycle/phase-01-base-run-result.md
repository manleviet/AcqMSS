# Phase 01: Extract BaseRunResult Dataclass

## Context
- Parent: [plan.md](plan.md)
- Brainstorm: `plans/reports/brainstorm-260227-1028-unified-runner-lifecycle.md`

## Overview
- **Priority**: High (foundation for all other phases)
- **Status**: Complete
- **Progress**: 100%
- **Description**: Extract 9 shared fields from ConGenRunResult and InteractiveRunResult into BaseRunResult base dataclass

## Key Insights
- Both result classes share: `kb_constraints`, `kb_clauses`, `bg_clauses`, `n_bias`, `n_kb`, `runtime_ms`, `consistency_checks`, `memory_peak_mb`, `profiler_data`
- Both have `to_dict()` and `get_performance_metrics()` with overlapping logic
- Dataclass inheritance requires careful field ordering (defaults after non-defaults)

## Requirements
- BaseRunResult contains all 9 shared fields
- Shared `_base_to_dict()` helper for common serialization logic
- `get_performance_metrics()` on base class (subclasses may override)
- ConGenRunResult and InteractiveRunResult inherit BaseRunResult
- No change to external API (to_dict output must remain backward-compatible)

## Architecture

```
BaseRunResult (dataclass)
├── kb_constraints: List[str]
├── kb_clauses: List[List[int]]
├── bg_clauses: List[List[int]]
├── n_bias: int
├── n_kb: int
├── runtime_ms: float
├── consistency_checks: int
├── memory_peak_mb: float
├── profiler_data: Dict[str, Any] = {}
├── _base_to_dict() -> dict
└── get_performance_metrics() -> PerformanceMetrics

ConGenRunResult(BaseRunResult)
├── redundant_constraints, n_mss, 8 extended profiler metrics
├── to_dict() — calls _base_to_dict() + adds ConGen-specific fields
└── get_performance_metrics() — override with full ConGen metrics

InteractiveRunResult(BaseRunResult)
├── n_queries, convergence_reason, query_history
├── to_dict() — calls _base_to_dict() + adds interactive-specific fields
└── get_performance_metrics() — override with n_mss=None
```

## Related Code Files
- **Create**: `conacq/runners/base_runner.py` (BaseRunResult lives here)
- **Modify**: `conacq/runners/congen_runner.py` (inherit BaseRunResult)
- **Modify**: `conacq/runners/interactive_runner.py` (inherit BaseRunResult)
- **Modify**: `conacq/runners/__init__.py` (export BaseRunResult)

## Implementation Steps

1. Create `conacq/runners/base_runner.py` with `BaseRunResult` dataclass
2. Define 9 shared fields (required first, `profiler_data` with default last)
3. Implement `_base_to_dict()` returning shared dict structure
4. Implement base `get_performance_metrics()` returning PerformanceMetrics
5. Update `ConGenRunResult` to inherit `BaseRunResult`, remove duplicated fields
6. Update `InteractiveRunResult` to inherit `BaseRunResult`, remove duplicated fields
7. Handle dataclass inheritance field ordering: use approach where BaseRunResult has 8 required + 1 default field; child classes add their required fields before defaults using `__init__` override or `kw_only=True`
8. Update `__init__.py` exports

## Todo
- [x] Create base_runner.py with BaseRunResult
- [x] Update ConGenRunResult to inherit
- [x] Update InteractiveRunResult to inherit
- [x] Update __init__.py exports
- [x] Verify to_dict() output unchanged

## Completion Summary
- BaseRunResult dataclass created in conacq/runners/base_runner.py
- 9 shared fields extracted (kb_constraints, kb_clauses, bg_clauses, n_bias, n_kb, runtime_ms, consistency_checks, memory_peak_mb, profiler_data)
- Used kw_only=True to handle field ordering with defaults
- ConGenRunResult and InteractiveRunResult inherit BaseRunResult
- No changes to external API; to_dict() output remains backward-compatible
- All imports updated in __init__.py

## Success Criteria
- Both result classes inherit BaseRunResult
- `to_dict()` output is backward-compatible
- No field duplication between base and child classes

## Risk Assessment
- **Dataclass inheritance ordering**: Required fields in child can't follow default fields in parent. Solution: use `kw_only=True` on child class or restructure field ordering.
- **Serialization compatibility**: `to_dict()` output must not change. Verify with existing test assertions.

## Next Steps
- Phase 02 depends on this (PerformanceMetrics changes)
