# Code Review: Cross-Validation Seed Refactoring

## Scope
- Files: `acqmss/eval/cross_validation.py`, `apps/run_interactive_eval.py`
- LOC changed: ~90 (net reduction)
- Focus: recent commit -- seed handling, fold generation, deterministic shuffling

## Overall Assessment

Clean, well-motivated refactoring. Eliminates global `random.seed()` state mutation and consolidates fold generation into `generate_folds()` from `fold_io.py`. Per-fold deterministic RNG via `random.Random(seed)` instances is the correct pattern. No critical issues found.

## High Priority

### 1. `process_model` type hint still allows `None` for seed
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_interactive_eval.py:126`

```python
seed: int = None  # type hint says int but default is None
```

The downstream `n_fold_cross_validation_interactive` now requires `seed: int` (no default). If `process_model` is ever called without a seed and CV is triggered, `generate_folds(seed=None)` will be called. `random.Random(None)` is valid Python (uses system entropy), so it won't crash, but it silently breaks reproducibility.

**Impact:** Low risk in practice (all current callers pass `seed=42` as fallback), but the type hint is misleading.

**Fix:** Either `seed: int = 42` or `seed: Optional[int] = None` with explicit documentation that `None` means non-deterministic.

### 2. Logging message always reports `shared_folds=True`
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/eval/cross_validation.py:178-180`

```python
# After fold_data is guaranteed non-None (generated or passed in):
logging.info('... shared_folds=%s', fold_data is not None)  # always True
```

The log parameter `shared_folds` was meaningful when `fold_data` could be `None` during the loop. Now `fold_data` is always set before this line, so it always logs `True`.

**Fix:** Either remove the parameter or change semantics to log whether folds were pre-provided vs generated on-the-fly. For example, capture a boolean before the `if fold_data is None` block:
```python
folds_provided = fold_data is not None
if fold_data is None:
    fold_data = generate_folds(...)
logging.info('... shared_folds=%s', folds_provided)
```

## Medium Priority

### 3. Dead `fold_data is not None` guard in `shuffle_bias` check
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/eval/cross_validation.py:217`, line 398

```python
if shuffle_bias and fold_data is not None:
    fold_shuffle_seed = fold_data.shuffle_seeds[fold_idx]
```

`fold_data` is guaranteed non-None at this point (set at top of function). The `is not None` check is dead code. Not harmful, but slightly misleading -- suggests `fold_data` could still be `None`.

**Fix:** Simplify to `if shuffle_bias:`.

### 4. `random` module still imported but only `random.Random` class used
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/eval/cross_validation.py:16`

The `import random` is still needed for `random.Random(...)`, so this is fine. No action needed -- just noting that no module-level random state functions remain, which is the correct outcome.

## Low Priority

### 5. Config default mismatch: 42 vs 82
All TOML configs use `seed = 82`, but all Python fallbacks use `42`. This is by design (fallback != standard config), but worth noting -- if someone runs without a config, they get different fold splits than documented experiments.

### 6. Interactive function missing `shared_folds` log parameter
`n_fold_cross_validation_interactive` (line 355) doesn't log `shared_folds` at all, while the CONGEN variant does. Minor inconsistency.

## Positive Observations

- **No global state mutation**: Removing `random.seed()` calls eliminates a class of subtle bugs where unrelated code shares the global RNG state
- **Per-fold deterministic RNG**: `random.Random(fold_data.shuffle_seeds[fold_idx])` is the correct pattern -- isolated, reproducible, no cross-fold interference
- **DRY**: Both functions now share the same fold generation path via `generate_folds()` + `apply_folds()`
- **Backward compatible at the call site level**: `run_congen_eval.py` already passes seed as keyword arg with a default, so no breakage
- **Deleted code**: Removing `_split_into_folds` reduces surface area; `generate_folds` in `fold_io.py` is the single source of truth

## Recommended Actions

1. **[High]** Fix `process_model` seed type hint to match the new required contract
2. **[High]** Fix `shared_folds` logging to reflect whether folds were user-provided vs auto-generated
3. **[Medium]** Remove dead `fold_data is not None` guards on lines 217 and 398

## Unresolved Questions

- Was the old behavior (where `seed=None` skipped seeding entirely) intentional for any use case? The new code with `seed=42` fallback always seeds, which changes behavior for configs that deliberately omitted seed. All current TOML configs specify seed, so this is likely a non-issue.
