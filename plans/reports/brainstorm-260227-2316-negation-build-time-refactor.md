# Brainstorm: Move Negation to Build Time

## Problem
ConGenModel and QuAcqModel compute `negated_constraint_map` inside `prepare()` (TaskPreparation), causing side effects on model state each run. DiagnosisModel and FMOracleModel already compute negation at build time — making `prepare()` read-only and idempotent.

## Decision: Option B — KISS
Move negation to build time. Keep oracle param in `prepare()`. Minimal change, achieves idempotent `prepare()`.

## Evaluated Approaches

### Option A: Cache all oracle data at build time
- **Pro**: `prepare()` needs no oracle at all
- **Con**: ConGen GenerateNE still needs oracle → forced to cache or inject separately
- **Con**: Over-engineering — more changes than needed

### Option B: Only move negation to build (CHOSEN)
- **Pro**: Smallest change, achieves goal
- **Pro**: `prepare()` already idempotent after negation removed
- **Pro**: Consistent with DiagnosisModel pattern
- **Con**: `prepare()` still takes oracle — but that's fine

### Option C: Cache BG/FM, inject oracle for GenerateNE only
- **Pro**: QuAcq prepare() drops oracle
- **Con**: Asymmetric API between ConGen and QuAcq
- **Con**: More refactoring for marginal gain

## Implementation Plan

### Phase 1: ConGen (4 files)

**1a. ConGenModelBuilder.build()** — add negation computation
- Require oracle via `.with_oracle()` (method already exists)
- After loading bias → `constraint_map`:
  - Get `oracle.get_bg_data().next_available_id` → starting tseitin var
  - Loop constraint_map → compute negated forms → `model.negated_constraint_map`
  - Store `model.next_available_id` = final tseitin var ID
- Validate: oracle required in `_validate()`

**1b. ConGenTaskPreparation.prepare()** — remove negation loop
- Delete Step 1 negate_cnf_tseitin loop (lines ~100-102)
- Read `model.negated_constraint_map` directly (already populated by builder)
- Use `model.next_available_id` as starting ID instead of computing from bg_data

**1c. ConGenRunner.__init__()** — pass oracle to builder
```python
self.model = (ConGenModelBuilder
              .from_bias(bias_path)
              .with_oracle(self.oracle)
              .use_incremental(use_incremental)
              .build())
```

**1d. ConGenModel** — no structural change, just uses existing fields

### Phase 2: QuAcq (4 files)

**2a. QuAcqModelBuilder.build()** — add negation computation (same pattern)
- Oracle already required via `.with_oracle()`
- Compute negation before `model.prepare(oracle)` call
- Store `model.next_available_id`

**2b. QuAcqTaskPreparation.prepare()** — remove negation loop
- Same change as ConGen: delete negate loop, read from model

**2c. QuAcqRunner** — minimal change (already passes oracle to builder)

**2d. QuAcqModel** — no structural change

### Phase 3: Tests + Verify
- Run full test suite
- Verify multi-prepare safety (ConGenModel reuse in CV)

## Key Design Decisions
1. Oracle required at build time for both builders — acceptable since BaseRunner creates oracle before subclass init
2. `prepare()` keeps oracle parameter — needed for BG data copy + GenerateNE (ConGen) + FM data (QuAcq)
3. `negated_constraint_map` populated once at build → `prepare()` read-only

## Risks
- **Low**: `next_available_id` must be correctly propagated from negation to prepare
- **Low**: Existing tests should catch any ID offset bugs

## Success Criteria
- All existing tests pass
- `prepare()` no longer writes to `negated_constraint_map`
- ConGen CV (multi-run) works identically
- Pattern consistent with DiagnosisModel approach
