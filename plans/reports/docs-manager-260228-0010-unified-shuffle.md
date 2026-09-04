# Documentation Update: Unified Shuffle-After-Prepare Refactoring

**Date**: 2026-02-28
**Commit**: 260228-0010
**Status**: Complete

## Summary

Updated documentation to reflect the unified shuffle-after-prepare refactoring for both ConGenRunner and QuAcqRunner. Both runners now follow an identical lifecycle pattern where bias constraints are shuffled AFTER prepare(), not before, enabling reproducible cross-validation without model rebuild.

## Changes Made

### 1. docs/codebase-summary.md

**Section**: conacq/runners/ — Execution Runners

**Updates**:
- Updated BaseRunner description to reflect model built once in __init__ (not just oracle)
- Added clarification that runners now "build model once in __init__, reused across all run() calls"
- Updated ConGenRunner documentation:
  - __init__: Builds model once via ConGenModelBuilder (requires oracle for negation computation)
  - Per-fold lifecycle explicitly documented: prepare() → shuffle set_c after prepare() → run ConGen
  - Noted oracle reuse across folds (no rebuild)
- Updated QuAcqRunner documentation:
  - __init__: Builds model once (requires oracle, auto-prepares)
  - Per-run lifecycle: re-prepare() → shuffle set_c after prepare() → dispatch to oracle/example mode
- Added new "Unified Shuffle Pattern" section (commit 260228):
  - Both runners follow identical shuffle lifecycle: prepare() → shuffle set_c → run algorithm
  - Shuffle seed controls bias iteration order AFTER preparation (not before)
  - Enables reproducible CV experiments without model rebuild

**Rationale**: Accurate documentation of the new shuffle-after-prepare pattern that is now shared across both runners.

### 2. docs/system-architecture.md

**Sections**:
- conacq/runners/ — Execution Runners
- ConGen Learning Flow (data flow diagram)
- QuAcq Interactive/Batch Flow (data flow diagram)

**Updates**:

#### Runners Architecture (conacq/runners/)
- Expanded "Unified Lifecycle Pattern" with concrete code examples showing:
  - ConGenRunner: build once → prepare per fold → shuffle → run
  - QuAcqRunner: same pattern with model re-prepare per run
- Updated BaseRunner ABC description to mention model building in __init__
- Detailed per-run lifecycle for both runners
- Clarified shuffle timing (after prepare, not before)

#### ConGen Learning Flow Diagram
- Added [__init__] and [run] labels to clarify when each step occurs
- Updated to show shuffle-after-prepare pattern (commit 260228)
- Added "Key Changes" summary explaining:
  - Build-time negation (idempotent)
  - Shuffle after prepare enables CV reuse
  - No rebuild between folds
  - PrepareNE internal to prepare()
  - Mode-agnostic design

#### QuAcq Interactive/Batch Flow Diagram
- Added [__init__] and [run] labels matching ConGen pattern
- Updated to show per-run re-prepare with shuffle-after-prepare
- Added "Key Changes" section (commit 260228):
  - Build-time negation
  - Per-run prepare for fresh task
  - Shuffle after prepare (matching ConGen)
  - Unified pattern across both paradigms

**Rationale**: Data flow diagrams now accurately reflect the actual execution order and timing of operations. Both runners follow identical shuffle timing, making the pattern easier to understand.

### 3. docs/code-standards.md

**Section**: Design Patterns → Dependency Injection

**Updates**:
- Replaced ConGenModelBuilder usage examples with new cross-validation pattern
- Changed from old "auto-prepare" pattern to explicit manual prepare pattern
- Added concrete code for cross-validation loop:
  - Build once with oracle
  - For each fold: prepare() → shuffle task.set_c → run ConGen
  - Shuffle timing now explicit: AFTER prepare, not before
- Added ConGenRunner facade pattern as "recommended for production"
- Removed old Pattern 1 (auto-prepare with examples at build time)

**Rationale**: Code examples now match current API (oracle required at build time) and demonstrate the shuffle-after-prepare pattern with clear fold iteration.

## Verification

All changes reference documented code patterns:
- ✓ ConGenRunner.__init__: Builds model with oracle (verified in conacq/runners/congen_runner.py line 114-118)
- ✓ Shuffle after prepare: random.Random(shuffle_seed).shuffle(task.set_c) (verified line 162)
- ✓ QuAcqRunner.__init__: Builds model with oracle (verified in conacq/runners/quacq_runner.py line 85-89)
- ✓ QuAcqRunner per-run prepare: model.prepare(self.oracle) (verified line 157)
- ✓ Shuffle pattern: Both runners shuffle task.set_c after prepare

## Files Updated

1. `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` (lines 139-170)
2. `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` (lines 223-292, 586-646, 634-688)
3. `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md` (lines 274-309)

## Key Concepts Documented

### Unified Lifecycle Pattern
Both runners now follow:
1. **__init__**: Build oracle once, build model once (negation computed at build time)
2. **run()**: Prepare for fold → Shuffle set_c → Run algorithm
3. **cleanup()**: Release oracle resources

### Shuffle Timing
- **Before**: Shuffle constraint_map before prepare (old ConGenRunner pattern)
- **After**: Shuffle task.set_c AFTER prepare() (new unified pattern)
- **Benefit**: Enables CV reuse without model rebuild

### Build-Time Negation
- Negated forms (Tseitin transformation) computed at builder.build() time
- Model stores next_available_id for reuse across multiple prepare() calls
- prepare() reads negation maps (idempotent), never writes to them
- Fixes latent CV bug where next_available_id drifted across folds

## Documentation Accuracy

All referenced patterns verified against actual code:
- ConGenModelBuilder requires oracle at build time ✓
- QuAcqModelBuilder requires oracle at build time ✓
- Both shuffle task.set_c (not constraint_map) ✓
- Both shuffle AFTER prepare(), not before ✓
- No _original_bias_constraint_order field ✓
- No _use_incremental field (in QuAcqRunner) ✓
- No _feature_ids field (in QuAcqRunner) ✓

## Impact

**Documentation Coverage**: All runner lifecycle patterns and shuffle mechanics now accurately reflected across codebase summary, system architecture, and code standards docs.

**Consistency**: Both ConGenRunner and QuAcqRunner documented with identical lifecycle pattern, making cross-paradigm understanding clearer for developers.

**Clarity**: Explicit before/after timing in data flow diagrams removes ambiguity about when shuffle operations occur relative to prepare().
