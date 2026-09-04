# Phase 01: Modify ConGenModelBuilder

## Context

- Parent: [plan.md](plan.md)
- Brainstorm: [brainstorm report](../reports/brainstorm-260218-0929-congenmodelbuilder-auto-prepare.md)
- Target file: `conacq/algorithms/acqmss/congen_model_builder.py`

## Overview

- **Priority**: P2
- **Status**: completed
- **Description**: Add `with_oracle()` method and modify `build()` to auto-prepare when oracle+examples present

## Key Insights

- Current `build()` ignores `with_examples()`/`with_examples_data()` — callers must manually resolve + prepare
- `ConGenModel.prepare()` already idempotent — no changes needed there
- `ConGenRunner` uses build-once-prepare-per-fold pattern → unaffected by changes
- `_resolve_examples()` already handles both file path and raw data

## Requirements

### Functional
1. `with_oracle(oracle)` stores `FeatureModelOracle` instance, returns self
2. `build()` auto-calls `model.prepare()` when both oracle and examples present
3. `with_examples()` clears raw data fields (last-call-wins)
4. `with_examples_data()` clears path field (last-call-wins)
5. Negative examples optional — `_has_examples()` checks positive only

### Non-Functional
- Backward compatible — existing code unchanged
- No new dependencies

## Related Code Files

### Modify
- `conacq/algorithms/acqmss/congen_model_builder.py`

### No Changes Needed
- `conacq/algorithms/acqmss/congen_model.py` — `prepare()` untouched
- `conacq/runners/congen_runner.py` — uses CV pattern, unaffected
- `conacq/algorithms/__init__.py` — already exports `ConGenModelBuilder`

## Implementation Steps

### 1. Add `_oracle` field to `__init__`

```python
self._oracle: Optional['FeatureModelOracle'] = None
```

### 2. Add `with_oracle()` method

```python
def with_oracle(self, oracle: 'FeatureModelOracle') -> 'ConGenModelBuilder':
    """Set oracle for auto-prepare during build()."""
    self._oracle = oracle
    return self
```

### 3. Update `with_examples()` for last-call-wins

Clear `_positive_examples` and `_negative_examples` when path is set.

### 4. Update `with_examples_data()` for last-call-wins

Clear `_examples_path` when raw data is set. Also: negative parameter should be `Optional` (can be empty list or None).

### 5. Modify `build()`

After model construction, add:
```python
if self._oracle and self._has_examples():
    pos, neg = self._resolve_examples()
    model.prepare(oracle=self._oracle,
                  positive_examples=pos,
                  negative_examples=neg or [])
```

### 6. Update docstring and class docstring

Add Pattern 1 (auto-prepare from file) and Pattern 2 (auto-prepare from data) examples.

### 7. Update `_resolve_examples()`

Handle case where `_negative_examples` is None (return empty list).

## Todo List

- [x] Add `_oracle` field
- [x] Add `with_oracle()` method
- [x] Update `with_examples()` — clear raw data fields
- [x] Update `with_examples_data()` — clear path, make negative optional
- [x] Modify `build()` — auto-prepare logic
- [x] Update `_resolve_examples()` — handle None negative
- [x] Update docstrings

## Success Criteria

- All 3 API patterns work as documented in brainstorm
- Existing tests pass without modification
- `ConGenRunner` continues to work (CV pattern)

## Risk Assessment

- **Low**: All changes in single file, backward compatible
- **Edge case**: `build()` with oracle but no examples → unprepared model (correct)
- **Edge case**: `build()` with examples but no oracle → unprepared model (correct)
