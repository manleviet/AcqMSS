# Phase R Documentation Completion Report

**Date**: 2026-06-19  
**Task**: Complete Phase R refactor documentation sweep — remove stale API references, trim oversized files

## Summary

Surgical edits across 7 documentation files to align with Phase R task-as-unit refactor (commit 260618 completion). 

**Key Changes**:
- Replaced all `.prepare(oracle, ...)` references with `prepare_task(task_input, oracle)`
- Removed all `CheckerModel` protocol mentions (deleted in R6, replaced by `ConsistencyExecutor` Protocol)
- Removed all `.use_incremental(...)` builder-chain examples (now operation-level via `CheckerFactory.create_from_task(use_incremental=...)`)
- Removed all `create_from_model(model)` code examples (replaced by `create_from_task(task, ...)`)
- Clarified that `GenerateNE` is pure (returns clauses; caller extends its own KB copy)
- Trimmed two files from 908→798 LOC and 840→783 LOC to meet <800 target

## Files Modified

### 1. **docs/system-architecture.md** (908→798 LOC, -110 lines)

**Sections Updated**:
- **Lines 70, 109**: Removed `.use_incremental(True)` from builder examples (operation-level only)
- **Lines 76-77**: Updated prepare call to `model.prepare_task(task_input, oracle)`
- **Lines 161-168**: Clarified GenerateNE is pure (returns clauses); called by ConGenTaskPreparation
- **Lines 306, 314**: Replaced `.prepare(oracle, ...)` with `.prepare_task(task_input, oracle)`
- **Lines 649, 651**: Updated method calls and clarified pure pattern
- **Line 653**: Removed stale CheckerModel protocol reference
- **Lines 684, 706, 736, 742**: Removed deprecated API calls
- **Lines 791**: Updated per-run prepare pattern
- **Diagram lines 693, 706, 721, 742**: Removed stale method signatures

**Trimming Strategy**:
- Consolidated redundant QueryProvider examples (lines 130-133 → single example)
- Simplified QuAcq complexity descriptions (lines 157-158 → brief summary)
- Reduced oracle class list detail (lines 199-230 → 5-line bullet list)
- Cut QueryProvider API details (lines 179-189 → 3-line summary)
- Removed evaluation metrics equations (lines 278-283 → inline summary)
- Removed Architecture Notes section (lines 200-202, redundant with Critical Detail)

### 2. **docs/code-standards.md** (840→783 LOC, -57 lines)

**Sections Updated**:
- **Line 204**: Updated `CheckerFactory.create_from_model(self.model)` to `create_from_task(task, ...)`
- **Lines 207-210**: Refactored runner example to use `prepare_task(TaskInput(), oracle)` + `create_from_task(...)`
- **Line 357**: Removed `.use_incremental(True)` from builder example
- **Line 489**: Removed `CheckerModel` protocol reference; clarified ModelProtocol + immutable KB

**Trimming Strategy**:
- Consolidated manual CV loop and ConGenRunner facade into single, concise example (lines 361-407)
- Removed VariableCodec example block (19 lines, redundant with codec pattern section elsewhere)
- Removed Task-as-Unit detailed example block (15 lines, high-level statement sufficient)

### 3. **docs/codebase-summary.md** (594 LOC, no trim target)

**Lines Modified**:
- **Line 22**: Updated table description: GenerateNE is "pure negated example generation" (not "internal to ConGenModel.prepare()")
- **Lines 138-142**: Merged 9 detailed design notes into 8 concise bullets; clarified GenerateNE is pure, prepare_task pattern
- **Lines 507-514**: Replaced stale build-time/prepare idempotence notes with Phase R architecture summary

### 4. **docs/congen.md** (389 LOC, no trim target)

**Lines Modified**:
- **Lines 138-140**: Updated GenerateNE description; clarified returns clauses (no mutation); invoked by ConGenTaskPreparation during `prepare_task()`

### 5. **docs/quacq.md** (460 LOC, no trim target)

**Lines Modified**:
- **Lines 206-207**: Updated GenerateNE description; clarified pure function pattern invoked by strategy

### 6. **docs/project-overview-pdr.md** (369 LOC, no trim target)

**Lines Modified**:
- **Line 50**: Simplified GenerateNE description; noted Phase R (pure, returns clauses)

### 7. **README.md** (183 LOC)

No stale references found; no changes required.

## Acceptance Criteria — All MET ✓

```
CHECK 1: grep -rn "create_from_model|CheckerModel|\.use_incremental(" docs/ README.md
  → PASS: Only allowed historical "replaces create_from_model" lines remain
           (project-overview-pdr.md:310, project-roadmap.md:127)

CHECK 2: grep -rn "model\.prepare(|Model\.prepare(" docs/ README.md | grep -v prepare_task
  → PASS: Empty result (no stale calls found)

CHECK 3: wc -l docs/system-architecture.md docs/code-standards.md
  → PASS: system-architecture.md: 798 LOC (< 800)
           code-standards.md: 783 LOC (< 800)
```

## Verification Commands (User Can Run)

```bash
# Verify no stale API references
grep -rn "create_from_model\|CheckerModel\|\.use_incremental(" docs/ README.md | grep -v "replaces"

# Verify no model.prepare() calls
grep -rn "model\.prepare(\|Model\.prepare(" docs/ README.md | grep -v prepare_task

# Verify LOC targets met
wc -l docs/system-architecture.md docs/code-standards.md
```

## Technical Accuracy Verified Against

- `conacq/algorithms/acqmss/congen_model.py`: `prepare_task(task_input, oracle) → ConGenTask`
- `conacq/algorithms/acqmss/task_preparation.py`: ConGenTaskPreparation calls GenerateNE internally
- `conacq/algorithms/acqmss/generate_ne.py`: `generate()` returns `NEPerTestcase` list (pure)
- `conacq/algorithms/quacq/quacq_model.py`: Same prepare_task pattern
- `explanation/operations/algorithms/checker.py`: `CheckerFactory.create_from_task(task, use_incremental=...)`
- `explanation/models/diagnosis_model_builder.py`: No `use_incremental` on model builders

## Status

**Status**: DONE

All stale references removed, both oversized files trimmed to <800 LOC, all acceptance criteria met. Documentation now accurately reflects Phase R immutable KB + pure Task factory pattern.

