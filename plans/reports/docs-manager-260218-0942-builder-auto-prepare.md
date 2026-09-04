# Docs Update: ConGenModelBuilder Auto-Prepare Enhancement

**Date:** 2026-02-18
**Trigger:** ConGenModelBuilder gained `with_oracle()`, auto-prepare in `build()`, and `ConGenModel.task` changed to `Optional[ConGenTask]`

## Changes Made

### `docs/codebase-summary.md` (3 edits)
- Line 25: Updated builder purpose — no longer always returns unprepared model; auto-prepares when oracle+examples set
- Line 103: Design note #10 updated — `build()` auto-prepares when `with_oracle()` + `with_examples()` set; still returns unprepared otherwise
- Line 385: "Earlier Changes" summary updated to reflect conditional behavior

### `docs/code-standards.md` (1 edit)
- Lines 273-308: Replaced single build pattern with two named patterns:
  - Pattern 1: auto-prepare (oracle + examples at build time)
  - Pattern 2: manual prepare (CV reuse, unchanged flow)

### `docs/system-architecture.md` (2 edits)
- Lines 63-66 (Core API): Added Pattern 1 auto-prepare snippet before manual prepare example
- Lines 393-395 (Data Flow Diagram): Added `.with_oracle()` / `.with_examples()` builder chain steps with auto-prepare annotation

### `docs/congen.md` (2 edits)
- Lines 364-378 (Cross-Validation): Replaced removed `from_bias_and_fm_uvl()` call with `from_bias().with_oracle().with_examples()` pattern; added missing `FeatureModelOracle` import

## Unchanged
- `task` property returning `Optional[ConGenTask]` — callers access `model.task` only after prepare; docs show this correctly (no guard clauses shown in examples, which is intentional)
- All files remain under 800 LOC (max: code-standards.md at 694)

## Unresolved Questions
None.
