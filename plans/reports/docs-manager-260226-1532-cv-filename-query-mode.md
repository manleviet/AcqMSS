# Documentation Update: CV Filename query_mode Suffix

**Date**: 2026-02-26
**Scope**: Minor filename format documentation update
**Status**: Complete

## Summary

Updated documentation to reflect CV output filename format change in `run_cv.py` for interactive runs, which now includes the `query_mode` suffix.

## Change Details

**Code change**: `apps/run_cv.py` line 189 now generates filenames as:
- Interactive: `{model}_cv_{mode}_{query_mode}.json`
- Example: `REAL-FM-7_rs_1n_cv_non-incremental_example_only.json`

Previous format (non-interactive, still applies to ConGen):
- ConGen: `{model}_cv_{mode}.json`

## Files Updated

### 1. `/Users/manleviet/Development/GitHub/AcqMSS/docs/eval-pipeline.md`

**Line 148 (output directory structure)**
- Added explicit example for interactive algorithm showing the query_mode suffix
- Changed: `└── REAL-FM-7_rs_1n_cv_non-incremental.json`
- To: `└── REAL-FM-7_rs_1n_cv_non-incremental_example_only.json` (with explanatory comment)

### 2. `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md`

**Lines 375-377 (Unified CV JSON filename format)**
- Updated generic format description to clarify algorithm-specific patterns
- Added separate examples for ConGen vs Interactive
- Now shows: ConGen uses `{model}_{strategy}_{mode}_cv.json`, Interactive adds `_{query_mode}`

## Files NOT Updated

Checked all docs; no other files explicitly reference the CV filename format:
- `codebase-summary.md` — references scripts, not filename format
- `code-standards.md` — code conventions only
- `quacq.md` — algorithm docs, not filenames
- `congen.md` — algorithm docs, not filenames
- `project-overview-pdr.md` — feature list, not filenames
- `project-roadmap.md` — roadmap progress, not filenames
- `README.md` — already generic about file naming

## Testing

Pattern `*_cv_*.json` in `find_cv_files()` (system-architecture.md line 450) correctly handles both old and new formats via regex in `extract_results.py:parse_filename()`, so backward compatibility is maintained.

## Notes

- Change is minor and backward-compatible
- `parse_filename()` uses regex to handle both patterns
- No breaking changes to users; just documentation clarification
