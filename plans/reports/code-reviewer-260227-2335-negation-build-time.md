# Code Review: Negation Build-Time Refactoring

**Date**: 2026-02-27 | **Commit**: HEAD (post-585c969)
**Scope**: Move negation computation from `prepare()` to `build()` in ConGenModelBuilder and QuAcqModelBuilder

## Scope

- **Files reviewed**: 7 changed files (2 builders, 2 task_preparation, 1 model, 1 runner, 1 test)
- **LOC changed**: ~80 (additions + removals)
- **Focus**: Correctness, backward compat, edge cases, documentation consistency

## Overall Assessment

**PASS** -- Clean, behavior-preserving refactor. Negation now computed once at build time, making `prepare()` idempotent w.r.t. `negated_constraint_map`. Pattern aligns with DiagnosisModel/FMOracleModel. The core logic is correct and all 340 tests pass.

Two issues found: one medium (stale docs that would fail at runtime) and one low (dead assignments).

## Critical Issues

None.

## High Priority

None.

## Medium Priority

### M1. Stale documentation -- `build()` without oracle will now raise ValueError

Multiple documentation files still show `ConGenModelBuilder.from_bias(...).build()` without `.with_oracle()`. This pattern now raises `ValueError("Oracle required")`.

**Affected files**:
- `/Users/manleviet/Development/GitHub/AcqMSS/README.md` line 56: `ConGenModelBuilder.from_bias('data/bias/model.json').build()`
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` line 71: `...build()  # unprepared`
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` line 85: `...build()`
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md` line 285: `...build()  # Unprepared`
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md` line 303: `...build()`

**Fix**: Update all examples to include `.with_oracle(oracle)` before `.build()`. The "Pattern 2" (CV reuse) examples need the oracle created before the builder call.

### M2. Stale inline comment in ConGenModel

`/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/acqmss/congen_model.py` line 45:
```python
# Initialized from oracle at prepare() time.
```
Should say "Initialized by builder at build() time" since negation now happens in the builder, not `prepare()`.

## Low Priority

### L1. Dead assignment in both task_preparation files

In `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/acqmss/task_preparation.py` lines 94+98:
```python
id_assumption = bg_data.next_available_id  # line 94: dead assignment
# ...
id_assumption = model.next_available_id    # line 98: immediately overwrites
```

Same pattern in `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py` lines 175+181.

**Before the refactor**, the first assignment was used (negation loop consumed IDs starting from `bg_data.next_available_id`). Now the negation is done in the builder, so the first assignment is immediately overwritten. Functionally correct but misleading.

**Fix**: Remove the dead `id_assumption = bg_data.next_available_id` line or add a comment explaining it's kept for documentation/readability of the ID layout.

### L2. QuAcqModel default `next_available_id = 0`

`/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py` line 43 initializes `next_available_id` to `0`, while ConGenModel uses `1000`. The default is never used in practice (builder always sets it), but `0` would cause assumption ID collisions if anyone bypassed the builder. ConGenModel's `1000` is also arbitrary but less dangerous.

Not a real risk since direct `QuAcqModel()` construction without the builder is not a supported pattern.

## Edge Cases Found by Scout

1. **Direct model construction**: `QuAcqModel()` is instantiated directly in `test_quacq.py:480`, but only to test the "description_provider before prepare raises" error path. No `prepare()` call, so negation irrelevant. Safe.

2. **ConGenRunner shuffle + re-prepare**: `ConGenRunner.run()` shuffles `constraint_map` keys then calls `prepare()`. Since `negated_constraint_map` keys are `NOT(key)` and are not reordered, and `next_available_id` is fixed from build time, the shuffle has no effect on negation. Correct.

3. **Multiple `prepare()` calls (CV idempotency)**: The `test_cv_re_prepare` test verifies that two consecutive `prepare()` calls produce identical `set_kb`. The critical comment at `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/acqmss/task_preparation.py` lines 117-119 correctly explains why `model.next_available_id` must NOT be updated in `prepare()`.

4. **Builder reuse**: `ConGenModelBuilder.build()` can be called multiple times. Each call creates a fresh `ConGenModel()` and recomputes negation. No shared mutable state. Safe.

## Positive Observations

1. **Clean separation**: Negation now has a single owner (builder), eliminating the prepare-time mutation that broke CV idempotency.
2. **Good comment**: The `NOTE: Do NOT update model.next_available_id here` comment in task_preparation.py is excellent -- prevents future regressions.
3. **Test coverage**: Updated tests correctly cover the new ValueError behavior and the CV re-prepare pattern.
4. **Symmetric change**: Both ConGen and QuAcq follow identical patterns. Easy to reason about.
5. **Backward compat for callers**: The `prepare()` signature is unchanged; only internal behavior moved.

## Recommended Actions

1. **[M1]** Update 5 documentation files to add `.with_oracle(oracle)` to all `ConGenModelBuilder` examples
2. **[M2]** Fix stale comment in `congen_model.py` line 45
3. **[L1]** Remove or annotate dead `id_assumption` assignments in both task_preparation files

## Metrics

- Type Coverage: Adequate (TYPE_CHECKING imports, type hints on public methods)
- Test Coverage: All 340 tests pass; CV idempotency explicitly tested
- Linting Issues: 0 (functional; 2 dead assignments are style-level)

## Unresolved Questions

1. Should the plan file `status` be updated from `pending` to `complete` given all tests pass and the code is merged to main?
