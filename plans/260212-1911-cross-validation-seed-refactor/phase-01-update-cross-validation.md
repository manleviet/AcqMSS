# Phase 1: Update cross_validation.py

## Context Links

- Source: `acqmss/eval/cross_validation.py` (504 lines)
- Dependency: `acqmss/eval/fold_io.py` (`generate_folds`, `apply_folds`, `FoldData`)
- Plan: [plan.md](plan.md)

## Overview

- **Priority**: P2
- **Status**: complete
- **Description**: Modify both CV function signatures to require `seed`, replace `_split_into_folds` with `generate_folds`+`apply_folds`, remove `_split_into_folds`, fix `shuffle_each_fold` reproducibility.

## Key Insights

- `_split_into_folds` (line 488-504) uses global `random.shuffle` -- non-reproducible
- `generate_folds` returns `FoldData` with index-based fold assignments, same round-robin logic
- Both CV functions already import `FoldData` and `apply_folds` from `fold_io`
- `generate_folds` is NOT yet imported in `cross_validation.py`
- `shuffle_each_fold` uses `random.shuffle` (global state) at lines 217-218 and 403-404 -- also non-reproducible

## Requirements

### Functional
- `seed: int` required (no default) in `n_fold_cross_validation` and `n_fold_cross_validation_interactive`
- When `fold_data is None`: generate folds via `generate_folds(len(pos), len(neg), n_folds, seed)` then use `apply_folds`
- When `fold_data is not None`: existing behavior unchanged
- Remove `_split_into_folds` function entirely
- `shuffle_each_fold` uses local `random.Random(seed)` instead of global `random.shuffle`

### Non-functional
- Backward compatible for callers already passing `seed`
- No behavior change when `fold_data` is provided

## Architecture

No architectural changes. Same data flow; only internal fold-generation mechanism replaced.

```
Before: _split_into_folds(examples, n) -> List[List]  (then manual train/test split)
After:  generate_folds(n_pos, n_neg, n, seed) -> FoldData -> apply_folds(fd, pos, neg, idx)
```

## Related Code Files

| File | Action |
|------|--------|
| `acqmss/eval/cross_validation.py` | Modify |

## Implementation Steps

### 1. Update import (line 23)

Add `generate_folds` to the existing `fold_io` import:
```python
from .fold_io import FoldData, generate_folds, apply_folds
```

### 2. Remove `import random` (line 16)

After all changes, `random` module is no longer needed. Remove `import random` from line 16.

**Wait**: `shuffle_each_fold` still needs random. Use local `random.Random(seed)` instance instead. So still remove the `import random` at module level? No -- `random.Random` is from the `random` module. Keep the import but remove `random.seed(seed)` calls.

### 3. Update `n_fold_cross_validation` signature (line 128-140)

Change `seed: int = None` to `seed: int` (required, no default). Move it before optional params:

```python
def n_fold_cross_validation(
        positive_examples: List[Dict[str, bool]],
        negative_examples: List[Dict[str, bool]],
        n_folds: int,
        bias_clauses: Dict[str, List[List[int]]],
        feature_ids: Dict[str, int],
        seed: int,                              # <-- required, no default
        solver_name: str = 'glucose4',
        is_incremental: bool = True,
        shuffle_each_fold: bool = True,
        fold_data: Optional[FoldData] = None,
        shuffle_bias: bool = False
) -> CrossValidationResult:
```

### 4. Replace fold generation logic in `n_fold_cross_validation` (lines 168-213)

**Remove** lines 168-169 (`if seed is not None: random.seed(seed)`).

**Replace** lines 191-193:
```python
# Old:
if fold_data is None:
    pos_folds = _split_into_folds(positive_examples, n_folds)
    neg_folds = _split_into_folds(negative_examples, n_folds)
```

With:
```python
if fold_data is None:
    fold_data = generate_folds(
        n_positive=len(positive_examples),
        n_negative=len(negative_examples),
        n_folds=n_folds,
        seed=seed
    )
```

