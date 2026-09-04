# Docs Update: ConGen Pipeline Simplification

**Date**: 2026-02-18
**Agent**: docs-manager

## Summary

Updated four docs to reflect ConGen pipeline simplification: removal of `evaluate_congen_results.py` + `evaluate_congen_config.toml`, `run_congen_eval.py` reduced to CV-only, `extract_results.py` DRY-refactored with fold metrics.

## Files Modified

### `docs/codebase-summary.md`
- Removed `evaluate_congen_results.py` from apps table (was 524 LOC)
- Updated apps count: 9 → 8 files, ~3,702 → ~3,100 LOC, stats row updated
- Updated `extract_results.py` LOC: 1,013 → 621 with note on DRY refactor and fold metrics
- Updated `run_congen_eval.py` description: CV-only, removed Option 1 mention
- Config files count: 8 → 7 TOML files (`evaluate_congen_config.toml` removed)
- Added pipeline note to Main Applications section
- Updated shell examples: reordered to show CV as primary path, extract_results as final step
- Updated File Size Analysis entry for `extract_results.py`

### `docs/project-roadmap.md`
- Phase 4 completed list: removed `evaluate_congen_results.py`, updated `run_congen_eval.py` + `extract_results.py` descriptions, TOML count 8 → 7
- Phase 6 completed list: added pipeline simplification bullet
- Current Metrics table: apps 9 → 8 files, ~3,300 → ~3,100 LOC

### `docs/system-architecture.md`
- Application layer ASCII diagram: added `extract_results.py`, labeled `run_congen_eval.py` as CV-only
- App listing in Two-Layer Architecture section: added `extract_results.py`, labeled `run_congen.py` and `run_congen_eval.py`

### `docs/project-overview-pdr.md`
- Two-Layer Architecture app listing: added `extract_results.py`, annotated `run_congen.py` (dev/debug) and `run_congen_eval.py` (CV only)

## Pipeline Change Documented

| | Old | New |
|---|---|---|
| Step 1 | `run_congen` → result file | `run_congen_eval` (CV) |
| Step 2 | `run_congen_eval` (Option 1 or CV) | `extract_results` (reports + fold metrics) |
| Step 3 | `evaluate_congen_results` (deleted) | — |
| Step 4 | `extract_results` | — |

## No Unresolved Questions
