# Documentation Review: Python -m Invocation Pattern Refactoring

**Date**: 2026-02-25
**Subagent**: docs-manager
**Context**: AcqMSS project refactored from `PYTHONPATH=. python apps/X.py` to `python -m apps.X` pattern

## Summary

Documentation successfully updated to reflect the new `python -m` invocation pattern. Only one minor addition was needed to inventory files.

## Changes Made

### docs/codebase-summary.md

**Updated**: apps/ section file inventory

- **Before**: Listed 10 files in apps/ section; `__init__.py` not mentioned
- **After**:
  - Updated file count from 10 → 11 files
  - Added `__init__.py` with note "(enables python -m invocation)"
  - Added header note: "Uses `python -m apps.X` invocation pattern"
  - All code examples already use correct `python -m apps.X` pattern (verified via grep)

### docs/system-architecture.md

**Status**: No changes needed

- No references to app invocation patterns found
- Architecture diagrams correctly show abstract API calls

### docs/project-roadmap.md

**Status**: No changes needed

- Test commands still use `PYTHONPATH=. pytest tests/` (correct)
- No app-specific invocation patterns documented

## Verification Completed

✅ **Stale pattern search**: 0 occurrences of old `PYTHONPATH=. python apps/` in docs/
✅ **Code examples**: All already use `python -m apps.X` pattern
✅ **File inventory**: `apps/__init__.py` now documented in codebase-summary.md
✅ **Cross-links**: No broken references; imports use `conacq.*` package name (not acqmss)

## Files Inspected

1. `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` — Updated
2. `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` — No changes needed
3. `/Users/manleviet/Development/GitHub/AcqMSS/docs/project-roadmap.md` — No changes needed

## Documentation Consistency Status

| Document | Invocation Pattern | Status |
|----------|-------------------|--------|
| codebase-summary.md | `python -m apps.X` | ✅ Current |
| system-architecture.md | N/A (architecture docs) | ✅ N/A |
| project-roadmap.md | N/A (roadmap/metrics) | ✅ N/A |
| README.md | Already updated in refactoring | ✅ External |
| CLAUDE.md | Already updated in refactoring | ✅ External |

## Unresolved Questions

None. Documentation is current and consistent with codebase implementation.

## Next Steps

None required for this task. All documentation reflects current `python -m` invocation pattern.
