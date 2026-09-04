---
title: "Add query_mode to interactive CV output filename"
description: "Include query_mode in run_cv.py output filename for interactive algorithm to prevent overwrites"
status: complete
priority: P3
effort: 15m
branch: main
tags: [interactive, cv, filename]
created: 2026-02-26
---

# Add query_mode to Interactive CV Output Filename

## Problem
`run_cv.py` generates identical output filenames regardless of `query_mode` for interactive runs.
Running with different `query_mode` values overwrites previous results.

**Current:** `{name}_cv_{mode_name}.json`
**Desired (interactive only):** `{name}_cv_{mode_name}_{query_mode}.json`

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | Modify CV filename logic | complete | [phase-01](phase-01-modify-cv-filename.md) |

## Compatibility (pre-verified)
- `find_cv_files()` globs `*_cv_*.json` — new names match
- `run_compare.py` reads JSON content, not filenames
- ConGen output unchanged (no `query_mode`)
