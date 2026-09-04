# Documentation Update: ConGen Workflow Refactoring

**Date**: 2026-02-14
**Agent**: docs-manager
**Work Context**: `/Users/manleviet/Development/GitHub/AcqMSS`

## Summary

Updated project documentation to reflect ConGen workflow refactoring changes. All updates focused on API usage patterns and architectural flow diagrams.

## Changes Made

### 1. docs/code-standards.md

**Section Updated**: Design Patterns → Dependency Injection

- **Before**: `ConGen.acquire(task: CONGENTask)`
- **After**: `ConGen.acquire(set_b, set_bg, set_tc, set_ne, neg_c_map, assumption_to_constraint)`
- Added ConGenModelBuilder fluent pattern example
- Added CheckerFactory.create_from_model() usage
- Removed task object parameter, replaced with direct assumption ID params

### 2. docs/system-architecture.md

**Sections Updated**:
- **acqmss/algorithms/ — Core API**: Updated to show ConGenModelBuilder and CheckerFactory usage
- **Key Algorithms**: Updated ConGen description to clarify GenerateNE is called by `ConGenModel.prepare()`
- **Two Learning Paradigms**: Updated ConGen section to mention CheckerModel protocol
- **ConGen Learning Flow**: Completely revised flow diagram showing:
  - ConGenModelBuilder fluent pattern
  - ConGenModel.prepare() calling GenerateNE internally
  - CheckerFactory.create_from_model()
  - ConGen.acquire() with direct params
- Added Builder Pattern note

### 3. docs/codebase-summary.md

**Sections Updated**:
- **acqmss/algorithms/ file table**:
  - Updated congen.py description (direct params instead of task)
  - Updated generate_ne.py description (called by prepare())
  - Added congen_model.py entry (CheckerModel protocol)
  - Added congen_model_builder.py entry (fluent builder)
- **Critical Implementation Details**:
  - Added CheckerModel protocol point
  - Added Builder Pattern point
  - Updated GenerateNE design description

### 4. CLAUDE.md

**Section Updated**: Key API Patterns → ConGen usage

- **Recommended pattern**: ConGenModelBuilder fluent API
  - `.from_files()` → `.with_examples()` → `.use_incremental()` → `.build()`
  - `CheckerFactory.create_from_model()`
  - `ConGen.acquire()` with 6 direct params
- **Alternative pattern**: Direct ConGenModel construction for CV folds
  - Manual `prepare()` call
  - Reuse model across folds with different examples

## Key Architectural Changes Documented

1. **ConGenModel now satisfies CheckerModel protocol**:
   - `get_kb()` → task.set_kb
   - `get_assumptions()` → task.assumptions
   - `use_incremental`, `solver_name` attributes

2. **ConGenModel.prepare() includes GenerateNE**:
   - Callers no longer invoke GenerateNE manually
   - Results merged into task before return
   - Temp non-incremental checker used for NE generation

3. **ConGenModelBuilder class**:
   - Fluent builder pattern (mirrors DiagnosisModelBuilder)
   - Encapsulates file loading, model creation, prepare() call
   - Single `.build()` returns ready-to-use model

4. **ConGen.acquire() signature change**:
   - From: `acquire(task: ConGenTask)`
   - To: `acquire(set_b, set_bg, set_tc, set_ne, neg_c_map, assumption_to_constraint)`
   - Direct params instead of task object

5. **Checker creation standardized**:
   - All callers use `CheckerFactory.create_from_model(model, profiler)`
   - No manual checker instantiation
   - Model provides solver config via CheckerModel protocol

## Files Updated

- `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md` (1 section)
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` (4 sections)
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` (2 sections)
- `/Users/manleviet/Development/GitHub/AcqMSS/CLAUDE.md` (1 section)

## Documentation Validation

All updates verified against actual code:
- `acqmss/algorithms/congen_model_builder.py` (157 LOC)
- `acqmss/algorithms/congen_model.py` (186 LOC)
- `acqmss/algorithms/congen.py` (acquire signature lines 67-75)

No fictional APIs or non-existent methods documented. All code examples reflect actual implementation.

## Next Steps

None required. Documentation now accurately reflects refactored ConGen workflow.
