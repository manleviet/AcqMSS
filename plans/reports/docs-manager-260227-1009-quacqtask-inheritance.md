# Documentation Update: QuAcqTask Inheritance Refactoring

**Date**: 2026-02-27 10:09
**Task**: Update documentation to reflect QuAcqTask inheritance from DiagnosisTask
**Work Context**: /Users/manleviet/Development/GitHub/AcqMSS
**Status**: COMPLETE

## Summary

Updated three key documentation files to reflect the QuAcqTask inheritance refactoring (commit 260227). QuAcqTask now properly inherits from DiagnosisTask, eliminating duplicate field definitions and establishing a clear task hierarchy.

## Changes Made

### 1. system-architecture.md

**Section**: "explanation/models/ — Diagnosis Models"

**Updates**:
- Restructured task class documentation to show inheritance hierarchy:
  - `DiagnosisTask` (base) with shared fields: `assumptions`, `set_kb`, `set_b`, `set_c`, `negation_map`
  - `TestCaseTask(DiagnosisTask)` for test case scenarios
  - `ConGenTask(TestCaseTask)` for passive learning
  - `QuAcqTask(DiagnosisTask)` for interactive learning (NEW parallel hierarchy)

- Updated QuAcq flow diagram to clarify field inheritance:
  - Inherited fields from DiagnosisTask listed explicitly
  - `set_b` field correctly identified as inherited BG assumption IDs
  - `background_clauses` documented as interactive-specific raw BG CNF
  - Removed outdated "background" field reference

- Refined "Key Changes" section:
  - Renamed from "Bug Fix" to "Inheritance Refactoring"
  - Explained inheritance benefits: eliminates duplicates, establishes single source of truth
  - Clarified field semantics: `set_b` (IDs) vs `background_clauses` (raw CNF)

**Lines Affected**: ~20 updates across task hierarchy and QuAcq flow sections

### 2. codebase-summary.md

**Section**: "Interactive Sub-package (`interactive/`, 11 files, ~2,300 LOC)"

**Updates**:
- Updated `quacq_task.py` description: changed from "parallel to ConGenTask, now with background_clauses field" to "inherits from DiagnosisTask, adds interactive-specific fields"

**Section**: "Recent Changes (QuAcqTask Inheritance Refactoring - commit 260227)"

**Updates**:
- Completely rewrote "Recent Changes" section (renamed from "BG Assumption Bug Fix")
- Added detailed task hierarchy explanation:
  - DiagnosisTask → base class with shared fields
  - TestCaseTask(DiagnosisTask) → adds `set_tc`, `set_tv`
  - ConGenTask(TestCaseTask) → adds `set_neg_tv`
  - QuAcqTask(DiagnosisTask) → inherits from DiagnosisTask, adds interactive fields
- Listed explicit benefits:
  - Eliminates duplicate field definitions
  - Clear inheritance hierarchy
  - QuAcqTask focused on interactive-specific state
  - Consistent field naming
- Documented shared duck-typing helpers in `_task_compat.py`

**Lines Affected**: Replaced ~20 lines with refined explanation

### 3. quacq.md

**Section**: "Assumption ID Architecture (Current)"

**Updates**:
- Expanded task class descriptions with full field details:
  - Inherited vs. interactive-specific fields clearly marked
  - Full documentation of: `bias`, `learned_kb`, `background_clauses`, `constraint_clauses`, `negated_clauses`, `feature_ids`, `id_to_feature`

- Added new "Inheritance Pattern (Refactored)" subsection:
  - DiagnosisTask (Base) — inherited common fields
  - QuAcqTask(DiagnosisTask) (Derived) — interactive-specific additions
  - Complete field listing with types and purposes

- Added "Field Semantics (Consistent with ConGen)" subsection:
  - Clarified `set_b: List[int]` as inherited BG assumption IDs
  - Explained `background_clauses: List[List[int]]` as raw CNF for violation detection
  - Documented fix: correct interpretation of assumptions vs. clause structures

**Lines Affected**: ~35 new lines added to improve clarity

## Key Documentation Improvements

1. **Clear Inheritance Hierarchy**: All task classes now explicitly show inheritance relationships
2. **Single Source of Truth**: DiagnosisTask fields no longer duplicated in subclasses
3. **Field Semantics**: Consistent naming convention across ConGen and QuAcq (set_b for IDs)
4. **Interactive-Specific Fields**: QuAcqTask clearly distinguishes inherited vs. added fields
5. **Bug Fix Context**: Documentation explains dual storage pattern for correctness

## Verification

**Files Updated**: 3
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` — Task hierarchy + QuAcq flow
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` — Code descriptions + recent changes
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/quacq.md` — Assumption architecture + field semantics

**No External Links Changed**: All cross-references within docs/ verified as valid

**Code References Verified**:
- QuAcqTask class definition in `conacq/algorithms/interactive/quacq_task.py`
- DiagnosisTask inheritance confirmed via `explanation/models/task_preparation.py`
- Duck-typing helpers in `conacq/algorithms/interactive/_task_compat.py`

## Backward Compatibility

All documentation updates are **backward compatible**:
- Deprecated classes still documented (InteractiveTask, InteractiveLearner)
- New architecture explains migration path
- Existing code examples remain valid (minor field name clarifications only)

## Unresolved Questions

None. All task inheritance changes reflected in documentation; all cross-references verified.
