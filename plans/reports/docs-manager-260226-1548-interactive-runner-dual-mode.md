# Documentation Update: InteractiveRunner Dual-Mode Refactoring

**Report Date**: 2026-02-26 14:48 UTC
**Work Context**: /Users/manleviet/Development/GitHub/AcqMSS
**Status**: ✅ COMPLETE — All docs updated and verified

## Summary

Documentation review and update for the InteractiveRunner dual-mode refactoring introduced in the recent CV pipeline enhancement.

### Changes Made

**Scope**: API signature changes affecting documentation references to `InteractiveRunner` and `n_fold_cross_validation_interactive()` functions.

#### API Changes

1. **InteractiveRunner Constructor**
   - Old: `InteractiveRunner(bias_clauses, feature_ids, fm_path, bias_path, ...)`
   - New: `InteractiveRunner(bias_path, fm_path, ...)`
   - **Impact**: Now file-path-based, matching `ConGenRunner` pattern; constructor loads bias internally

2. **InteractiveRunResult Fields**
   - Added: `bg_clauses` — background knowledge clauses
   - Added: `profiler_data` — full profiler snapshot
   - **Impact**: Enhanced result structure with metrics collection

3. **n_fold_cross_validation_interactive() Signature**
   - Removed params: `bias_clauses`, `feature_ids`
   - New params: (unchanged) receives `positive_examples`, `negative_examples`, `fm_path`, `bias_path`, etc.
   - **Impact**: Cleaner API — bias loading handled internally

4. **run_interactive.py Execution**
   - Old: Direct `InteractiveLearner` instantiation
   - New: Uses `InteractiveRunner(bias_path, fm_path, ...).run(mode=...)`
   - **Impact**: Unified runner interface for both CONGEN and Interactive paths

#### Documentation Files Updated

| File | Changes | Status |
|------|---------|--------|
| `docs/system-architecture.md` | Updated QuAcq section with file-path constructor + dual-mode `.run()` pattern | ✅ Updated |
| `docs/eval-pipeline.md` | Updated table showing `InteractiveRunner(bias_path, fm_path, ...)` + `.run()` call signature | ✅ Updated |
| `docs/codebase-summary.md` | No changes needed — already accurate (LOC counts, purpose descriptions correct) | ✅ Verified |
| `docs/code-standards.md` | No changes needed — design pattern docs remain valid | ✅ Verified |
| `docs/project-roadmap.md` | No changes needed — "Runners package move" summary still accurate | ✅ Verified |
| `README.md` | No changes needed — package structure listing already correct | ✅ Verified |

#### Files NOT Updated

- `docs/quacq.md` — No InteractiveRunner references
- `docs/congen.md` — ConGen-specific, no changes
- `docs/project-overview-pdr.md` — High-level goals, API-agnostic

### Verification Results

**Reference Search**: Scanned all docs for `InteractiveRunner`, `n_fold_cross_validation_interactive`, `bias_clauses`, `feature_ids` patterns.

**Critical Findings**:
- ✅ No obsolete method signatures found
- ✅ All API references point to correct new signatures
- ✅ bg_clauses + profiler_data fields documented in `InteractiveRunResult`
- ✅ Dual-mode pattern (oracle vs example) clearly explained in pipeline docs

### Key Documentation Points

1. **File-Path Constructor**: Both `ConGenRunner` and `InteractiveRunner` now follow consistent pattern
   ```
   runner = InteractiveRunner(bias_path=str, fm_path=str, solver_name=str, ...)
   ```

2. **Dual-Mode run() Method**: Dispatcher handles mode-based routing
   - Oracle modes: `'automated'`, `'interactive'` → via `from_files()`
   - Example modes: `'example_only'`, `'example_first'` → via `from_examples()`

3. **Result Enhancement**: `InteractiveRunResult` now carries:
   - `bg_clauses` — root constraint for analysis
   - `profiler_data` — full execution metrics
   - Performance fields (runtime, consistency checks, memory)

4. **CV Integration**: `n_fold_cross_validation_interactive()` orchestrates per-fold runs via `InteractiveRunner.run()`

### Size Compliance

All affected docs remain under 800 LOC limit:
- `system-architecture.md` — 712 LOC ✅
- `eval-pipeline.md` — 347 LOC ✅
- `codebase-summary.md` — 467 LOC ✅

### Accuracy Verification

- ✅ Constructor signature verified against `/conacq/runners/interactive_runner.py` (lines 91-98)
- ✅ Result fields verified against `InteractiveRunResult` dataclass (lines 21-49)
- ✅ Dual-mode dispatch verified against `run()` method (lines 121-229)
- ✅ CV function signature verified against `cross_validation.py`

## Unresolved Questions

None. All API changes identified and documented. No breaking changes to public interfaces beyond the deliberate refactoring.

## Recommendations

1. **Future Updates**: When `InteractiveRunner` receives new parameters (e.g., timeout, max_queries), update the constructor documentation with default values.
2. **Example Code**: Consider adding code example in `README.md` showing both oracle and example modes of `InteractiveRunner`.
3. **Migration Guide**: Document migration path for any external code using old API (unlikely given research codebase, but good practice).

---

**Completed by**: docs-manager
**Verification**: All docs cross-checked with implementation
**Ready for**: Next phase or release
