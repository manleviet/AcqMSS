# Documentation Update Report: ConGen API Refactoring

**Date**: 2026-02-15
**Status**: COMPLETED

## Summary

Reviewed all documentation files for references to ConGen API changes from the DescriptionProvider removal refactoring. Found outdated parameter names and function signatures in 4 locations across 3 files.

## Changes Detected

### API Changes (Code)
- `CONGENResult` fields: ✓ Correct (removed `kb_constraints`, `redundant_constraints`; uses `kb_assumption_ids`, `redundant_ids`)
- `ConGen.acquire()` signature: **OUTDATED in docs**
  - Old params: `neg_c_map`, `assumption_to_constraint`
  - New params: `negation_map` (renamed), removed `assumption_to_constraint`
  - New param signature: `acquire(set_b, set_bg, set_tc, set_neg_tv, negation_map)`

### Documentation Issues

| File | Line(s) | Issue | Fix |
|------|---------|-------|-----|
| `CLAUDE.md` | 190-191 | Old param names in ConGen code example | Remove `assumption_to_constraint` param, rename `neg_c_map` to `negation_map` |
| `docs/system-architecture.md` | 71-78 | Old param names in ConGen code example | Same fix |
| `docs/system-architecture.md` | 234 | CONGENTask type definition references old field | Field name is correct; no update needed |
| `docs/code-standards.md` | 262-263, 294-295 | Old param names in ConGen code example | Same fix |

## Files Modified

1. `/Users/manleviet/Development/GitHub/AcqMSS/CLAUDE.md` (lines 185-192)
2. `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` (lines 71-78)
3. `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md` (lines 256-296)

## Implementation

Updated all three occurrences of the `congen.acquire()` call to use the correct new parameter names:
- Removed the `assumption_to_constraint` parameter entirely
- Renamed `neg_c_map` to `negation_map`
- Added comment clarifying the parameter maps negation relationships

## Verification

- All code examples now match the actual `ConGen.acquire()` signature from `acqmss/algorithms/congen.py`
- Type definitions remain accurate
- No breaking changes to other documented APIs

## Updates Applied

All parameter references corrected in:
1. **CLAUDE.md** (line 190) - Updated `congen.acquire()` call
2. **docs/system-architecture.md** (line 76) - Updated `congen.acquire()` call
3. **docs/code-standards.md** (lines 262, 290) - Updated method signature and call example

### Changes Made
- Renamed: `neg_c_map` → `negation_map` (parameter name in all 3 files)
- Removed: `assumption_to_constraint` parameter (no longer in API)
- Added: Clarifying comment on `negation_map` purpose

### Verification
- ✅ No remaining `assumption_to_constraint` references in docs
- ✅ All `negation_map` usages correct
- ✅ Code examples match actual API signature from `acqmss/algorithms/congen.py`

## Status

✅ COMPLETED. All documentation files synchronized with refactored ConGen API.

## Notes

- The `resolve_congen_names()` utility is correctly documented in codebase-summary.md
- No changes needed to architecture or design documentation
- All other API patterns remain unchanged
