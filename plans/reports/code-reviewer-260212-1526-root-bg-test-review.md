# Code Review: Root Constraint BG Tests (08b4d39)

**Score: 8/10**

## Scope

- Files: `tests/test_congen.py`, `tests/test_interactive.py`, `tests/test_evaluation.py`
- LOC changed: ~88 (additions)
- Focus: New assertions verifying root constraint propagation into BG
- All 62 tests pass, 3 skipped (missing `REAL-FM-7_rs_1n_kb.json`)

## Overall Assessment

Good, targeted regression tests for commit 08b4d39. Tests correctly verify root feature ID flows through model creation, task preparation, and result extraction in both incremental and non-incremental modes. Assertions are precise with clear messages.

## High Priority

### 1. `test_clause_eval_includes_bg_clauses` is silently skipped

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_evaluation.py` (line 416)

The new integration test `test_clause_eval_includes_bg_clauses` lives inside `TestIntegration`, which has a class-level `@pytest.mark.skipif` that requires `data/results/REAL-FM-7_rs_1n_kb.json` to exist. This file does not exist in the repo (results use `_fold1_kb`, `_fold2_kb`, etc.). The new test does NOT depend on that result file -- it constructs `CONGENResultData` directly -- but it is still skipped due to the class-level guard.

**Impact:** The core test for bg_clauses in clause evaluation never runs. The feature is untested in CI.

**Fix:** Either move `test_clause_eval_includes_bg_clauses` to its own class without the skip guard, or add per-method skip conditions instead of class-level.

```python
# Option A: standalone class
class TestBgClausesIntegration:
    """Integration tests for bg_clauses in evaluation."""

    @pytest.mark.skipif(
        not (Path('data/fms/REAL-FM-7.uvl').exists() and
             Path('data/bias/REAL-FM-7-bias.json').exists()),
        reason="FM and bias data files not found"
    )
    def test_clause_eval_includes_bg_clauses(self):
        ...
```

### 2. `test_congen_incremental_with_ff_examples` not updated

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py` (line 183)

The FF-examples test (`test_congen_incremental_with_ff_examples`) unpacks `root_id` from the helper but does not assert `set_b` or `bg_clauses` like the RS tests do. This is inconsistent; the same root-in-BG invariant should hold regardless of example strategy.

**Impact:** Low risk since the mechanism is the same, but inconsistency may mask future regressions.

## Medium Priority

### 3. `_build_task_from_bias` tested via private method access

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_interactive.py` (line 336)

`test_build_task_from_bias_includes_root` calls `InteractiveLearner._build_task_from_bias()` directly. Acceptable for a unit test, but if this method is renamed or refactored the test breaks silently. The `test_learner_from_files` test already validates the same behavior through the public API, making this test partially redundant.

**Impact:** Minor maintenance burden. Not blocking.

### 4. `test_bg_clauses_default_empty` is trivial

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_evaluation.py` (line 211)

```python
result = CONGENResultData(kb_constraints=[], n_bias=10, n_kb=0)
assert result.bg_clauses == []
```

This only tests Python's `field(default_factory=list)`. It has near-zero value for verifying business logic. Not harmful, just noise.

## Positive Observations

- Assertions use descriptive messages (`"Root should be in set_b"`, etc.)
- Both incremental (`List[int]`) and non-incremental (`List[List[List[int]]]`) BG representations are tested with type-correct assertions
- `create_checker_and_task` helper updated cleanly with backward-compatible tuple extension
- Proper `try/finally` cleanup in CONGEN tests for checker resources
- `test_build_task_from_bias_includes_root` uses strict equality (`==`) rather than just `in`, verifying background has exactly the root
- Existing test patterns followed consistently

## Recommended Actions

1. **[High]** Move `test_clause_eval_includes_bg_clauses` out of the skipped `TestIntegration` class so it actually runs
2. **[Medium]** Add `set_b` and `bg_clauses` assertions to `test_congen_incremental_with_ff_examples` for consistency
3. **[Low]** Consider whether `test_bg_clauses_default_empty` adds enough value to keep

## Unresolved Questions

- The class-level `skipif` in `TestIntegration` depends on `REAL-FM-7_rs_1n_kb.json` which does not exist. Are the 3 integration tests in that class intended to be permanently skipped, or is this a stale fixture reference?
