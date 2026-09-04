# Documentation Update: Oracle Package Extraction

**Date**: 2026-02-13
**Task**: Update project documentation to reflect oracle package extraction
**Status**: Complete

## Summary

Updated three documentation files to reflect the relocation of oracle classes from `acqmss/testcases/oracle.py` and `acqmss/algorithms/interactive/user_interface.py` into the new `acqmss/oracle/` package.

## Changes Made

### 1. docs/codebase-summary.md

**Updated sections:**

#### Interactive Sub-package (line 25)
- Removed `user_interface.py` (293 LOC) from `interactive/` sub-package listing
- Updated file count from 8 to 7 files
- Updated LOC from ~2,045 to ~1,750 (reflects removed user_interface.py)

#### acqmss/testcases/ section (line 49-66)
- Removed `oracle.py` (326 LOC) from testcases file listing
- Updated file count from 8 to 5 files
- Updated LOC from ~1,600 to ~1,370
- Added new **Oracle Sub-package** section documenting the extracted package:
  - `acqmss/oracle/oracle.py` (326 LOC) - Oracle, FeatureModelOracle abstract and FM-based validators
  - `acqmss/oracle/interactive.py` (293 LOC) - InteractiveOracle, AutomatedOracle, UserPromptOracle, CachedOracle, ExampleProvider

#### Critical Implementation Details (line 70)
- Updated reference from generic "The Oracle's" to specific `FeatureModelOracle`'s _build_feature_ids() method
- Added full path: `acqmss/oracle/oracle.py`
- Clarified that FmToPysat integration is in this module

### 2. docs/system-architecture.md

**Updated section:**

#### Feature ID Consistency (CRITICAL) - line 680
- Changed: `Oracle (acqmss/testcases/oracle.py)` → `Oracle (acqmss/oracle/oracle.py)`
- Maintains all other context and technical details

### 3. docs/quacq.md

**Updated section:**

#### Relation to Codebase - Core Implementation (line 82-88)
- Replaced: `acqmss/algorithms/interactive/user_interface.py` — Oracle + ExampleProvider interfaces
- With two separate entries reflecting new package structure:
  - `acqmss/oracle/oracle.py` — Oracle, FeatureModelOracle base classes
  - `acqmss/oracle/interactive.py` — InteractiveOracle, AutomatedOracle, UserPromptOracle, ExampleProvider

## Canonical Import Pattern

Documentation now correctly reflects the canonical import pattern from the new package:

```python
from conacq.oracle import (
    Oracle,
    FeatureModelOracle,
    InteractiveOracle,
    AutomatedOracle,
    UserPromptOracle,
    CachedOracle,
    ExampleProvider,
)
```

## Verification

- Scanned all doc files (*.md) for references to old import paths
- No remaining references to:
  - `acqmss.testcases.oracle`
  - `acqmss.algorithms.interactive.user_interface`
  - Old class import locations
- All references updated to point to new `acqmss/oracle/` package paths

## Files Updated

1. `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` — 3 sections
2. `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` — 1 reference
3. `/Users/manleviet/Development/GitHub/AcqMSS/docs/quacq.md` — 1 section

**Total**: 5 changes across 3 files

## Notes

- Changes are minimal and focused on import path updates
- No functional or conceptual changes to documentation
- Maintained all technical details and accuracy
- Updated stats reflect actual file reorganization (LOC adjustments for testcases and interactive sub-packages)
