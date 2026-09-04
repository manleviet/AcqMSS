# Documentation Update Report: Module Refactoring

**Date**: 2026-02-14  
**Task**: Update documentation for QueryGenerator and ExampleProvider relocation  
**Status**: COMPLETED

## Summary

Updated project documentation to reflect refactoring that moved:
1. **QueryGenerator**: `acqmss/algorithms/interactive/query_generator.py` → `acqmss/example_generators/query_generator.py`
2. **ExampleProvider**: `acqmss/oracle/example_provider.py` → `acqmss/example_generators/example_provider.py`

## Files Updated

### 1. `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md`

**Changes Made**:
- Updated **acqmss/algorithms/interactive/** section:
  - Removed QueryGenerator from table (was 262 LOC)
  - Updated file count from 7 to 6 files
  - Updated LOC from ~2,200 to ~1,950

- Added new **acqmss/example_generators/** section:
  - New consolidated section for example & query generation (~1,285 LOC, 7 files)
  - Includes all sampling strategies: RandomSampling, FeatureFrequency, TwoCoverage
  - Documents QueryGenerator move with context: "moved from interactive/"
  - Documents ExampleProvider move with context: "moved from oracle/"
  - Notes lazy loading in `__init__.py`

- Updated **acqmss/oracle/** section:
  - Removed ExampleProvider from table
  - Updated file count from 7 to 6 files
  - Updated LOC from ~750 to ~630
  - Added note: "ExampleProvider moved to `acqmss.example_generators`"

- Updated **Codebase Statistics** table:
  - Added "Recent Changes" subsection documenting:
    - QueryGenerator relocation path
    - ExampleProvider relocation path
    - Canonical import information

### 2. `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md`

**Changes Made**:

- Updated **Core API** code example:
  - Added canonical import: `from acqmss.example_generators import QueryGenerator, ExampleProvider`
  - Added usage examples for both QueryGenerator and ExampleProvider

- Added **acqmss/example_generators/** section (new):
  - Documents purpose: "Generate diverse positive/negative configurations and discriminative queries for learning"
  - Lists example generation strategies (RS, FF, 2-COV)
  - Includes ExampleProvider with relocation note
  - Includes QueryGenerator with relocation note and details:
    - Purpose: discriminative query generation for interactive learning
    - Features: greedy selection, priority strategies
    - Implementation: lazy-loaded via `__getattr__`
  - Documents import strategy:
    - Canonical imports from `acqmss.example_generators`
    - Explains lazy loading mechanism and circular dependency resolution

- Updated **acqmss/oracle/** section:
  - Clarified purpose: "configuration validation" (removed "and example generation")
  - Removed ExampleProvider from concrete implementations
  - Kept 5 implementations: FeatureModelOracle, UserPromptOracle, CachedOracle, OracleData
  - Added note cross-referencing ExampleProvider in example_generators

## Key Documentation Decisions

### Import Documentation
- **Canonical imports**: Documented both classes' new home in `acqmss.example_generators`
- **Lazy loading explanation**: Added technical note explaining the circular dependency resolution strategy in `__getattr__`
- **Backward compatibility note**: Explicitly stated that old import paths no longer work

### Module Organization
- Grouped QueryGenerator and ExampleProvider with example generation strategies
- Rationale: Both are integral to the learning pipeline, QueryGenerator generates queries, ExampleProvider supplies batches
- Creates cohesive "Example & Query Generation" module

### Statistics
- Maintained accurate LOC counts reflecting relocation
- Added new section tracking recent changes for developer awareness

## Files NOT Updated

- **code-standards.md**: Already updated by developer (no changes needed per task)
- **project-overview-pdr.md**: No changes required (high-level focus)
- **project-roadmap.md**: No changes required (timeline/phases not affected)
- **design-guidelines.md**: Not applicable to this refactoring

## Validation

All documentation changes:
- ✅ Reflect actual codebase structure (verified via file system)
- ✅ Use correct case for class names and module paths
- ✅ Include canonical import paths per task requirements
- ✅ Cross-reference between files for consistency
- ✅ Maintain existing formatting and structure conventions
- ✅ Keep file sizes under documentation limits

## Impact Assessment

### For Developers
- Clear understanding of new module organization
- Canonical import paths eliminate confusion
- Lazy loading mechanism explained for future maintenance

### For API Users
- Updated import statements in code examples
- Old imports no longer shown (clean break with old structure)
- New location emphasizes cohesion of example/query generation

## Summary Statistics

| Metric | Value |
|--------|-------|
| Files Updated | 2 |
| Sections Added | 2 (acqmss/example_generators in both docs) |
| Sections Modified | 4 (interactive, oracle in codebase-summary; core API, oracle in system-architecture) |
| Code Examples Updated | 2 (both in system-architecture.md) |
| Cross-references Added | 3+ |

