# Phase 3: Update Tests

## Context Links

- [Phase 1](phase-01-inject-checker-into-findscope-findc.md), [Phase 2](phase-02-update-quacq-callsites.md)
- [plan.md](plan.md)
- Source: `tests/test_quacq.py`

## Overview

- **Priority**: P2
- **Status**: complete
- **Description**: Update existing QuAcq tests to work with new FindScope/FindC signatures. Verify all integration tests pass with SAT-based checking.

## Key Insights

- FindScope/FindC are NOT tested directly — they're only exercised through QuAcq.learn() integration tests
- Tests `TestQuAcq.test_quacq_learn_with_limit`, `TestQuAcqWithAssumptionIDs.test_quacq_learn_with_quacq_task`, and `TestIntegration.test_full_learning_small_limit` all exercise the FindScope/FindC path via negative examples
- QuAcq instantiation in tests already passes checker — need to ensure `model` is also passed
- `_minimal_checker()` creates `NonIncrementalPySATChecker([], [])` — used in tests without real model data

## Requirements

### Functional
- All existing QuAcq tests pass with updated FindScope/FindC
- Tests that exercise negative-example path verify SAT-based pruning works
- No test regressions

### Non-Functional
- Minimal test changes (most tests won't need modification)

## Related Code Files

### Modify
- `tests/test_quacq.py` — update QuAcq instantiation where model is needed

### Reference (read-only)
- `conacq/algorithms/quacq/quacq.py` — to understand which tests hit FindScope/FindC path

## Architecture

### Test Impact Analysis

| Test | Hits FindScope/FindC? | Needs Model? | Change? |
|------|----------------------|-------------|---------|
| `test_quacq_creation` | No (just constructor) | No | None |
| `test_quacq_learn_with_limit` | Yes (negative examples) | Yes | Pass model |
| `test_quacq_empty_bias` | No (empty bias → immediate exit) | No | None |
| `test_quacq_learn_with_quacq_task` | Yes | Yes | Pass model |
| `test_quacq_empty_bias_quacq_task` | No | No | None |
| `test_result_resolved_via_model` | Yes | Yes | Pass model |
| `test_full_learning_small_limit` | Yes | Already passes model | Verify |
| Factory tests | No | No | None |
| Mode validation tests | No (empty bias) | No | Model validation change |

### Key Observations

1. **test_quacq_learn_with_limit** (line 216): Creates QuAcq via `QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)` — does NOT pass model. FindScope/FindC will get `model=None`. Must pass model.

2. **test_quacq_learn_with_quacq_task** (line 464): Same pattern — no model passed to QuAcq. Must add.

3. **test_result_resolved_via_model** (line 511): Same — no model passed. Must add.

4. **test_full_learning_small_limit** (line 291): Already passes `model=model`. OK as-is.

5. **Mode validation tests**: `_validate_mode()` now requires model. Tests using `_minimal_checker()` + no model should still pass for empty-bias tests (model not needed if bias empty, no negative examples processed). But if model validation added unconditionally, need to pass model or adjust validation to only check when bias is non-empty.

## Implementation Steps

### Step 1: Update test_quacq_learn_with_limit

**Before (line 228):**
```python
quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)
```

**After:**
```python
quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen, model=prepared_model)
```

Note: This test uses `prepared_model` fixture (already available via `checker` fixture dependency chain). Add `prepared_model` to test method params.

**Current signature:** `def test_quacq_learn_with_limit(self, prepared_model, oracle, bias, checker)`
`prepared_model` already in params. Just pass it.

### Step 2: Update test_quacq_learn_with_quacq_task

**Before (line 464):**
```python
quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)
```

**After:**
```python
quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen, model=prepared_model)
```

### Step 3: Update test_result_resolved_via_model

**Before (line 511):**
```python
quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)
```

**After:**
```python
quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen, model=prepared_model)
```

### Step 4: Handle model validation in empty-bias tests

Tests `test_quacq_empty_bias` and `test_quacq_empty_bias_quacq_task` use `_minimal_checker()` and no model. They pass empty `set_c=[]`, so the while loop never enters — FindScope/FindC never called. Model validation should be:

**Option A (recommended)**: Validate model only when entering negative-example path (lazy check in learn(), not in _validate_mode). This keeps empty-bias tests working without changes.

**Option B**: Pass a minimal model in empty-bias tests. Unnecessary complexity.

Go with Option A: Add guard `if self.model is None: raise ValueError(...)` in the negative-example branch of learn(), NOT in _validate_mode(). This keeps it lazy.

### Step 5: Run full test suite

```bash
PYTHONPATH=. pytest tests/test_quacq.py -v
```

Verify all tests pass.

### Step 6: Optional — add direct FindScope/FindC unit tests

Consider adding targeted tests for FindScope/FindC with checker. Low priority since integration tests cover the path. If added:

```python
class TestFindScopeWithChecker:
    def test_findscope_prunes_with_sat(self, prepared_model, oracle, checker):
        """FindScope prunes constraints using SAT-based checking."""
        task = prepared_model.task
        find_scope = FindScope(oracle, checker, prepared_model)
        # ... test with real data
```

Mark as optional — only if time permits.

## Todo List

- [ ] Update test_quacq_learn_with_limit: pass model=prepared_model
- [ ] Update test_quacq_learn_with_quacq_task: pass model=prepared_model
- [ ] Update test_result_resolved_via_model: pass model=prepared_model
- [ ] Ensure model validation is lazy (not in _validate_mode)
- [ ] Run full test suite: `PYTHONPATH=. pytest tests/test_quacq.py -v`
- [ ] Run broader tests: `PYTHONPATH=. pytest tests/ -v`
- [ ] (Optional) Add direct FindScope/FindC unit tests

## Success Criteria

- All existing tests pass
- No test regressions in broader test suite
- Tests that exercise negative examples use SAT-based checking path

## Risk Assessment

- **Low**: Most tests don't directly test FindScope/FindC
- **Medium**: test_quacq_learn_with_limit may produce different results (SAT catches more violations → potentially different convergence path). Assert conditions are flexible enough (n_queries <= 5, convergence in valid set).

## Security Considerations

- No external input changes
- Test data paths unchanged

## Next Steps

- Run full test suite to confirm
- Code review
- Documentation update (if API changed significantly)