**Remove** the `else` branch (lines 209-213) for on-the-fly fold splitting. After this change, `fold_data` is always set, so the loop always uses `apply_folds`:

```python
for fold_idx in range(n_folds):
    train_pos, train_neg, test_pos, test_neg = apply_folds(
        fold_data, positive_examples, negative_examples, fold_idx
    )
```

**Remove** the `if fold_data is not None: ... else: ...` conditional inside the loop (lines 203-213). Just always call `apply_folds`.

### 5. Fix `shuffle_each_fold` reproducibility (line 216-218)

Replace:
```python
if shuffle_each_fold:
    random.shuffle(train_pos)
    random.shuffle(train_neg)
```

With:
```python
if shuffle_each_fold:
    fold_rng = random.Random(fold_data.shuffle_seeds[fold_idx])
    fold_rng.shuffle(train_pos)
    fold_rng.shuffle(train_neg)
```

Using `fold_data.shuffle_seeds[fold_idx]` — `generate_folds` already creates per-fold seeds derived from the original seed, giving deterministic but different shuffle per fold.

### 6. Update `n_fold_cross_validation_interactive` signature (line 314-329)

Same change: `seed: int = None` -> `seed: int` (required).

### 7. Replace fold generation logic in `n_fold_cross_validation_interactive` (lines 354-400)

Same pattern as step 4:
- Remove `if seed is not None: random.seed(seed)` (lines 354-355)
- Replace `_split_into_folds` calls (lines 380-382) with `generate_folds`
- Remove conditional `if fold_data is not None / else` inside loop; always use `apply_folds`
- Fix `shuffle_each_fold` same as step 5

### 8. Remove `_split_into_folds` function (lines 488-504)

Delete the entire function.

### 9. Remove unused `random.seed` pattern

Both functions had `if seed is not None: random.seed(seed)` -- remove these since `generate_folds` handles seeding internally and `shuffle_each_fold` uses local RNG.

### 10. Update docstrings

Update Args sections for both functions:
- `seed` description: "Random seed for fold generation and training shuffle (required)"
- Remove mention of `seed` being optional

## Todo List

- [x] Add `generate_folds` to import from `fold_io`
- [x] Change `seed: int = None` to `seed: int` in `n_fold_cross_validation`
- [x] Remove `random.seed(seed)` from `n_fold_cross_validation`
- [x] Replace `_split_into_folds` with `generate_folds` + unified `apply_folds` loop in `n_fold_cross_validation`
- [x] Fix `shuffle_each_fold` to use local RNG in `n_fold_cross_validation`
- [x] Change `seed: int = None` to `seed: int` in `n_fold_cross_validation_interactive`
- [x] Remove `random.seed(seed)` from `n_fold_cross_validation_interactive`
- [x] Replace `_split_into_folds` with `generate_folds` + unified `apply_folds` loop in `n_fold_cross_validation_interactive`
- [x] Fix `shuffle_each_fold` to use local RNG in `n_fold_cross_validation_interactive`
- [x] Delete `_split_into_folds` function
- [x] Update docstrings for both functions
- [x] Verify `import random` still needed (yes, for `random.Random`)

## Success Criteria

- `_split_into_folds` no longer exists
- Both CV functions require `seed: int` (no default)
- When `fold_data is None`, folds generated via `generate_folds`
- No global `random.seed()` or `random.shuffle()` calls remain
- Existing tests pass (`PYTHONPATH=. pytest tests/ -v`)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Behavioral difference in fold assignment | Low | `generate_folds` uses same round-robin logic as `_split_into_folds`; results may differ due to different RNG seeding but that's the point |
| Breaking callers that pass `seed=None` | Medium | Phase 2 ensures all callers provide a valid seed |

## Security Considerations

None -- purely internal refactoring of fold generation logic.

## Next Steps

Phase 2: Update all callers to pass required `seed` parameter.
