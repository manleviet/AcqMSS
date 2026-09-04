# Documentation Update: Oracle BG Data Extraction

**Date**: 2026-02-18
**Changes Reviewed**: BG data extraction refactoring

## Summary

Oracle BG data extraction refactoring introduces a new `BGData` frozen dataclass and extraction API. Documentation updated to reflect these changes across oracle package structure and FMOracleModel capabilities.

## Changes Made

### 1. codebase-summary.md (lines 65-77)

**Oracle Sub-package Update**:
- Incremented file count: 9 → 10 files
- Updated LOC: ~929 → ~998
- Added entry: `bg_data.py` (27 LOC) — BGData frozen dataclass for root BG constraint + negation pair
- Updated `fm_oracle_model.py` description (268 → 280+ LOC) to document `bg_data` property and `get_bg_data()` method

**Critical Implementation Details** (line 90):
- Enhanced FMOracleModel description to explicitly mention `bg_data` property exposure and `get_bg_data()` method for ConGen

**Recent Changes Section** (lines 369-379):
- Enhanced ConGenTaskPreparation description: Added note that `_prepare_bg()` method has been refactored
- **NEW**: BG Data Extraction subsection documenting:
  - BGData dataclass fields: `set_kb`, `assumptions`, `negation_map`, `descriptions`, `next_available_id`
  - Extraction via `FMOracleModel.bg_data` property (lazy-computed) and `get_bg_data()` method
  - ConGenTaskPreparation integration: Calls `oracle.get_bg_data()` post-preparation
  - Assumption ID layout separation: Oracle owns Parts 1-4; ConGen allocates from `next_available_id`

### 2. system-architecture.md (lines 202-230)

**Key Classes Section** (Oracle ABC documentation):
- Inserted new entry: **BGData** (3) — Immutable dataclass for root BG constraint extraction
  - Documents all fields: `set_kb`, `assumptions` tuple, `negation_map`, `descriptions`, `next_available_id`
  - Extraction interface: `FMOracleModel.bg_data` property and `get_bg_data()` method
  - Use case: Enables ConGen clean assumption ID allocation

- Renumbered subsequent classes: FMOracleModel (4), UserPromptOracle (5), CachedOracle (6), OracleData (7)
- Enhanced FMOracleModel (4) description:
  - Added: "Exposes `bg_data` property (lazy-computed) and `get_bg_data()` method"
  - Added: "Internal: Uses `_assignments_index` to track feature assignment assumption boundary"

## Verification

**File sizes (within 800 LOC limit)**:
- codebase-summary.md: 450 LOC ✓
- system-architecture.md: 606 LOC ✓

**Documentation accuracy**:
- `bg_data.py`: 27 LOC verified ✓
- `conacq/oracle/`: 10 files verified ✓
- `oracle/ total`: ~998 LOC verified ✓
- FMOracleModel methods verified: `bg_data` property, `get_bg_data()` present ✓
- ConGenTaskPreparation verified: Calls `oracle.get_bg_data()` at line 89 ✓
- `_prepare_bg()` verified removed from ConGenTaskPreparation ✓
- `_start_id_assignments` verified renamed to `_assignments_index` ✓

## Impact Assessment

**Substantive changes**: Yes
- New public API in FMOracleModel (`bg_data` property + `get_bg_data()` method)
- New dataclass in oracle package
- Refactored ConGenTaskPreparation to use BG data extraction instead of `_prepare_bg()`
- Updated assumption ID layout documentation

**No breaking documentation changes** — only clarifications and additions reflecting actual implementation refactoring.

## Unresolved Questions

None. All changes substantively documented and verified against codebase.
