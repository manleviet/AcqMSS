# Code Review: task_preparation.py Refactoring

**Date:** 2026-02-15
**Scope:** acqmss/algorithms/task_preparation.py
**LOC:** 206 lines
**Focus:** Refactoring `_prepare_bias_constraints` to reuse `prepare_kb`
**Scout findings:** None (focused review)

## Overall Assessment

Refactoring successfully eliminates code duplication by replacing `_prepare_bias_constraints` with a call to `prepare_kb` from `explanation.models.task_preparation`, plus a new helper `_build_constraint_maps` for post-processing. All 13 ConGen tests pass.

## Critical Issues

**None**

## High Priority

### H1: Duplicate Import of DescriptionProvider

**Location:** Lines 13, 17

```python
from explanation.models import DescriptionProvider  # Line 13
from explanation.models.task_preparation import (
    TestCaseTask,
    TestCaseTaskPreparationStrategy,
    DescriptionProvider,  # Line 17 - duplicate
    ...
)
```

**Impact:** Redundant import, reduces clarity

**Fix:**

```python
from explanation.models.task_preparation import (
    TestCaseTask,
    TestCaseTaskPreparationStrategy,
    DescriptionProvider,  # Keep only this
    PreparationOutput,
    prepare_testsuite_with_negation,
    prepare_kb,
)
```

Remove line 13.

## Medium Priority

**None**

## Low Priority

**None**

## Edge Cases Found

**None** — Verified `negated_constraint_map=None` is handled correctly (lines 78-81).

## Positive Observations

1. **Correct ID Mirroring**: `_build_constraint_maps` correctly mirrors `prepare_kb`'s sequential ID assignment pattern (+1 per original, +1 per negated form if exists)

2. **Clean Abstraction**: Separation of concerns between ID assignment (`prepare_kb`) and bidirectional map building (`_build_constraint_maps`) is clear

3. **Edge Case Handling**: Safe `None` check for `negated_constraint_map` (line 78)

4. **Iteration Order**: Dict iteration order is deterministic (Python 3.7+), ensuring consistency between `prepare_kb` and `_build_constraint_maps`

5. **No Circular Imports**: Verified import chain is clean

6. **Test Coverage**: All 13 ConGen tests pass, confirming correctness

## Recommended Actions

1. **Remove duplicate import** (line 13) — trivial fix, no behavioral change

## Metrics

- Type Coverage: Not measured (Python, type hints partial)
- Test Coverage: 100% of ConGen tests passing (13/13)
- Linting Issues: 1 (duplicate import)

## Unresolved Questions

None
