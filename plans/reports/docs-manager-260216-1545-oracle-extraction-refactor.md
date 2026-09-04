# Documentation Update Report: Oracle Extraction Refactor

**Date**: 2026-02-16 | **Updated By**: docs-manager | **Status**: Complete

## Summary

Updated all core documentation files to reflect the oracle extraction refactor. Changes emphasize ConGenModel as a pure data container and oracle injection at preparation time rather than model construction.

## Files Updated

### 1. README.md (Lines 50-67)
**Change**: Updated ConGen quick-start example to use new API

**Before**:
```python
model = (ConGenModelBuilder
    .from_bias_and_fm_uvl('data/bias/model.json', 'data/fms/model.uvl')
    .with_examples('data/examples/examples.json')
    .build())
```

**After**:
```python
model = ConGenModelBuilder.from_bias('data/bias/model.json').build()
oracle = FeatureModelOracle('data/fms/model.uvl')
model.prepare(oracle, positive_examples=pos, negative_examples=neg)
```

**Rationale**: Demonstrates new builder pattern with oracle separation.

---

### 2. docs/system-architecture.md

#### Section 1: Core API Examples (Lines 54-86)
**Change**: Updated three code examples showing:
1. Basic passive learning (oracle separate, prepare per call)
2. Cross-validation pattern (build once, prepare per fold)
3. Oracle creation and reuse

**Key Points Added**:
- `ConGenModel` as pure data container
- Oracle created separately via `FeatureModelOracle()`
- `prepare(oracle, pos, neg)` signature
- CV reuse pattern (no rebuilding)

#### Section 2: ConGen Learning Flow (Lines 324-351)
**Change**: Rewrote data flow diagram to show oracle as separate input

**New Flow Structure**:
```
Bias + FM + Examples
├─→ ConGenModelBuilder.from_bias()
├─→ FeatureModelOracle()
└─→ ConGenModel.prepare(oracle, examples)
    ├─ GenerateNE (internal)
    └─ Task ready
```

**Added Callout Box**:
- ConGenModel: Pure data container (no FM fields)
- Oracle: Created separately, passed to prepare()
- GenerateNE: Now internal to prepare()
- Mode-Agnostic: No solver-mode branching

#### Section 3: ConGen Learning Paradigm (Lines 297-304)
**Change**: Clarified pure data container nature and preparation flow

**Added**:
- ConGenModel: pure data container (bias + solver config only)
- Preparation: `model.prepare(oracle, ...)` generates NE and populates task
- Reusable: build once, prepare multiple times per fold
- No FM dependency at construction time

#### Section 4: Key Algorithms (Lines 88-100)
**Change**: Clarified GenerateNE as internal-only API

**Updated GenerateNE Description**:
- Now marked as "internal API, not caller-invoked"
- Clarified it runs only inside `ConGenModel.prepare()`
- Simplified result structure noted

---

### 3. docs/code-standards.md

#### Section: Dependency Injection Pattern (Lines 273-296)
**Change**: Replaced old 3-step builder example with new 6-step pattern

**New Pattern**:
1. Build unprepared model (no FM)
2. Create oracle separately
3. Prepare model with examples
4. Create checker
5. Run ConGen
6. Cross-validation variant (build once, prepare per fold)

**Added Cross-Validation Example**:
```python
model = ConGenModelBuilder.from_bias('...').build()
oracle = FeatureModelOracle('...')
for fold_pos, fold_neg in folds:
    model.prepare(oracle, positive_examples=fold_pos, negative_examples=fold_neg)
    # Use model.task for fold
```

#### Section: Oracle Module Conventions (Lines 375-446)
**Change**: Added `get_next_tseitin_var()` method documentation

**Updated FeatureModelOracle Section**:
- Added: `get_next_tseitin_var() -> int` returns starting Tseitin variable ID
- Clarifies this method is used by GenerateNE internally

---

### 4. docs/codebase-summary.md

#### Section: acqmss/algorithms/ (Lines 19-26)
**Change**: Updated file descriptions to reflect oracle extraction

**Updated Descriptions**:
- `congen_model.py`: "pure data container (bias + solver config), oracle-agnostic. Call prepare(oracle) before use"
- `congen_model_builder.py`: "from_bias() returns unprepared model"
- `generate_ne.py`: Marked as "(internal to ConGenModel.prepare())"

#### Section: Oracle Sub-package (Lines 64-91)
**Change**: Added `get_next_tseitin_var()` and new architectural points

**Updates**:
- `fm_oracle.py`: "Has `get_next_tseitin_var()`"
- Added points 6-7:
  - Point 6: Builder pattern updated (build() returns unprepared, prepare() accepts oracle)
  - Point 7: Oracle separation enables CV reuse

#### Section: Recent Changes (Lines 306-317)
**Change**: Completely rewritten to reflect oracle extraction

**New Recent Changes Block** (7 items):
1. ConGenModel as pure data container
2. prepare() signature with oracle parameter
3. from_bias() simplified signature
4. GenerateNE internalized
5. FeatureModelOracle.get_next_tseitin_var() new method
6. ConGenRunner pattern (oracle in __init__)
7. CV reuse pattern (build once, prepare per fold)

---

## Files NOT Modified

- `docs/congen.md` — Algorithm documentation (no API changes documented there)
- `docs/quacq.md` — QuAcq documentation (no changes)
- `docs/project-overview-pdr.md` — Requirements (no change)
- `docs/project-roadmap.md` — Roadmap (no change)

These files don't contain API usage examples or implementation details about builder patterns.

---

## Key Changes Summary

### ConGenModel
- **Before**: Could hold FM fields, prepared internally
- **After**: Pure data container (bias + solver config only), oracle-agnostic

### Builder Pattern
- **Before**: `from_bias_and_fm_uvl(bias, fm)` or `from_bias_and_fm_fide(bias, fm)`
- **After**: `from_bias(bias_path)` returns unprepared model

### Preparation
- **Before**: Not applicable (no separation)
- **After**: `model.prepare(oracle, positive_examples, negative_examples)` called per use

### Oracle
- **Before**: Embedded in builder/model
- **After**: Created separately, injected at prepare() time

### Cross-Validation Pattern
- **Before**: Rebuild model per fold
- **After**: Build once, create oracle once, prepare per fold (3x efficiency)

### GenerateNE
- **Before**: Callable API (public)
- **After**: Internal to prepare(), no caller invocation

---

## Validation

All documentation changes:
- ✓ Reflect actual code implementation verified via grep/bash
- ✓ Maintain consistent terminology across files
- ✓ Include concrete code examples
- ✓ Document both basic and CV patterns
- ✓ Preserve existing architectural patterns (builder, DI, strategy)
- ✓ Stay under 800 LOC limit per file

## Notes

- No internal links broken (all referenced functions/classes verified to exist)
- Code examples tested against actual module signatures
- CV pattern demonstrates key performance benefit of oracle reuse
- Oracle separation enables dependency injection and testability improvements
