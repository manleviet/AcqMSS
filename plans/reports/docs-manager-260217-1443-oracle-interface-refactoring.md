# Documentation Update: Oracle Interface Refactoring

**Date**: 2026-02-17
**Updated by**: docs-manager
**Scope**: Oracle ABC slimming, FMData introduction, example generator refactoring
**Commits Covered**: c978d66 (oracle interface refactor)

---

## Executive Summary

Updated project documentation to reflect the oracle interface refactoring that simplifies the Oracle ABC to a minimal membership query interface while decoupling FM metadata via a new FMData dataclass. Key changes emphasize separation of concerns, reduced coupling, and explicit metadata passing over oracle dependency.

**Files Updated**:
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md`
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md`
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md`

---

## Changes Made

### 1. system-architecture.md

**acqmss/oracle/ Section - Complete Rewrite**:
- Replaced entire Oracle section with detailed architecture explanation
- **Oracle ABC**: Now documents minimal interface (only `is_valid()` abstract, `ask()` concrete)
- **FMData**: New subsection explaining frozen dataclass for FM metadata
- **FeatureModelOracle**: Extended with all FM-specific methods (get_fm_data, get_features, complete_configuration, etc.)
- **FMOracleModel**: Clarified assumption-guarded clause architecture
- **UserPromptOracle & CachedOracle**: Updated with new behavior (no FM-specific methods required)
- **Architecture Notes**: Added design principles section

**Date Updated**: 2026-02-17

---

### 2. code-standards.md

**Oracle Module Conventions Section - Complete Rewrite**:
- Replaced with comprehensive oracle usage guide
- **Oracle ABC**: Minimal interface with code example
- **FMData Dataclass**: Explained as immutable metadata container
- **Architecture**: 5-part breakdown (FeatureModelOracle, FMOracleModel, UserPromptOracle, CachedOracle, OracleData)
- **Design Principles**: Listed 4 key principles

**Code Examples**: Added comprehensive oracle usage patterns showing FMData snapshot creation and complete_configuration() usage

**Date Updated**: 2026-02-17

---

### 3. codebase-summary.md

**Oracle Sub-package Table - Updated**:
- Added `fm_data.py` with 25 LOC (FMData dataclass)
- Updated `fm_oracle.py` LOC from 144 to 200+ (extended methods)
- Total oracle package expanded to 9 files, ~1,000 LOC

**Critical Implementation Details - Expanded from 7 to 11 points**:
- New details on FMData decoupling pattern
- Example generator refactoring patterns
- InteractiveLearner and ConGenTaskPreparation signature changes

**Recent Changes Section - Significantly Expanded**:
- Detailed what changed in Oracle ABC, FMData, FeatureModelOracle
- Listed example generator refactoring patterns
- Documented method signature changes across components

**Date Updated**: 2026-02-17

---

## Architecture Principles Documented

### Oracle ABC Minimization
- **Before**: Abstract methods for `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()`
- **After**: Only `is_valid()` (membership query) abstract, `ask()` alias concrete
- **Rationale**: Decouples callers from FM-specific APIs

### FMData Decoupling
- **Pattern**: FM metadata passed explicitly as frozen dataclass, not retrieved from oracle
- **Benefits**: Clear separation of ground truth queries vs metadata

### Concrete-Specific Extensions
- **Pattern**: FM-specific methods live on `FeatureModelOracle`, not Oracle ABC
- **Benefit**: Avoids forcing all oracles to implement FM-only APIs

### Example Generator Refactoring
- **Before**: Directly used pysat.solvers
- **After**: Typed as `FeatureModelOracle`, call `oracle.complete_configuration()`
- **Benefit**: Decouples generators from solver details

---

## Key Integration Points Updated

### ConGenTaskPreparation
- **New signature**: `prepare(model, fm_data, oracle)` (separate metadata and queries)

### InteractiveLearner._build_task_from_bias
- **New signature**: Takes `fm_data: FMData` instead of `oracle`

### Example Generators
- Call `oracle.get_fm_data()` once in `__init__`
- Use `oracle.complete_configuration()` for config generation

---

## Documentation Consistency

### Naming Consistency
- Metadata getters: `get_features()`, `get_feature_ids()`, `get_root_feature()`, `get_num_constraints()`
- Config operations: `complete_configuration()`, `get_cnf_clauses()`
- Utility: `get_next_tseitin_var()`

### Type Consistency
- Example generators: `ExampleGenerator(oracle: FeatureModelOracle)`
- Task preparation: `ConGenTaskPreparation.prepare(model, fm_data: FMData, oracle)`

### Architecture Consistency
- All three docs use identical terminology
- Consistent explanation of assumption-guarded clauses
- Feature ID consistency reiterated as critical requirement

---

## Coverage Assessment

### Well-Documented
1. Oracle ABC design (minimal interface)
2. FMData pattern (metadata decoupling)
3. FeatureModelOracle architecture (all methods)
4. Feature ID consistency (critical requirement)
5. Example generator refactoring (complete_configuration usage)

### Areas for Future Enhancement
1. UserPromptOracle edge cases
2. CachedOracle fallback behavior specifics
3. Performance implications of SAT-based complete_configuration()
4. Migration guide for old Oracle ABC method usage

---

## Backward Compatibility Notes

1. **OracleData**: Old name kept as backward-compat alias; GroundTruthData is new name
2. **Oracle ABC Methods**: Removed from ABC but still on FeatureModelOracle
3. **FMData Creation**: New pattern but optional (can still call methods directly)

---

## Verification Checklist

- ✅ Oracle ABC signatures match actual code
- ✅ All FeatureModelOracle methods documented
- ✅ FMData fields match dataclass definition
- ✅ Architecture diagrams consistent with code
- ✅ Code examples follow actual API patterns
- ✅ Cross-references between docs validated
- ✅ All files updated consistently
- ✅ Updated dates set to 2026-02-17

---

**Status**: COMPLETE - All documentation updated and consistent
