# Planner Report: Unified CV Output JSON

**Date**: 2026-02-26
**Plan**: `plans/260226-1254-unified-cv-output/`

## Summary

Created 5-phase implementation plan to consolidate the CV pipeline output from 45+ files per model into a single unified JSON file per (model x strategy x mode).

## Current State (Problem)

- `run_cv.py` outputs: 1 CV summary + N fold KB JSONs + 1 intersected KB JSON
- `run_compare.py` adds: N fold eval JSONs + 1 intersected eval JSON
- For 6 strategies x 3 folds x 1 mode = ~54 files for one model
- `extract_results.py` must discover and merge separate eval files

## Plan (5 Phases, ~6h)

1. **Phase 1: Enrich CV Result** (1.5h) — Add `generate_unified_cv_dict()` to report.py, `ConGenResultData.from_dict()`, `ComparationResult.to_enriched_dict()`. Remove `save_cv_kb_files()`.

2. **Phase 2: Refactor run_cv.py** (1h) — Load Bias once per model, output single unified JSON with fold data, intersected KB, and eval placeholders.

3. **Phase 3: Refactor run_compare.py** (2h) — Read unified JSONs, compare each fold + intersected KB, write evaluation back, compute summary metrics. Add `find_cv_files()` to config.py.

4. **Phase 4: Update extract_results.py** (1h) — Read embedded evaluation from unified JSON. Fall back to separate eval files for backward compat.

5. **Phase 5: Tests and Cleanup** (0.5h) — Verify all tests pass, add targeted tests for new functions, integration smoke test.

## Key Design Decisions

- **Bias resolved at serialization time** (not stored in dataclass) — avoids threading Bias through CV loop
- **Idempotent run_compare** — re-running overwrites evaluation fields in same file
- **Backward compatible** — `ConGenResultData.from_dict()` handles both enriched `[{id, description}]` and legacy `["c1"]` formats; `extract_results.py` falls back to separate eval files
- **CLI mode preserved** — `run_compare --kb` still works for single-file comparison

## Files Modified (9 files)

| File | Change |
|------|--------|
| `conacq/eval/report.py` | Add `generate_unified_cv_dict()`, remove `save_cv_kb_files()` |
| `conacq/eval/result_loader.py` | Add `from_dict()` classmethod |
| `conacq/eval/kb_comparator.py` | Add `to_enriched_dict()` method |
| `conacq/eval/config.py` | Add `find_cv_files()` |
| `conacq/eval/__init__.py` | Update exports |
| `apps/run_cv.py` | Single unified JSON output |
| `apps/run_compare.py` | Read/enrich unified JSON |
| `apps/extract_results.py` | Read embedded evaluation |
| `tests/` | New tests for added functions |

## Output File Reduction

Before: ~54 files per model (6 strategies x 3 folds x 1 mode)
After: 6 files per model (1 per strategy x mode)
