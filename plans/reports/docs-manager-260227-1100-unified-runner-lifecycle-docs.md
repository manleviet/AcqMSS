# Documentation Update: Unified Runner Lifecycle Refactoring

**Date**: 2026-02-27 10:00 UTC
**Task**: Update project documentation to reflect Unified Runner Lifecycle refactoring
**Scope**: docs/codebase-summary.md, docs/system-architecture.md
**Status**: COMPLETE

## Summary of Changes

The Unified Runner Lifecycle refactoring introduced a base class pattern for constraint acquisition runners with clean resource management. Documentation has been updated to reflect this new architecture.

## Changes Made

### 1. docs/codebase-summary.md

**Section**: conacq/runners/ — Execution Runners

**Updates**:
- Added new `base_runner.py` file to inventory (110 LOC)
- Updated file count: 3 files → 4 files
- Updated LOC estimate: ~446 → ~480 LOC
- Expanded section with detailed descriptions of new components:
  - **BaseRunner ABC**: Lifecycle pattern (build-once/run-many/cleanup-once)
  - **BaseRunResult**: 9 shared fields, dataclass inheritance structure
  - **ConGenRunner**: Details on inheritance and behavior
  - **InteractiveRunner**: Details on inheritance and behavior
- Documented oracle reuse across multiple runs (CV pattern)
- Added cleanup() method documentation and resource management pattern

**Verification**:
- File now at 565 lines (within limits)
- All runner classes documented with clear inheritance hierarchy
- Cross-references to oracle and examples consistent

### 2. docs/system-architecture.md

**Section 1**: conacq/runners/ — Execution Runners (NEW subsection)

**Added**:
- **Purpose**: Unified lifecycle for running constraint acquisition algorithms with resource management
- **Unified Lifecycle Pattern**: Code example showing build-once/run-many/cleanup-once lifecycle
- **BaseRunner ABC**: Methods and responsibilities
- **BaseRunResult**: 9 shared fields documented with types and purposes
- **ConGenRunner**: Inheritance and specific behavior
- **InteractiveRunner**: Inheritance and specific behavior
- **Re-export Pattern**: Documentation of backward-compatible re-exports via conacq.eval

**Section 2**: conacq/eval/ — Evaluation Framework (updated)

**Updates**:
- Moved "Runners" subsection content into new conacq/runners/ section
- Updated cross_validation.py description to note runner.cleanup() via try/finally
- Removed duplicate runner documentation (now in runners section)

**Section 3**: Performance Metrics (NEW subsection in "Performance Characteristics")

**Added**:
- **PerformanceMetrics.n_mss**: Documented Optional[int] = None change
- Explanation of ConGen vs Interactive behavior:
  - ConGen: Sets actual MSS count from ACQMSS
  - Interactive: None (no MSS concept)
- Rationale: Unified metrics while supporting ConGen-specific measurements

## Key Architectural Points Documented

### Lifecycle Pattern
```python
runner = ConGenRunner(bias_path, fm_path)      # __init__: build once, oracle created
try:
    result1 = runner.run(...)                  # run many (CV fold 1)
    result2 = runner.run(...)                  # oracle reused (CV fold 2)
finally:
    runner.cleanup()                           # cleanup once: release resources
```

### Shared Result Structure
- **BaseRunResult**: 9 fields inherited by ConGenRunResult and InteractiveRunResult
  - KB output: kb_constraints, kb_clauses, bg_clauses
  - Size metrics: n_bias, n_kb
  - Performance: runtime_ms, consistency_checks, memory_peak_mb
  - Profiling: profiler_data

### Resource Management
- Oracle created once in __init__, reused across multiple run() calls
- cv.py wrapper functions call runner.cleanup() via try/finally
- Enables safe multi-fold cross-validation without rebuilding runners

### Backward Compatibility
- BaseRunner and BaseRunResult exported from conacq/runners/__init__.py
- Re-exported from conacq/eval/__init__.py for backward compatibility
- No breaking changes to existing imports or APIs

## Files Updated

| File | Lines | Status | Changes |
|------|-------|--------|---------|
| docs/codebase-summary.md | 565 | Updated | +48 lines (runners section expanded) |
| docs/system-architecture.md | 897 | Updated | +41 lines (new runners section + metrics) |

## Verification Checklist

- [x] base_runner.py correctly documented (ABC + dataclass)
- [x] BaseRunResult 9 fields documented with types
- [x] ConGenRunner inheritance from BaseRunner documented
- [x] InteractiveRunner inheritance from BaseRunner documented
- [x] Lifecycle pattern (build-once/run-many/cleanup-once) clearly explained
- [x] Oracle reuse across CV folds documented
- [x] PerformanceMetrics.n_mss Optional change documented
- [x] Backward-compatible re-exports from conacq.eval documented
- [x] Cross-references consistent with actual code
- [x] File sizes within acceptable limits

## Documentation Quality

- **Accuracy**: 100% verified against actual codebase files
- **Clarity**: Clear inheritance hierarchy and lifecycle pattern
- **Completeness**: All new classes and methods documented
- **Organization**: Logical flow from base classes to concrete implementations
- **Examples**: Lifecycle pattern shown with concrete code example

## No Breaking Changes

The refactoring maintains full backward compatibility:
- All existing imports still work
- BaseRunner/BaseRunResult re-exported from conacq.eval
- No changes to public method signatures
- Runner subclasses inherit new functionality cleanly

## Related Commits

- 260227-1028-unified-runner-lifecycle: Implementation of BaseRunner ABC and BaseRunResult
- This documentation update: 260227-1100-unified-runner-lifecycle-docs

## Questions & Notes

None — all changes successfully documented based on actual code implementation.
