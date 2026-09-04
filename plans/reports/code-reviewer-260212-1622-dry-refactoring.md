# Code Review: DRY Refactoring

**Date:** 2026-02-12
**Score:** 9/10
**Verdict:** Clean, correct refactoring. No bugs introduced. One minor type-safety observation.

---

## Scope

- **Files reviewed:** 3 production + 3 test files
- **LOC changed:** ~+55 / -200 (net reduction ~145 lines)
- **Focus:** DRY cleanup -- method extraction, dict-based dispatch, dataclass removal

| File | Change |
|------|--------|
| `acqmss/testcases/generators/base.py` | +50 lines: extracted `_generate_valid_config` + new imports |
| `acqmss/testcases/generators/random_sampling.py` | -98 lines: removed 2 identical method copies + unused imports |
| `apps/generate_examples.py` | -60 lines: removed `ModelConfig`/`parse_models`, dict dispatch for strategies |
| `tests/test_congen.py` | +35 lines: root constraint assertions |
| `tests/test_evaluation.py` | +69 lines: path constants, bg_clauses tests |
| `tests/test_interactive.py` | +21 lines: root feature background tests |

---

## Overall Assessment

Textbook DRY refactoring. All 65 tests pass. No behavioral changes in production code. The test changes are additive (new assertions for root constraint/bg_clauses) and unrelated to the DRY cleanup -- they appear to verify the prior commit `08b4d39` (root constraint in background knowledge).

---

## Critical Issues

None.

---

## High Priority

None.

---

## Medium Priority

### 1. Type-safety: `get_cnf_clauses()` not on ABC (pre-existing)

`_generate_valid_config` in `base.py` calls `self.oracle.get_cnf_clauses()`, but `Oracle` ABC only declares `classify`, `is_valid`, `get_features`, `get_feature_ids`. The method exists only on `FeatureModelOracle`.

This is **pre-existing** (the duplicated methods had the same issue). However, by moving to the base class, the implicit contract is now more visible. A future `Oracle` subclass without `get_cnf_clauses` would fail at runtime.

**Recommendation (low urgency):** Add `get_cnf_clauses` as an abstract method to `Oracle` ABC, or narrow the type hint in `ExampleGenerator.__init__` to `FeatureModelOracle`.

### 2. Internal code duplication in `_generate_valid_config` (pre-existing)

The fallback path (lines 98-104 in `base.py`) duplicates the config-building logic from the primary path (lines 92-96). Could extract a `_model_to_config(model)` helper. Not introduced by this PR -- just made visible.

---

## Low Priority

### 1. `Dict` import from `typing` (minor)

`base.py` imports `Dict` from `typing`. Python 3.9+ supports `dict[str, bool]` natively. Not a bug, just modernization opportunity.

### 2. Verbose print simplification in `process_model`

The removed E+/E- distribution preview (`ControlledRandomSamplingGenerator.calculate_distribution`) was informational. The simplified `(total=N)` message is adequate but less detailed. Acceptable trade-off for DRY.

---

## Detailed Verification

### Imports after removal -- CORRECT

| File | Removed | Still needed? | Verdict |
|------|---------|--------------|---------|
| `random_sampling.py` | `Solver` from `pysat.solvers` | No (moved to base) | OK |
| `random_sampling.py` | `Dict` from `typing` | No (not used) | OK |
| `random_sampling.py` | `Oracle` from `..oracle` | No (only in docstrings) | OK |
| `generate_examples.py` | `dataclass` | No (`ModelConfig` removed) | OK |
| `generate_examples.py` | `RandomSamplingGenerator` | No (was unused import) | OK |

### STRATEGY_COUNTS dict vs if/elif chain -- BEHAVIOR PRESERVED

| Strategy | Old return | Dict lambda | Match? |
|----------|-----------|-------------|--------|
| `rs_1n` | `n_features` | `lambda n, m: n` | Yes |
| `rs_2n` | `2 * n_features` | `lambda n, m: 2 * n` | Yes |
| `rs_3n` | `3 * n_features` | `lambda n, m: 3 * n` | Yes |
| `rs_m` | `m_value` | `lambda n, m: m` | Yes |
| `2cov` | `None` | `lambda n, m: None` | Yes |
| `ff` | `10 * n_features` | `lambda n, m: 10 * n` | Yes |
| `balanced` | `2 * n_features` | `lambda n, m: 2 * n` | Yes |

Error case: unknown strategy raises `ValueError` in both versions. Correct.

### `generate_examples_for_strategy` signature change -- SAFE

Old: `(oracle, strategy, n_features, seed, m_value, valid_configs)`
New: `(oracle, strategy, n_examples, n_features, seed, valid_configs)`

- `m_value` param removed; `n_examples` added (pre-computed by caller)
- Only caller is `process_model` in same file, already updated
- No external imports of this function found

### `process_model` dict vs `ModelConfig` -- BEHAVIOR PRESERVED

Old: `model_config.path`, `.valid_configs`, `.m`, `.strategies`
New: `model_config['path']`, `.get('valid_configs')`, `.get('m')`, `.get('strategies')`

TOML `tomllib.load()` returns dicts, so passing raw dicts is correct. The `ModelConfig` dataclass was just wrapping dict access. `.get()` with default `None` matches the old `Optional` field defaults.

### Missed references to removed symbols -- NONE

`ModelConfig` and `parse_models` still exist in other app scripts (`run_congen.py`, `run_interactive_eval.py`, `run_congen_eval.py`, `generate_bias_files.py`). Those are independent -- no cross-file dependency with `generate_examples.py`.

### metadata['strategy'] deduplication -- CORRECT

Old: set `metadata['strategy']` inside each branch.
New: set once after the if/elif block (line 105). All branches flow through to this line. Correct.

---

## Positive Observations

- Two 49-line identical method copies eliminated -- textbook DRY
- `STRATEGY_COUNTS` dict is more maintainable than if/elif chain; adding a strategy = 1 line
- `ModelConfig` removal reduces indirection with no loss of type safety (TOML always returns dicts)
- Test additions for root constraint/bg_clauses are well-targeted
- `RandomSamplingGenerator` unused import caught and removed

---

## Test Results

```
65 passed, 1 warning in 2.45s
```

Warning is unrelated (`pytest.mark.slow` not registered).

---

## Recommended Actions

1. **(Medium, future)** Add `get_cnf_clauses()` to `Oracle` ABC or narrow type hint in `ExampleGenerator`
2. **(Low, future)** Extract `_model_to_config(model)` helper inside `_generate_valid_config` to remove internal duplication
3. **(Low, future)** Consider same DRY pattern for `ModelConfig`/`parse_models` in `run_congen.py`, `run_congen_eval.py`, `run_interactive_eval.py`

---

## Unresolved Questions

None.
